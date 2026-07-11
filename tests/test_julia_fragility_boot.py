"""Opt-in parity test for the fragility H4 wild-bootstrap script.

Runs julia/scripts/fragility_boot.jl in --check-only mode (point-estimate
parity against fragility_h4_reference.csv; no bootstrap). Skipped unless
Julia is installed AND RUN_JULIA_FRAGILITY=1.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_REF = _REPO / "data" / "exports" / "tables" / "fragility_h4_reference.csv"


@pytest.mark.skipif(shutil.which("julia") is None, reason="julia not installed")
@pytest.mark.skipif(os.getenv("RUN_JULIA_FRAGILITY") != "1",
                    reason="set RUN_JULIA_FRAGILITY=1 to run")
@pytest.mark.skipif(not _REF.exists(), reason="reference CSV not built")
def test_fragility_parity_check_only():
    result = subprocess.run(
        ["julia", "--project=julia", "julia/scripts/fragility_boot.jl", "--check-only"],
        cwd=_REPO, capture_output=True, text=True, timeout=900,
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert "FAIL" not in result.stdout
