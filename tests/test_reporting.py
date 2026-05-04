from __future__ import annotations

import pandas as pd

from src.reporting import tables


def test_export_table_writes_safe_csv_and_markdown(tmp_path, monkeypatch):
    monkeypatch.setattr(tables.config, "TABLES_EXPORT_DIR", tmp_path)

    df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    written = tables.export_table(
        df,
        "Category Summary!",
        panel_mode="offline",
        formats=("csv", "markdown"),
    )

    assert set(written) == {"csv", "markdown"}
    assert written["csv"] == tmp_path / "offline" / "category_summary.csv"
    assert written["markdown"] == tmp_path / "offline" / "category_summary.markdown"
    assert pd.read_csv(written["csv"]).equals(df)
    assert "| A" in written["markdown"].read_text(encoding="utf-8")
