"""Standalone, resumable ThetaData v3 acquisition. See docs/windows_options_pull.md.

No legacy imports, quote screening, Greek requirements, OI filling, or study writes.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timedelta, timezone
import getpass
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import re
import sys
import time

import pandas as pd

LIQUID_TICKERS = ["EDV", "EMB", "IEF", "LQD", "TIP", "TLT", "VCLT", "ZROZ"]
ENDPOINTS = {
    "eod": "option_history_eod",
    "open_interest": "option_history_open_interest",
    "greeks_eod": "option_history_greeks_eod",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def classify_error(exc):
    """Do not turn access failures, unknown failures, or missing OI into zero data."""
    message = str(exc).upper()
    if any(x in message for x in ("PERMISSION_DENIED", "UNAUTHENTICATED", "UNAUTHORIZED",
                                  "FORBIDDEN", "HTTP 401", "HTTP 403")):
        return "permission_denied"
    if any(x in message for x in ("NO_DATA", "NO DATA FOUND", "HTTP 472")):
        return "no_data"
    if any(x in message for x in ("RESOURCE_EXHAUSTED", "UNAVAILABLE", "DEADLINE_EXCEEDED",
                                  "TIMEOUT", "TIMED OUT", "HTTP 429", "HTTP 500",
                                  "HTTP 502", "HTTP 503", "HTTP 504")):
        return "transient_error"
    return "error"


class SDKSource:
    def __init__(self):
        os.environ.setdefault("GRPC_DNS_RESOLVER", "native")
        from thetadata import ThetaClient
        email = os.environ.get("THETADATA_USERNAME") or input("ThetaData email: ")
        password = os.environ.get("THETADATA_PASSWORD") or getpass.getpass("ThetaData password: ")
        self.client = ThetaClient(email=email, password=password, dataframe_type="pandas")

    def fetch(self, endpoint, parameters):
        kwargs = dict(parameters)
        for key in ("start_date", "end_date"):
            kwargs[key] = date.fromisoformat(kwargs[key])
        frame = getattr(self.client, ENDPOINTS[endpoint])(**kwargs)
        if not isinstance(frame, pd.DataFrame):
            raise ValueError("Expected a pandas DataFrame from ThetaData")
        return frame


class RESTSource:
    def __init__(self, base_url):
        import requests
        self.session = requests.Session()
        self.base_url = base_url.rstrip("/")

    def fetch(self, endpoint, parameters):
        response = self.session.get(
            f"{self.base_url}/option/history/{endpoint.replace('_', '/') if endpoint == 'greeks_eod' else endpoint}",
            params={**parameters, "format": "csv"}, timeout=(10, 180),
        )
        if response.status_code == 204:
            return pd.DataFrame()
        if response.status_code != 200:
            raise RuntimeError(f"HTTP {response.status_code}: {response.text[:300]}")
        return pd.read_csv(io.StringIO(response.text))


def validate_frame(frame, endpoint, parameters):
    """Check response identity without dropping malformed prices, null IV, or zero OI."""
    if frame.empty and len(frame.columns) == 0:
        return
    fields = {"symbol", "expiration", "strike", "right"}
    fields |= {"created", "bid", "ask"} if endpoint == "eod" else {"timestamp"}
    if endpoint == "open_interest":
        fields.add("open_interest")
    if not fields.issubset(frame.columns):
        raise ValueError(f"Missing response columns: {sorted(fields - set(frame.columns))}")
    if frame.empty:
        return
    if not frame.symbol.eq(parameters["symbol"]).all():
        raise ValueError("Response contains a different symbol")
    clock = "created" if endpoint == "eod" else "timestamp"
    # Preserve timestamp text. No timezone conversion or OI date shifting here.
    days = frame[clock].astype(str).str[:10]
    if not days.eq(parameters["start_date"]).all():
        raise ValueError("Response contains a different observation date")


def acquire(root, endpoint, parameters, source, *, retries=3, retry_empty=False):
    directory = root / parameters["symbol"] / parameters["start_date"]
    directory.mkdir(parents=True, exist_ok=True)
    metadata_path = directory / f"{endpoint}.json"
    csv_path = directory / f"{endpoint}.csv.gz"
    if metadata_path.exists():
        saved = json.loads(metadata_path.read_text(encoding="utf-8"))
        if saved["parameters"] != parameters:
            raise ValueError("Request changed inside an existing run; use a new output folder")
        if saved["status"] == "ok":
            if not csv_path.exists() or digest(csv_path) != saved["sha256"]:
                raise ValueError(f"Damaged saved partition: {csv_path}")
            return saved
        if saved["status"] == "no_data" and not retry_empty:
            return saved
    record = {"endpoint": ENDPOINTS[endpoint], "parameters": parameters,
              "retrieved_at_utc": utc_now(), "rows": 0}
    for attempt in range(retries + 1):
        try:
            frame = source.fetch(endpoint, parameters)
            validate_frame(frame, endpoint, parameters)
            record.pop("error_type", None)
            record["status"] = "no_data" if frame.empty else "ok"
            record["rows"] = len(frame)
            record["columns"] = list(frame.columns)
            if not frame.empty:
                temporary = csv_path.with_suffix(".tmp")
                frame.to_csv(temporary, index=False, compression={"method": "gzip", "mtime": 0})
                temporary.replace(csv_path)
                record["sha256"] = digest(csv_path)
                record["file"] = str(csv_path.relative_to(root)).replace("\\", "/")
            break
        except Exception as exc:
            record["status"] = classify_error(exc)
            # Exception payloads may include credentials. Store only type and category.
            record["error_type"] = type(exc).__name__
            if record["status"] == "transient_error" and attempt < retries:
                time.sleep(min(2 ** attempt, 30))
                continue
            break
    record["attempts"] = attempt + 1
    write_json(metadata_path, record)
    return record


def make_plan(args):
    if args.dates:
        dates = sorted({date.fromisoformat(value) for value in args.dates})
    else:
        if not args.start or not args.end:
            raise ValueError("Provide --dates or both --start and --end")
        start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
        if start > end:
            raise ValueError("Start must precede end")
        dates = [start + timedelta(days=n) for n in range((end - start).days + 1)
                 if (start + timedelta(days=n)).weekday() < 5]
    if not dates or max(dates) >= datetime.now(timezone.utc).date():
        raise ValueError("Use completed historical dates before today")
    tickers = list(dict.fromkeys(ticker.upper() for ticker in args.tickers))
    if any(not re.fullmatch(r"[A-Z][A-Z0-9.]{0,9}", ticker) for ticker in tickers):
        raise ValueError("Invalid ticker")
    if args.max_dte is not None and args.max_dte < 1:
        raise ValueError("max-dte must be positive")
    return {"schema_version": 1, "tickers": tickers,
            "dates": [day.isoformat() for day in dates], "max_dte": args.max_dte,
            "endpoints": list(ENDPOINTS) if args.greeks else ["eod", "open_interest"],
            "backend": args.backend, "base_url": args.base_url if args.backend == "rest" else None,
            "expiration": "*", "strike": "*", "right": "both",
            "date_rule": "explicit_dates" if args.dates else "weekdays_inclusive_holidays_attempted",
            "script_sha256": digest(Path(__file__))}


def run(args, source=None):
    plan = make_plan(args)
    expected = len(plan["tickers"]) * len(plan["dates"]) * len(plan["endpoints"])
    print(f"{len(plan['tickers'])} tickers, {len(plan['dates'])} dates, {expected} requests", flush=True)
    if args.dry_run:
        print(json.dumps(plan, indent=2))
        return 0
    root = args.output.resolve()
    manifest_path = root / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["plan"] != plan:
            raise ValueError("Existing run has a different plan/source; use a new output folder")
    else:
        if root.exists() and any(root.iterdir()):
            raise ValueError("Output folder is nonempty without this collector's manifest")
        root.mkdir(parents=True, exist_ok=True)
        versions = {}
        for package in ("pandas", "requests", "thetadata"):
            try:
                versions[package] = importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:
                pass
        manifest = {"plan": plan, "created_at_utc": utc_now(), "python": sys.version,
                    "platform": platform.platform(), "packages": versions,
                    "status": "in_progress", "expected_requests": expected}
        write_json(manifest_path, manifest)
    counts = Counter()
    rows = []
    source = source or (SDKSource() if args.backend == "sdk" else RESTSource(args.base_url))
    stopped = False
    try:
        for ticker in plan["tickers"]:
            for day in plan["dates"]:
                for endpoint in plan["endpoints"]:
                    parameters = {"symbol": ticker, "start_date": day, "end_date": day,
                                  "expiration": "*", "strike": "*", "right": "both"}
                    if plan["max_dte"] is not None:
                        parameters["max_dte"] = plan["max_dte"]
                    record = acquire(root, endpoint, parameters, source,
                                     retry_empty=args.retry_empty)
                    counts[record["status"]] += 1
                    rows.append({"symbol": ticker, "date": day, "endpoint": endpoint,
                                 "status": record["status"], "rows": record["rows"]})
                    print(f"{len(rows)}/{expected} {ticker} {day} {endpoint}: "
                          f"{record['status']} ({record['rows']} rows)", flush=True)
                    if record["status"] not in {"ok", "no_data"}:
                        stopped = True
                        return 2
    finally:
        pd.DataFrame(rows).to_csv(root / "coverage.csv", index=False)
        manifest.update(updated_at_utc=utc_now(), counts=dict(counts),
                        status="requests_finished_review_coverage" if len(rows) == expected and not stopped
                        else "incomplete")
        write_json(manifest_path, manifest)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--tickers", nargs="+", default=LIQUID_TICKERS)
    parser.add_argument("--dates", nargs="+")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--max-dte", type=int, help="Omit to request all expirations")
    parser.add_argument("--greeks", action="store_true", help="Store independent EOD Greeks responses")
    parser.add_argument("--backend", choices=["sdk", "rest"], default="sdk")
    parser.add_argument("--base-url", default="http://127.0.0.1:25503/v3")
    parser.add_argument("--retry-empty", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dates and (args.start or args.end):
        parser.error("Use --dates or --start/--end, not both")
    try:
        return run(args)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"{exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
