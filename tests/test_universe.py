from __future__ import annotations

import pandas as pd
import pytest

from src.data.universe import (
    DataFileUnavailableError,
    build_universe,
    is_lfs_pointer,
    load_etfdb_screener,
)


def test_load_etfdb_screener_rejects_lfs_pointer(tmp_path):
    screener = tmp_path / "etfdb_screener.csv"
    screener.write_text(
        "version https://git-lfs.github.com/spec/v1\n"
        "oid sha256:abc\n"
        "size 123\n",
        encoding="utf-8",
    )

    assert is_lfs_pointer(screener)
    with pytest.raises(DataFileUnavailableError, match="Git LFS pointer"):
        load_etfdb_screener(screener)


def test_build_universe_can_fallback_to_processed_panel_metadata(tmp_path):
    screener = tmp_path / "etfdb_screener.csv"
    screener.write_text(
        "version https://git-lfs.github.com/spec/v1\n"
        "oid sha256:abc\n"
        "size 123\n",
        encoding="utf-8",
    )
    processed_panel = tmp_path / "core_panel.csv"
    pd.DataFrame(
        {
            "Symbol": ["aaa", "aaa", "bbb.c"],
            "Name": ["Fund A", "Fund A", "Fund B"],
            "Assets": ["$1M", "$1M", "$2M"],
            "ETF Database Category": ["Corporate Bonds", "Corporate Bonds", "Government Bonds"],
            "ER": ["0.10%", "0.10%", "0.20%"],
            "Inception": ["2020-01-01", "2020-01-01", "2021-01-01"],
        }
    ).to_csv(processed_panel, index=False)

    metadata, tickers = build_universe(
        screener,
        filter_history=False,
        metadata_fallback_paths=[processed_panel],
    )

    assert tickers == ["AAA", "BBB-C"]
    assert metadata["Symbol"].tolist() == ["AAA", "BBB-C"]
    assert metadata["Name"].tolist() == ["Fund A", "Fund B"]
