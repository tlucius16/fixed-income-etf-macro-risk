"""One-command reproduction of every derived artifact from the raw caches.

Runs the full pipeline in dependency order:

  screen     scripts/02_concat_screen.py        chains/summary/ticker_summary.csv
  iv         scripts/03_build_iv_panel.py       iv_panel_full.csv        [FRED_API_KEY]
  cp-diag    scripts/05_build_call_put_iv_...   call_put_iv_diagnostic.csv
  panel      scripts/04_build_options_panel.py  options_panel.csv
  ladder     scripts/06_robustness_ladder.py    robustness_spec0.csv, side_capacity.csv
  artifacts  scripts/07_paper_artifacts.py      paper tables + figures 24-26
  jl-parity  julia parity_check.jl              (gate: must print PARITY OK)
  jl-boot    julia robustness_boot.jl           robustness_boot.csv
  jl-amer    julia american_bias.jl             american_bias.csv
  notebook   nbconvert --execute notebook 05    all remaining figures/tables
  tests      pytest -q

Requires the raw ThetaData caches under data/raw/options_screen/ (see
REPRODUCING.md). Only the `iv` stage needs a credential (FRED_API_KEY, read
from the environment or .env). Julia stages are skipped with a warning when
no julia executable is found.

Usage
-----
    python scripts/reproduce.py                    # everything
    python scripts/reproduce.py --list
    python scripts/reproduce.py --from ladder      # resume mid-pipeline
    python scripts/reproduce.py --until panel
    python scripts/reproduce.py --skip-julia --skip-notebook
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

IV_END_DEFAULT = "2026-07-02"   # last Friday in the committed IV cache


def _load_dotenv() -> None:
    env_file = REPO / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())


def _run(cmd: list[str], name: str) -> str:
    t0 = time.time()
    print(f"\n=== [{name}] {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=REPO, text=True, capture_output=True)
    dt = time.time() - t0
    tail = "\n".join(proc.stdout.strip().splitlines()[-6:])
    print(tail)
    if proc.returncode != 0:
        print(proc.stderr[-2000:])
        sys.exit(f"[{name}] FAILED after {dt:.0f}s (exit {proc.returncode})")
    print(f"[{name}] OK ({dt:.0f}s)")
    return proc.stdout


def _checkpoints() -> None:
    import pandas as pd
    from src import config as cfg

    print("\n=== Checkpoints ===")
    ok = True

    def check(label, actual, expected) -> None:
        nonlocal ok
        good = actual == expected
        ok &= good
        print(f"  {'OK  ' if good else 'FAIL'} {label}: {actual} (expected {expected})")

    chains = pd.read_csv(cfg.CHAINS_CSV)
    check("chains.csv rows", len(chains), 80521)
    ts = pd.read_csv(cfg.TICKER_SUMMARY_CSV)
    check("liquid tickers", int(ts["liquid"].sum()), 8)
    panel = pd.read_csv(cfg.OPTIONS_PANEL_CSV)
    check("options_panel.csv rows", len(panel), 18058)
    ladder = pd.read_csv(cfg.TABLES_DIR / "robustness_spec0.csv")
    s0 = ladder.loc[(ladder["spec"] == "S0 baseline (date FE)")
                    & (ladder["var"] == "hedge_capacity_ratio"), "coef"].iloc[0]
    check("Spec 0 coefficient (4dp)", round(float(s0), 4), -0.2682)
    boot = cfg.TABLES_DIR / "robustness_boot.csv"
    print(f"  {'OK  ' if boot.exists() else 'note'} robustness_boot.csv "
          f"{'present' if boot.exists() else 'absent (julia stages skipped?)'}")
    if not ok:
        sys.exit("Checkpoint mismatch — the run does not reproduce the reference state.")
    print("All checkpoints passed.")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--list", action="store_true")
    p.add_argument("--from", dest="from_stage", default=None, metavar="STAGE")
    p.add_argument("--until", dest="until_stage", default=None, metavar="STAGE")
    p.add_argument("--skip-julia", action="store_true")
    p.add_argument("--skip-notebook", action="store_true")
    p.add_argument("--iv-end", default=IV_END_DEFAULT,
                   help=f"end date for the IV panel (default {IV_END_DEFAULT}; "
                        "later dates require ThetaData credentials)")
    args = p.parse_args()

    _load_dotenv()
    py = sys.executable
    julia = shutil.which("julia")

    stages: list[tuple[str, list[str]]] = [
        ("screen",    [py, "scripts/02_concat_screen.py"]),
        ("iv",        [py, "scripts/03_build_iv_panel.py", "--end", args.iv_end]),
        ("cp-diag",   [py, "scripts/05_build_call_put_iv_diagnostic.py"]),
        ("panel",     [py, "scripts/04_build_options_panel.py"]),
        ("ladder",    [py, "scripts/06_robustness_ladder.py"]),
        ("artifacts", [py, "scripts/07_paper_artifacts.py"]),
        ("jl-parity", ["julia", "--project=julia", "julia/scripts/parity_check.jl"]),
        ("jl-boot",   ["julia", "--project=julia", "julia/scripts/robustness_boot.jl"]),
        ("jl-amer",   ["julia", "--project=julia", "-t", "auto",
                       "julia/scripts/american_bias.jl"]),
        ("notebook",  [py, "-m", "jupyter", "nbconvert", "--to", "notebook",
                       "--execute", "--inplace", "notebooks/05_options_analysis.ipynb"]),
        ("tests",     [py, "-m", "pytest", "tests/", "-q"]),
    ]
    names = [n for n, _ in stages]

    if args.list:
        print("\n".join(names))
        return
    for flag, val in (("--from", args.from_stage), ("--until", args.until_stage)):
        if val is not None and val not in names:
            sys.exit(f"{flag} {val!r}: unknown stage. Stages: {', '.join(names)}")

    start = names.index(args.from_stage) if args.from_stage else 0
    stop = names.index(args.until_stage) + 1 if args.until_stage else len(names)

    if "iv" in names[start:stop] and not os.environ.get("FRED_API_KEY"):
        sys.exit("FRED_API_KEY not set (environment or .env) — required by the iv stage.")

    for name, cmd in stages[start:stop]:
        if name.startswith("jl-"):
            if args.skip_julia:
                print(f"\n=== [{name}] skipped (--skip-julia)")
                continue
            if julia is None:
                print(f"\n=== [{name}] skipped (julia not found)")
                continue
        if name == "notebook" and args.skip_notebook:
            print(f"\n=== [{name}] skipped (--skip-notebook)")
            continue
        out = _run(cmd, name)
        if name == "jl-parity" and "PARITY OK" not in out:
            sys.exit("jl-parity did not report PARITY OK — aborting.")

    if stop == len(stages):
        _checkpoints()


if __name__ == "__main__":
    main()
