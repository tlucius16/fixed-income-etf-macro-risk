from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path

import pandas as pd

from src import config


def _safe_table_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip().lower())
    cleaned = cleaned.strip("._-")
    if not cleaned:
        raise ValueError("Table name must contain at least one alphanumeric character.")
    return cleaned


def table_export_dir(panel_mode: str = config.DEFAULT_PANEL_MODE) -> Path:
    return config.TABLES_EXPORT_DIR / panel_mode


def _markdown_table(table: pd.DataFrame, index: bool = False) -> str:
    out = table.reset_index() if index else table.copy()
    out = out.astype(object).where(pd.notna(out), "")
    columns = [str(col) for col in out.columns]
    rows = [[str(value) for value in row] for row in out.to_numpy()]

    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines) + "\n"


def export_table(
    table: pd.DataFrame | pd.Series,
    name: str,
    panel_mode: str = config.DEFAULT_PANEL_MODE,
    formats: Sequence[str] = ("csv",),
    index: bool = False,
) -> dict[str, Path]:
    """Export one notebook result table to the standard exports folder."""
    if isinstance(table, pd.Series):
        table = table.to_frame()
    if not isinstance(table, pd.DataFrame):
        raise TypeError("table must be a pandas DataFrame or Series.")

    output_dir = table_export_dir(panel_mode)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = _safe_table_name(name)

    written: dict[str, Path] = {}
    for fmt in formats:
        normalized = fmt.lower()
        path = output_dir / f"{stem}.{normalized}"
        if normalized == "csv":
            table.to_csv(path, index=index)
        elif normalized == "markdown":
            path.write_text(_markdown_table(table, index=index), encoding="utf-8")
        elif normalized == "latex":
            path.write_text(table.to_latex(index=index), encoding="utf-8")
        else:
            raise ValueError(f"Unsupported table format {fmt!r}.")
        written[normalized] = path

    return written


def export_tables(
    tables: Mapping[str, pd.DataFrame | pd.Series],
    panel_mode: str = config.DEFAULT_PANEL_MODE,
    formats: Sequence[str] = ("csv",),
    index: bool = False,
) -> dict[str, dict[str, Path]]:
    return {
        name: export_table(table, name, panel_mode=panel_mode, formats=formats, index=index)
        for name, table in tables.items()
    }
