"""Opt-in test for julia/scripts/robustness_boot.jl.

Runs the point-estimate parity checks and a tiny bootstrap smoke test. Skipped
unless Julia is installed AND RUN_JULIA_BOOTSTRAP=1 is set; the default test
suite remains fast and Julia-free.

    RUN_JULIA_BOOTSTRAP=1 .venv/bin/python -m pytest tests/test_julia_robustness_boot.py -v
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pandas as pd
import pytest

_REPO = Path(__file__).resolve().parents[1]
_OPTIONS_PANEL = _REPO / "data" / "processed" / "options_screen" / "options_panel.csv"
_CHAINS = _REPO / "data" / "processed" / "options_screen" / "chains.csv"


@pytest.mark.skipif(shutil.which("julia") is None, reason="julia not installed")
@pytest.mark.skipif(
    os.getenv("RUN_JULIA_BOOTSTRAP") != "1",
    reason="set RUN_JULIA_BOOTSTRAP=1 to run",
)
@pytest.mark.skipif(not _OPTIONS_PANEL.exists(), reason="options_panel.csv not built")
@pytest.mark.skipif(not _CHAINS.exists(), reason="chains.csv not built")
def test_julia_robustness_boot_smoke(tmp_path: Path):
    out = tmp_path / "robustness_boot_smoke.csv"
    result = subprocess.run(
        [
            "julia", "--project=julia", "julia/scripts/robustness_boot.jl",
            "--reps", "99", "--seed", "20260709", "--out", str(out),
        ],
        cwd=_REPO, capture_output=True, text=True, timeout=900,
    )
    if result.returncode != 0 and "Could not create lockfile" in result.stderr:
        pytest.skip("Juliaup launcher cannot create its lockfile in this sandbox")
    assert result.returncode == 0, (
        f"robustness bootstrap failed:\n{result.stdout}\n{result.stderr}"
    )
    assert "Point-estimate parity" in result.stdout
    assert out.exists()

    boot = pd.read_csv(out)
    assert set(["spec", "var", "coef", "p_cgm", "p_wildboot", "n_reps", "seed"]).issubset(boot.columns)
    assert len(boot) == 5
    assert boot["p_wildboot"].between(0, 1).all()
