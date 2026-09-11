"""Active hedge-design checks and explicit legacy-paper reproduction.

The default hedge-design profile verifies a pinned input audit and runs focused
tests. The nominal CVaR frontier is implemented and runs as an explicit, write-once
experiment via scripts/run_hedge_design.py; finite-model robust optimization is
controlled by robust_enabled in study_config.json. No legacy analysis, notebook, data fetch, or paper-artifact
producer runs in the default profile.

The legacy profile retains the unified-paper pipeline in dependency order:

  screen     legacy/unified/scripts/03_concat_screen.py        chains/summary/ticker_summary.csv
  iv         legacy/unified/scripts/04_build_iv_panel.py       iv_panel_full.csv        [FRED_API_KEY]
  cp-diag    scripts/05_build_call_put_iv_...   call_put_iv_diagnostic.csv
  panel      legacy/unified/scripts/06_build_options_panel.py  options_panel.csv
  ladder     legacy/unified/scripts/07_robustness_ladder.py    robustness_spec0.csv, side_capacity.csv
  artifacts  legacy/unified/scripts/08_paper_artifacts.py      hedge-capacity tables + figures
  h4-ref     legacy/unified/scripts/09_fragility_h4.py         stress-interaction reference table
  jl-boot    julia robustness_boot.jl           robustness_boot.csv
  jl-amer    julia american_bias.jl             american_bias.csv
  core-nb    nbconvert --execute notebooks 02-03 core fragility results
  hedge-nb   nbconvert --execute notebook 05    hedge-capacity results
  tests      pytest -q

Requires the raw ThetaData caches under data/raw/options_screen/ (see
REPRODUCING.md). Only the `iv` stage needs a credential (FRED_API_KEY, read
from the environment or .env). Julia stages are skipped with a warning when
no julia executable is found.

Usage
-----
    python scripts/reproduce.py                    # active audit verification + tests
    python scripts/reproduce.py --list
    python scripts/reproduce.py --profile legacy --list
    python scripts/reproduce.py --profile legacy --from ladder
    python scripts/reproduce.py --profile legacy --until panel
    python scripts/reproduce.py --profile legacy --skip-julia --skip-notebook
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

IV_END_DEFAULT = "2026-07-17"   # last Friday in the canonical IV cache
AUDIT_DATASET_DEFAULT = "local-20260904-v2"


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


def _run(cmd: list[str], name: str, *, allow_incomplete: bool = False) -> int:
    t0 = time.time()
    print(f"\n=== [{name}] {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=REPO, text=True, capture_output=True)
    dt = time.time() - t0
    tail = "\n".join(proc.stdout.strip().splitlines()[-6:])
    print(tail)
    if allow_incomplete and proc.returncode == 2:
        print(f"[{name}] INCOMPLETE: source audit reports unresolved inputs.")
        return 2
    if proc.returncode != 0:
        print(proc.stderr[-2000:])
        sys.exit(f"[{name}] FAILED after {dt:.0f}s (exit {proc.returncode})")
    print(f"[{name}] OK ({dt:.0f}s)")
    return 0


def _checkpoints() -> None:
    import pandas as pd
    from legacy.unified.src import config as cfg

    print("\n=== Checkpoints ===")
    ok = True

    def check(label, actual, expected) -> None:
        nonlocal ok
        good = actual == expected
        ok &= good
        print(f"  {'OK  ' if good else 'FAIL'} {label}: {actual} (expected {expected})")

    chains = pd.read_csv(cfg.CHAINS_CSV)
    check("chains.csv rows", len(chains), 339220)
    ts = pd.read_csv(cfg.TICKER_SUMMARY_CSV)
    check("liquid tickers", int(ts["liquid"].sum()), 6)
    liquid = sorted(ts.loc[ts["liquid"], "ticker"].astype(str).tolist())
    check("liquid ticker set", liquid, ["EDV", "EMB", "IEF", "LQD", "TLT", "ZROZ"])
    panel = pd.read_csv(cfg.OPTIONS_PANEL_CSV)
    check("options_panel.csv rows", len(panel), 18056)
    funnel = pd.read_csv(cfg.TABLES_DIR / "sample_funnel.csv")
    check("sample funnel ETF counts", funnel["etfs"].astype(int).tolist(), [352, 36, 33, 6])
    ladder = pd.read_csv(cfg.TABLES_DIR / "robustness_spec0.csv")
    s0 = ladder.loc[(ladder["spec"] == "S0 baseline (date FE)")
                    & (ladder["var"] == "hedge_capacity_ratio"), "coef"].iloc[0]
    check("Spec 0 coefficient (4dp)", round(float(s0), 4), -0.3377)
    boot = cfg.TABLES_DIR / "robustness_boot.csv"
    if boot.exists():
        boot_df = pd.read_csv(boot)
        boot_s0 = boot_df.loc[
            (boot_df["spec"] == "S0 baseline (date FE)")
            & (boot_df["var"] == "hedge_capacity_ratio"),
            "p_wildboot",
        ].iloc[0]
        check("Spec 0 wild-bootstrap p (4dp)", round(float(boot_s0), 4), 0.0953)
    else:
        print("  note robustness_boot.csv absent (Julia stages skipped?)")
    if not ok:
        sys.exit("Checkpoint mismatch — the run does not reproduce the reference state.")
    print("All checkpoints passed.")


def build_stages(profile: str, dataset_id: str, iv_end: str) -> list[tuple[str, list[str]]]:
    py = sys.executable
    if profile == "hedge-design":
        return [
            ("audit", [py, "scripts/audit_hedge_inputs.py", "--dataset-id", dataset_id, "--verify"]),
            ("tests", [py, "-m", "pytest", "tests/hedge_design", "tests/workflow", "-q"]),
        ]
    if profile != "legacy":
        raise ValueError(f"Unknown profile: {profile}")
    return [
        ("screen",    [py, "legacy/unified/scripts/03_concat_screen.py"]),
        ("iv",        [py, "legacy/unified/scripts/04_build_iv_panel.py", "--end", iv_end]),
        ("cp-diag",   [py, "legacy/unified/scripts/05_build_call_put_iv_diagnostic.py"]),
        ("panel",     [py, "legacy/unified/scripts/06_build_options_panel.py"]),
        ("ladder",    [py, "legacy/unified/scripts/07_robustness_ladder.py"]),
        ("artifacts", [py, "legacy/unified/scripts/08_paper_artifacts.py"]),
        ("h4-ref",    [py, "legacy/unified/scripts/09_fragility_h4.py"]),
        ("jl-boot",   ["julia", "--project=legacy/unified/julia", "legacy/unified/julia/scripts/robustness_boot.jl"]),
        ("jl-amer",   ["julia", "--project=legacy/unified/julia", "-t", "auto",
                       "legacy/unified/julia/scripts/american_bias.jl"]),
        ("core-nb",    [py, "-m", "jupyter", "nbconvert", "--to", "notebook",
                       "--execute", "--inplace", "legacy/unified/notebooks/02_rolling_risk_metrics.ipynb",
                       "legacy/unified/notebooks/03_analysis.ipynb"]),
        ("hedge-nb",   [py, "-m", "jupyter", "nbconvert", "--to", "notebook",
                       "--execute", "--inplace", "legacy/unified/notebooks/05_options_analysis.ipynb"]),
        ("tests",     [py, "-m", "pytest", "tests/", "legacy/unified/tests/", "-q"]),
    ]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--profile", choices=["hedge-design", "legacy"], default="hedge-design")
    p.add_argument("--dataset-id", default=None, help=f"active audit manifest (default {AUDIT_DATASET_DEFAULT})")
    p.add_argument("--list", action="store_true")
    p.add_argument("--from", dest="from_stage", default=None, metavar="STAGE")
    p.add_argument("--until", dest="until_stage", default=None, metavar="STAGE")
    p.add_argument("--skip-julia", action="store_true", help="legacy profile only")
    p.add_argument("--skip-notebook", action="store_true", help="legacy profile only")
    p.add_argument("--iv-end", default=None, help=f"legacy IV end date (default {IV_END_DEFAULT})")
    args = p.parse_args(argv)
    if args.profile == "hedge-design" and (args.skip_julia or args.skip_notebook or args.iv_end is not None):
        p.error("--skip-julia, --skip-notebook, and --iv-end require --profile legacy")
    if args.profile == "legacy" and args.dataset_id is not None:
        p.error("--dataset-id applies only to --profile hedge-design")
    stages = build_stages(args.profile, args.dataset_id or AUDIT_DATASET_DEFAULT,
                          args.iv_end or IV_END_DEFAULT)
    names = [n for n, _ in stages]

    if args.list:
        print("\n".join(names))
        return 0
    for flag, val in (("--from", args.from_stage), ("--until", args.until_stage)):
        if val is not None and val not in names:
            p.error(f"{flag} {val!r}: unknown stage for {args.profile}. "
                    f"Stages: {', '.join(names)}. Old analysis stages require --profile legacy.")

    start = names.index(args.from_stage) if args.from_stage else 0
    stop = names.index(args.until_stage) + 1 if args.until_stage else len(names)
    if start >= stop:
        p.error("--from must not follow --until")

    julia = None
    if args.profile == "legacy":
        _load_dotenv()
        julia = shutil.which("julia")

    if "iv" in names[start:stop] and not os.environ.get("FRED_API_KEY"):
        sys.exit("FRED_API_KEY not set (environment or .env) — required by the iv stage.")

    result_code = 0
    print(f"Profile: {args.profile}")
    for name, cmd in stages[start:stop]:
        if name.startswith("jl-"):
            if args.skip_julia:
                print(f"\n=== [{name}] skipped (--skip-julia)")
                continue
            if julia is None:
                print(f"\n=== [{name}] skipped (julia not found)")
                continue
        if name in {"core-nb", "hedge-nb"} and args.skip_notebook:
            print(f"\n=== [{name}] skipped (--skip-notebook)")
            continue
        result_code = max(result_code, _run(cmd, name, allow_incomplete=(name == "audit")))

    if args.profile == "legacy" and stop == len(stages):
        _checkpoints()
    elif args.profile == "hedge-design":
        print("Active checks finished. Nominal and finite-model robust design run as explicit "
              "experiments (scripts/run_hedge_design.py); enable robust_enabled for Phase 3.")
        if result_code:
            print("Input verification remains incomplete; no hedge results were generated here.")
    return result_code


if __name__ == "__main__":
    raise SystemExit(main())
