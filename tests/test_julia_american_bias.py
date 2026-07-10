"""Opt-in smoke test for julia/scripts/american_bias.jl.

Skipped unless Julia is installed AND RUN_JULIA_AMERICAN=1 is set; the default
suite remains fast and Julia-free.

    RUN_JULIA_AMERICAN=1 .venv/bin/python -m pytest tests/test_julia_american_bias.py -v
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pandas as pd
import pytest

_REPO = Path(__file__).resolve().parents[1]
_CHAINS = _REPO / "data" / "processed" / "options_screen" / "chains.csv"


@pytest.mark.skipif(shutil.which("julia") is None, reason="julia not installed")
@pytest.mark.skipif(
    os.getenv("RUN_JULIA_AMERICAN") != "1",
    reason="set RUN_JULIA_AMERICAN=1 to run",
)
@pytest.mark.skipif(not _CHAINS.exists(), reason="chains.csv not built")
def test_julia_american_bias_smoke(tmp_path: Path):
    out = tmp_path / "american_bias_smoke.csv"
    result = subprocess.run(
        [
            "julia", "--project=julia", "julia/scripts/american_bias.jl",
            "--max-rows", "1000", "--out", str(out), "--progress-every", "0",
        ],
        cwd=_REPO, capture_output=True, text=True, timeout=900,
    )
    if result.returncode != 0 and "Could not create lockfile" in result.stderr:
        pytest.skip("Juliaup launcher cannot create its lockfile in this sandbox")
    assert result.returncode == 0, (
        f"American-bias smoke failed:\n{result.stdout}\n{result.stderr}"
    )
    assert "CRR checks OK" in result.stdout
    assert out.exists()

    summary = pd.read_csv(out)
    required = {
        "ticker", "right", "moneyness_bucket", "rows",
        "valid_american_iv", "no_solution",
        "median_iv_bias", "p95_abs_iv_bias",
        "median_eep_pct_mid",
    }
    assert required.issubset(summary.columns)
    assert len(summary) > 0
    assert (summary["rows"] > 0).all()
