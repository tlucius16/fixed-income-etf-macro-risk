"""Opt-in parity test: RateSpace.jl vs the Python BSM reference.

Runs julia/scripts/parity_check.jl on a 2,000-row sample of the cached
chains.csv and asserts it exits cleanly. Skipped unless Julia is installed
AND RUN_JULIA_PARITY=1 is set (Julia startup + compile makes this a ~1-min
test; the default suite stays fast).

    RUN_JULIA_PARITY=1 .venv/bin/python -m pytest tests/test_julia_parity.py -v
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_CHAINS = _REPO / "data" / "processed" / "options_screen" / "chains.csv"


@pytest.mark.skipif(shutil.which("julia") is None, reason="julia not installed")
@pytest.mark.skipif(os.getenv("RUN_JULIA_PARITY") != "1",
                    reason="set RUN_JULIA_PARITY=1 to run")
@pytest.mark.skipif(not _CHAINS.exists(), reason="chains.csv not built")
def test_julia_parity_sample():
    result = subprocess.run(
        ["julia", "--project=julia", "julia/scripts/parity_check.jl",
         "--sample", "2000"],
        cwd=_REPO, capture_output=True, text=True, timeout=600,
    )
    assert result.returncode == 0, (
        f"parity check failed:\n{result.stdout}\n{result.stderr}"
    )
    assert "PARITY OK" in result.stdout
