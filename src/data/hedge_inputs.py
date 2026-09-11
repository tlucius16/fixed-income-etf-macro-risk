"""Offline input audit for hedge design; never fetches or repairs source data."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd


CHAIN_PATH = "data/processed/options_screen/chains.csv"
CORE_PATH = "data/processed/offline/core_panel.csv"
PRICE_PATH = "data/raw/prices.csv"
CHAIN_KEY = ["ticker", "snap_date", "expiry", "strike", "right"]
CHAIN_REQUIRED = CHAIN_KEY + ["underlying", "bid", "ask", "open_interest"]
PILOT_TICKERS = ("LQD", "TLT", "IEF")
REVIEW_TICKERS = PILOT_TICKERS + ("AGG", "EMB", "HYG")
REFERENCE_CHAIN_ROWS = 339_220


def is_cloud_placeholder(path: Path) -> bool:
    # Darwin's SF_DATALESS flag: opening this file can block on cloud hydration.
    return bool(getattr(path.stat(), "st_flags", 0) & 0x40000000)


def sha256_file(path: Path) -> str:
    if is_cloud_placeholder(path):
        raise OSError(f"Cloud-only placeholder: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _date_text(value: object) -> str | None:
    return None if pd.isna(value) else pd.Timestamp(value).date().isoformat()


def inventory_sources(root: Path, progress: Callable[[str], None] | None = None) -> list[dict]:
    """Inventory explicit study inputs, excluding credentials and generated audits."""
    paths = set()
    for folder in ("data/raw/options_screen", "data/processed/options_screen",
                   "data/processed/offline"):
        paths.update(p for p in (root / folder).rglob("*")
                     if p.is_file() and p.suffix in {".json", ".csv"})
    for name in (PRICE_PATH, "data/exports/legacy_csv_exports/raw_prices.csv",
                 "data/exports/legacy_csv_exports/daily_returns.csv"):
        if (root / name).is_file():
            paths.add(root / name)
    entries = []
    for index, path in enumerate(sorted(paths)):
        if progress and index % 1000 == 0:
            progress(f"Inventory: {index:,}/{len(paths):,} files")
        entry = {"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size,
                 "sha256": None, "status": "cloud_placeholder"}
        if not is_cloud_placeholder(path):
            try:
                entry.update(sha256=sha256_file(path), status="hashed")
            except OSError:
                entry["status"] = "unreadable"
        entries.append(entry)
    return entries


def load_chains(path: Path) -> pd.DataFrame:
    if is_cloud_placeholder(path):
        raise OSError("Chain panel is cloud-only")
    frame = pd.read_csv(path)
    missing = sorted(set(CHAIN_REQUIRED) - set(frame.columns))
    if missing:
        raise ValueError(f"Missing chain columns: {', '.join(missing)}")
    for column in ("snap_date", "expiry"):
        frame[column] = pd.to_datetime(frame[column], errors="raise")
    if frame[CHAIN_KEY].isna().any().any():
        raise ValueError("Null contract key")
    if frame.duplicated(CHAIN_KEY).any():
        raise ValueError("Duplicate contract key")
    return frame


def load_prices(path: Path) -> pd.DataFrame:
    if is_cloud_placeholder(path):
        raise OSError("Price file is cloud-only")
    frame = pd.read_csv(path)
    if "Date" not in frame:
        raise ValueError("Price file requires Date")
    frame["Date"] = pd.to_datetime(frame["Date"], errors="raise")
    if frame["Date"].isna().any() or frame["Date"].duplicated().any():
        raise ValueError("Null or duplicate price date")
    frame = frame.set_index("Date").sort_index()
    return frame.apply(pd.to_numeric, errors="raise")


def quote_flags(chains: pd.DataFrame, max_rel_spread: float = 0.35) -> pd.DataFrame:
    """Audit quote eligibility only; this does not verify deliverables or execution."""
    bid = pd.to_numeric(chains["bid"], errors="coerce")
    ask = pd.to_numeric(chains["ask"], errors="coerce")
    spot = pd.to_numeric(chains["underlying"], errors="coerce")
    strike = pd.to_numeric(chains["strike"], errors="coerce")
    oi = pd.to_numeric(chains["open_interest"], errors="coerce")
    mid = (bid + ask) / 2
    spread = (ask - bid) / mid.where(mid > 0)
    flags = pd.DataFrame(index=chains.index)
    flags["nonfinite_quote"] = ~np.isfinite(bid) | ~np.isfinite(ask)
    flags["nonpositive_bid"] = bid <= 0
    flags["nonpositive_ask"] = ask <= 0
    flags["crossed_quote"] = ask < bid
    flags["wide_spread"] = spread > max_rel_spread
    flags["invalid_spot_or_strike"] = (~np.isfinite(spot) | ~np.isfinite(strike)
                                               | (spot <= 0) | (strike <= 0))
    flags["invalid_right"] = ~chains["right"].isin(["C", "P"])
    flags["expired_contract"] = chains["expiry"] <= chains["snap_date"]
    quote_columns = flags.columns.tolist()
    flags["quote_eligible"] = ~flags[quote_columns].any(axis=1)
    flags["oi_missing"] = oi.isna()
    flags["oi_zero"] = oi == 0
    flags["oi_invalid"] = oi.notna() & (~np.isfinite(oi) | (oi < 0) | (oi % 1 != 0))
    return flags


def inspect_raw_chains(root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    records, diagnostics = [], []
    for path in sorted((root / "data/raw/options_screen").glob("*/*_chain.json")):
        item = {"path": path.relative_to(root).as_posix(), "ticker": path.parent.name,
                "snap_date": path.name.removesuffix("_chain.json"), "rows": 0}
        if is_cloud_placeholder(path):
            item["status"] = "cloud_placeholder"
            diagnostics.append(item)
            continue
        try:
            payload = json.loads(path.read_text())
            if not isinstance(payload, list) or any(not isinstance(r, dict) for r in payload):
                item["status"] = "invalid_schema"
            elif not payload:
                # Legacy empty arrays have no fetch status and cannot prove market absence.
                item["status"] = "empty_unverified"
            else:
                item["rows"] = len(payload)
                if any(not set(CHAIN_KEY).issubset(r) for r in payload):
                    item["status"] = "invalid_schema"
                elif any(str(r["ticker"]) != item["ticker"]
                         or str(r["snap_date"]) != item["snap_date"] for r in payload):
                    item["status"] = "path_record_mismatch"
                else:
                    item["status"] = "records"
                    records.extend(payload)
        except (OSError, ValueError, TypeError):
            item["status"] = "unreadable"
        diagnostics.append(item)
    return pd.DataFrame(records), pd.DataFrame(
        diagnostics, columns=["path", "ticker", "snap_date", "rows", "status"])


def reconcile_chains(raw: pd.DataFrame, derived: pd.DataFrame) -> dict:
    """Compare records independent of order and CSV float round-tripping."""
    if raw.empty or derived.empty:
        return {"status": "unavailable", "reason": "Raw or derived records missing"}
    if set(raw.columns) != set(derived.columns):
        return {"status": "mismatch", "reason": "Column sets differ"}
    if raw.duplicated(CHAIN_KEY).any() or derived.duplicated(CHAIN_KEY).any():
        return {"status": "mismatch", "reason": "Duplicate contract keys"}
    left, right = raw.copy(), derived.copy()
    for frame in (left, right):
        for column in ("snap_date", "expiry"):
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
    left = left.sort_values(CHAIN_KEY).reset_index(drop=True).sort_index(axis=1)
    right = right.sort_values(CHAIN_KEY).reset_index(drop=True).sort_index(axis=1)
    try:
        pd.testing.assert_frame_equal(left, right, check_dtype=False,
                                      check_exact=False, rtol=1e-9, atol=1e-12)
    except AssertionError:
        return {"status": "mismatch", "reason": "Values or row counts differ"}
    return {"status": "match", "rows": len(left), "float_rtol": 1e-9}


def price_coverage(prices: pd.DataFrame, tickers: tuple[str, ...]) -> pd.DataFrame:
    rows = []
    for ticker in tickers:
        values = prices[ticker] if ticker in prices else pd.Series(dtype=float)
        valid = values[np.isfinite(values) & (values > 0)]
        rows.append({"ticker": ticker, "present": ticker in prices,
                     "valid_rows": len(valid), "missing_rows": int(values.isna().sum()),
                     "invalid_nonmissing_rows": int((values.notna() &
                         (~np.isfinite(values) | (values <= 0))).sum()),
                     "first_date": _date_text(valid.index.min()) if len(valid) else None,
                     "last_date": _date_text(valid.index.max()) if len(valid) else None})
    return pd.DataFrame(rows)


def pilot_coverage(chains: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """Choose one expiry from the union; never fill missing settlement dates."""
    columns = ["snap_date", "expiry", "ticker", "quote_eligible_puts", "oi_positive_puts",
               "decision_price_present", "expiry_price_present", "prior_price_rows",
               "max_spot_relative_gap", "status"]
    rows = []
    flags = quote_flags(chains)
    dte = (chains["expiry"] - chains["snap_date"]).dt.days
    candidate = chains.loc[flags["quote_eligible"] & chains["right"].eq("P")
                           & chains["ticker"].isin(PILOT_TICKERS) & dte.between(21, 60)]
    for snap in sorted(chains["snap_date"].unique()):
        snap = pd.Timestamp(snap)
        options = candidate.loc[candidate["snap_date"] == snap]
        expiries = options["expiry"].unique()
        expiry = (min(map(pd.Timestamp, expiries), key=lambda e: (abs((e - snap).days - 30), e))
                  if len(expiries) else None)
        for ticker in PILOT_TICKERS:
            selected = options.loc[options["ticker"].eq(ticker)
                                   & options["expiry"].eq(expiry)]
            series = prices[ticker] if ticker in prices else pd.Series(dtype=float)
            series = series[np.isfinite(series) & (series > 0)]
            at_start = snap in series.index
            at_end = expiry is not None and expiry in series.index
            gap = ((selected["underlying"] / series.loc[snap] - 1).abs().max()
                   if at_start and not selected.empty else None)
            if expiry is None:
                status = "no_eligible_expiration"
            elif not at_start or not at_end:
                status = "missing_exact_price"
            elif selected.empty:
                status = "empty_menu"
            else:
                status = "price_coverage_only"
            rows.append({"snap_date": _date_text(snap), "expiry": _date_text(expiry),
                         "ticker": ticker, "quote_eligible_puts": len(selected),
                         "oi_positive_puts": int((pd.to_numeric(selected["open_interest"],
                             errors="coerce") > 0).sum()),
                         "decision_price_present": at_start, "expiry_price_present": at_end,
                         "prior_price_rows": int((series.index < snap).sum()),
                         "max_spot_relative_gap": gap, "status": status})
    return pd.DataFrame(rows, columns=columns)


def _csv_summary(path: Path) -> dict:
    frame = pd.read_csv(path)
    info = {"rows": len(frame), "columns": frame.columns.tolist()}
    date_col = next((c for c in ("snap_date", "Date", "date") if c in frame), None)
    ticker_col = next((c for c in ("ticker", "Symbol") if c in frame), None)
    if date_col:
        dates = pd.to_datetime(frame[date_col], errors="coerce")
        info.update(first_date=_date_text(dates.min()), last_date=_date_text(dates.max()),
                    unique_dates=int(dates.nunique()), invalid_dates=int(dates.isna().sum()))
    if ticker_col:
        info["tickers"] = sorted(frame[ticker_col].dropna().astype(str).unique().tolist())
    key = [c for c in (ticker_col, date_col) if c]
    if "side" in frame:
        key.append("side")
    if path.name == "chains.csv":
        key = CHAIN_KEY if set(CHAIN_KEY).issubset(frame) else []
    if key:
        info["key"] = key
        info["duplicate_keys"] = int(frame.duplicated(key).sum())
        info["null_keys"] = int(frame[key].isna().any(axis=1).sum())
    return info


def audit_inputs(root: Path, dataset_id: str, *,
                 progress: Callable[[str], None] | None = None) -> tuple[dict, dict[str, pd.DataFrame]]:
    """Return a compact manifest and detailed local diagnostics without writing."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", dataset_id):
        raise ValueError("dataset-id must contain only letters, digits, underscores, and hyphens")
    sources = inventory_sources(root, progress)
    issues = []

    def issue(code: str, severity: str, message: str) -> None:
        issues.append({"code": code, "severity": severity, "message": message})

    summaries = {}
    for entry in sources:
        if entry["status"] != "hashed":
            continue
        if entry["path"].startswith("data/processed/") and entry["path"].endswith(".csv"):
            try:
                info = _csv_summary(root / entry["path"])
                summaries[entry["path"]] = info
                if info.get("duplicate_keys", 0) or info.get("null_keys", 0) or info.get("invalid_dates", 0):
                    issue("derived_key_quality", "error", f"Invalid dates/keys: {entry['path']}")
            except (ValueError, OSError, pd.errors.ParserError) as exc:
                issue("unreadable_csv", "error", f"Cannot summarize {entry['path']}: {type(exc).__name__}")

    unavailable = [e for e in sources if e["status"] != "hashed"]
    if unavailable:
        issue("sources_not_local", "error",
              f"{len(unavailable)} source files are cloud-only or unreadable; content fingerprint is partial")
    if progress:
        progress("Inspecting chain schemas, prices, and raw/derived agreement")
    chains = pd.DataFrame()
    try:
        chains = load_chains(root / CHAIN_PATH)
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        issue("invalid_chains", "error", f"Cannot use chain panel: {exc}")
    if not (root / CORE_PATH).is_file():
        issue("missing_core", "error", "Fixed core panel is missing")
    elif not {"Date", "Symbol", "Return"}.issubset(summaries.get(CORE_PATH, {}).get("columns", [])):
        issue("invalid_core_schema", "error", "Core panel must contain Date, Symbol, Return")
    prices = pd.DataFrame()
    try:
        prices = load_prices(root / PRICE_PATH)
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        issue("invalid_prices", "error", f"Cannot use unadjusted prices: {exc}")

    raw, raw_files = inspect_raw_chains(root)
    raw_status = dict(Counter(raw_files["status"]))
    if raw_files.empty:
        issue("missing_raw_chains", "error", "No raw chain cache files")
    for status in ("unreadable", "invalid_schema", "path_record_mismatch"):
        if raw_status.get(status):
            issue("raw_" + status, "error", f"{raw_status[status]} raw chain files: {status}")
    if raw_status.get("empty_unverified"):
        issue("empty_cache_unverified", "warning",
              f"{raw_status['empty_unverified']} empty arrays lack fetch status; market absence is unverified")
    reconciliation = ({"status": "unavailable", "reason": "Some raw chains are cloud-only"}
                      if raw_status.get("cloud_placeholder") else reconcile_chains(raw, chains))
    available_comparison = {"status": "unavailable"}
    if not raw.empty and not chains.empty:
        pairs = raw[["ticker", "snap_date"]].drop_duplicates().copy()
        pairs["snap_date"] = pd.to_datetime(pairs["snap_date"], errors="coerce")
        observed = pd.MultiIndex.from_frame(chains[["ticker", "snap_date"]])
        subset = chains.loc[observed.isin(pd.MultiIndex.from_frame(pairs))]
        available_comparison = reconcile_chains(raw, subset)
        if available_comparison["status"] == "mismatch":
            issue("available_raw_mismatch", "error", "Available raw records disagree with their derived snapshot rows")
    if reconciliation["status"] != "match":
        issue("raw_derived_unreconciled", "error", "Full raw/derived agreement has not been established")

    pilot = pd.DataFrame()
    quote_counts = {}
    chain_tickers = set()
    if not chains.empty:
        flags = quote_flags(chains)
        quote_counts = {c: int(flags[c].sum()) for c in flags}
        if flags["oi_invalid"].any():
            issue("invalid_oi", "warning", "Some OI values are negative, fractional, or infinite")
        chain_tickers = set(chains["ticker"])
        pilot = pilot_coverage(chains, prices)
        if len(chains) != REFERENCE_CHAIN_ROWS:
            issue("reference_sample_mismatch", "warning",
                  f"Observed {len(chains):,} chain rows; legacy checkpoint expects {REFERENCE_CHAIN_ROWS:,}")
        for ticker in REVIEW_TICKERS:
            if ticker not in chain_tickers:
                issue("missing_universe_" + ticker, "warning", f"{ticker} absent from observed option chains")

    # These files contain no validated corporate-action or execution metadata contract.
    # A column name or a cached dividend yield alone is insufficient evidence.
    raw_columns = sorted(raw.columns.tolist())
    missing_fields = sorted({"multiplier", "deliverable_status", "quote_timestamp",
                             "oi_available_at"} - set(raw_columns))
    issue("contract_metadata_unverified", "blocker",
          "Contract multiplier/deliverable validation required; no verified metadata source configured")
    issue("execution_timing_unverified", "blocker",
          "Quote/OI availability timing is unverified; no executable same-day backtest claim")
    issue("daily_total_returns_unverified", "blocker",
          "No validated daily total-return/distribution and split input configured; price-only is a separate pilot")
    issue("static_aum", "warning", "Legacy AUM is static; investor position size is the proposed frontier denominator")

    groups = {}
    for prefix in ("data/raw/options_screen/", "data/processed/options_screen/",
                   "data/processed/offline/", "data/exports/legacy_csv_exports/"):
        subset = [entry for entry in sources if entry["path"].startswith(prefix)]
        groups[prefix] = {"files": len(subset), "bytes": sum(e["bytes"] for e in subset),
                          "unhashed_files": sum(e["status"] != "hashed" for e in subset),
                          "sha256": json_digest(subset)}
    direct_files = [entry for entry in sources if entry["path"] == PRICE_PATH]
    source_tree = {"groups": groups, "files": direct_files}
    code_paths = ("src/data/hedge_inputs.py", "scripts/audit_hedge_inputs.py",
                  "src/data/options_universe.py", "src/data/prices.py",
                  "scripts/01_download_prices.py", "scripts/reproduce.py")
    code = [{"path": name, "sha256": sha256_file(root / name)}
            for name in code_paths if (root / name).is_file()]
    integrity_ok = not any(i["severity"] == "error" for i in issues)
    derived_ok = not chains.empty and not prices.empty and not any(
        i["code"] in {"invalid_chains", "invalid_prices", "missing_core", "invalid_core_schema",
                      "derived_key_quality", "unreadable_csv", "available_raw_mismatch"}
        for i in issues)
    manifest = {
        "schema_version": 1, "dataset_id": dataset_id,
        "scope": "Local fixed core, options caches/derived panels, and candidate daily price inputs; no network",
        "input_fingerprint": json_digest(source_tree), "sources": source_tree,
        "content_fingerprint_complete": not unavailable,
        "audit_code": code, "csv_summaries": summaries,
        "raw_chains": {"files": len(raw_files), "rows": len(raw),
                       "dates": sorted(raw_files["snap_date"].unique().tolist()),
                       "status_counts": raw_status, "fields": raw_columns},
        "raw_derived_reconciliation": reconciliation,
        "available_raw_comparison": available_comparison,
        "quote_counts": quote_counts, "missing_raw_metadata_fields": missing_fields,
        "reference": {"source": "scripts/reproduce.py legacy checkpoint",
                      "chain_rows": REFERENCE_CHAIN_ROWS, "status": "unverified_reference"},
        "price_coverage": json.loads(price_coverage(prices, REVIEW_TICKERS).to_json(orient="records")),
        "pilot": {"tickers": list(PILOT_TICKERS), "expiry_target_days": 30,
                  "expiry_window_days": [21, 60], "max_rel_spread": 0.35,
                  "status_counts": dict(Counter(pilot["status"])) if not pilot.empty else {}},
        "readiness": {"source_integrity": "pass" if integrity_ok else "fail",
                      "descriptive_analysis": "conditional_on_derived_inputs" if derived_ok else "blocked",
                      "price_only_hedge_design": "blocked_pending_contract_validation",
                      "total_return_hedge_design": "blocked_pending_contract_and_return_validation",
                      "executable_backtest": "not_established"},
        "issues": issues,
    }
    return manifest, {"source_files": pd.DataFrame(sources), "raw_cache_status": raw_files,
                      "pilot_coverage": pilot}


