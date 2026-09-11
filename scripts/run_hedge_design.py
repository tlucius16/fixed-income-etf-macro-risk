"""Run or verify the offline, single-expiration accounting pilot."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.hedge_design.experiment import run_pilot, verify_run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("study_config.json"))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--verify", action="store_true", help="Check existing inputs, code and outputs without writing")
    args = parser.parse_args()
    try:
        if args.verify:
            verify_run(ROOT, args.run_id)
            print("Run inputs, code, dependencies and outputs MATCH. Research status remains conditional.")
        else:
            destination = run_pilot(ROOT, ROOT / args.config, args.run_id)
            print(f"Created {destination.relative_to(ROOT)}/report.md")
            print("Conditional accounting pilot only; standard deliverables and execution remain unverified.")
    except (OSError, ValueError, KeyError) as exc:
        print(f"Pilot failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
