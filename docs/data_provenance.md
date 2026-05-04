# Data Provenance

This project builds weekly fixed-income ETF panels from ETF prices, ETFDB metadata, macro-risk factors, and a weekly risk-free rate.

## Panel Slots

- `data/processed/offline/`: stable research panel used by notebooks by default.
- `data/processed/live/`: fresh rebuild target for live pulls.
- `data/exports/legacy_csv_exports/`: preserved historical exports from the original prototype.
- `data/raw/`: manually supplied source inputs, currently mainly `etfdb_screener.csv` if present.

## ETF Universe And Returns

- Universe input: `data/raw/etfdb_screener.csv` if present, else `data/exports/legacy_csv_exports/database.csv`.
- Price source: `yfinance`.
- Frequency: daily adjusted close is resampled to Friday weekly close.
- Return: simple weekly percentage return from weekly close.
- Missing price gaps are not forward-filled before return calculation.
- Panel shape: long and unbalanced. ETFs enter when valid return history exists.

## Macro Factors

Macro factors are sampled to Friday weekly levels, then weekly changes are computed.

- `ANFCI`: FRED `ANFCI`.
- `BAMLC0A0CM`: hybrid ICE BofA credit spread series.
- `DGS10`: FRED `DGS10`.
- `T10Y2Y`: FRED `T10Y2Y`.
- `T5YIE`: FRED `T5YIE`.
- `VIX`: Yahoo `^VIX`.
- `MOVE`: Yahoo `^MOVE`.
- `GPR`: Matteo Iacoviello daily GPR spreadsheet, resampled weekly.

## Hybrid BAML Handling

FRED now exposes only a rolling three-year window for the ICE BofA `BAMLC0A0CM` series. To preserve the historical research sample:

1. Load historical weekly BAML from `data/exports/legacy_csv_exports/baml_w.csv`.
2. Pull recent `BAMLC0A0CM` observations from FRED.
3. Concatenate legacy and live rows.
4. Sort by date and de-duplicate, keeping live FRED values on overlapping dates.
5. Recompute weekly changes after the full macro merge.

This means the live macro build is not pure FRED-only for BAML; it is historical cache plus live update.

## Risk-Free Rate

- Source: FRED `DTB3`.
- Conversion: annualized percent divided by `100 * 52` to produce an approximate weekly decimal rate.
- Excess return: `RET_XS = Return - RF_w`.

## Known Caveats

- The ETF universe is based on current or preserved ETFDB metadata and may include survivorship bias.
- ICE BofA historical data may have redistribution restrictions. Review licensing before making this repository or the legacy CSV exports public.
- Live pulls can change over time. Use `data/processed/offline/` for reproducible analysis snapshots.
- GPR live input is an `.xls` file and requires `xlrd` in the active Python environment.