def render_audit(manifest: dict) -> str:
    lines = ["# Hedge Input Audit", "", f"Dataset: `{manifest['dataset_id']}`", "",
             f"Inventory fingerprint: `{manifest['input_fingerprint']}`", "",
             f"All source contents hashed: **{manifest['content_fingerprint_complete']}**.", "",
             "This is a source audit, not a hedge backtest. Inputs were not modified or fetched.",
             "", "## Readiness", ""]
    lines += [f"- {key}: **{value}**" for key, value in manifest["readiness"].items()]
    lines += ["", "## Observed Panels", "", "| File | Rows | Dates | Range |",
              "|---|---:|---:|---|"]
    for path, info in manifest["csv_summaries"].items():
        lines.append(f"| `{path}` | {info['rows']:,} | {info.get('unique_dates', '-')} | "
                     f"{info.get('first_date', '-')} to {info.get('last_date', '-')} |")
    raw = manifest["raw_chains"]
    lines += ["", "## Raw Cache", "",
              f"{raw['files']:,} chain files; {raw['rows']:,} accepted records; {len(raw['dates'])} dates.",
              "", f"Raw/derived reconciliation: **{manifest['raw_derived_reconciliation']['status']}**.", ""]
    lines += [f"Available raw subset agreement: **{manifest['available_raw_comparison']['status']}**.", ""]
    lines += [f"- {key}: {value}" for key, value in raw["status_counts"].items()]
    lines += ["", "## Daily Price Coverage", "",
              "| Ticker | Valid rows | First | Last |", "|---|---:|---|---|"]
    for row in manifest["price_coverage"]:
        lines.append(f"| {row['ticker']} | {row['valid_rows']} | {row['first_date']} | {row['last_date']} |")
    lines += ["", "## Pilot Coverage", "",
              "Same expiration across LQD/TLT/IEF, nearest 30 days within 21-60 days;",
              "positive, non-crossed quotes and relative spread <= 35%. No Greek floors.",
              "Exact decision/expiration prices are checked without filling missing dates.",
              "Counts below describe ticker-date rows, not independent trades.", ""]
    lines += [f"- {key}: {value}" for key, value in manifest["pilot"]["status_counts"].items()]
    lines += ["", "## Findings", ""]
    lines += [f"- **{i['severity']} / {i['code']}**: {i['message']}" for i in manifest["issues"]]
    lines += ["", "## Next Data Requirements", "",
              "1. Reconcile failed source checks before scenario construction.",
              "2. Establish multipliers, deliverables, corporate actions, and expiration conventions.",
              "3. Validate daily distributions/total returns or declare a separate price-only pilot.",
              "4. Resolve quote/OI timing before calling a design experiment executable.",
              "", "Detailed source hashes, cache statuses, and pilot dates are in the adjacent CSV files.", ""]
    return "\n".join(lines)


def write_audit(root: Path, manifest: dict, tables: dict[str, pd.DataFrame]) -> Path:
    dataset_id = manifest["dataset_id"]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", dataset_id):
        raise ValueError("Invalid dataset-id")
    manifest_path = root / "data/manifests" / f"{dataset_id}.json"
    output = root / "data/processed/hedge_design" / dataset_id
    if manifest_path.exists() or output.exists():
        raise FileExistsError(f"Dataset {dataset_id} already exists; verify it or use a new dataset-id")
    payload = json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n"
    output.mkdir(parents=True)
    for name, table in tables.items():
        table.to_csv(output / f"{name}.csv", index=False)
    report = output / "audit.md"
    report.write_text(render_audit(manifest))
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("x") as stream:
        stream.write(payload)
    return report
