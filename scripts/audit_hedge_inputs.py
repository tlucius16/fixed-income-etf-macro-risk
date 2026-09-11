"""Audit local hedge inputs without fetching data or modifying source caches."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data.hedge_inputs import audit_inputs, write_audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--verify", action="store_true", help="Compare existing manifest without writing")
    args = parser.parse_args()
    try:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.dataset_id):
            raise ValueError("Invalid dataset-id")
        path = ROOT / "data/manifests" / f"{args.dataset_id}.json"
        output = ROOT / "data/processed/hedge_design" / args.dataset_id
        if not args.verify and (path.exists() or output.exists()):
            raise FileExistsError("Dataset already exists; use --verify or a new dataset-id")
        if args.verify and not path.exists():
            raise FileNotFoundError(f"Manifest not found: {path.relative_to(ROOT)}")
        manifest, tables = audit_inputs(ROOT, args.dataset_id, progress=lambda message: print(message, flush=True))
        if args.verify:
            previous = json.loads(path.read_text())
            matched = previous["input_fingerprint"] == manifest["input_fingerprint"]
            print(f"Inventory fingerprint: {'MATCH' if matched else 'CHANGED'}")
            print(f"All source contents hashed: {manifest['content_fingerprint_complete']}")
            print(f"Audit code: {'MATCH' if previous['audit_code'] == manifest['audit_code'] else 'CHANGED'}")
            if not matched:
                return 1
            return 0 if manifest["content_fingerprint_complete"] else 2
        report = write_audit(ROOT, manifest, tables)
    except (OSError, ValueError) as exc:
        print(f"Audit failed: {exc}", file=sys.stderr)
        return 1
    print(f"Manifest: {path.relative_to(ROOT)}")
    print(f"Report: {report.relative_to(ROOT)}")
    for check, status in manifest["readiness"].items():
        print(f"{check}: {status}")
    # A valid audit may document research blockers. Structural input failures use 2.
    return 0 if manifest["readiness"]["source_integrity"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
