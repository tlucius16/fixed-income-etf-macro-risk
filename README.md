# Fixed-Income ETF Macro-Risk Research

This repository supports a research workflow for studying fixed-income ETF fragility under macro stress. The core question is: how do fixed-income ETF returns and fragility measures respond to changes in financial conditions, rates, credit spreads, inflation expectations, volatility, and geopolitical risk?

The repo is built around the existing end-to-end prototype, but the active workflow is now split into small Python modules under `src/`.

## Repository Structure

```text
.
├── README.md
├── requirements.txt
├── data
│   ├── raw
│   ├── processed
│   └── exports
│       └── legacy_csv_exports
├── legacy
│   └── etf_data_legacy_reference.py
├── notebooks
│   ├── 01_exploration.ipynb
│   └── 02_rolling_risk_metrics.ipynb
├── src
│   ├── config.py
│   ├── data
│   │   ├── macro.py
│   │   ├── prices.py
│   │   ├── risk_free.py
│   │   └── universe.py
│   ├── features
│   │   └── structural.py
│   └── pipelines
│       └── build_core_panel.py
└── tests
```

## Legacy References

The original prototype is preserved unchanged at:

```text
legacy/etf_data_legacy_reference.py
```

The full exported pandas CSV folder is preserved unchanged at:

```text
data/exports/legacy_csv_exports/
```

These files are references, not the active source code. The modular pipeline follows the same ordering and naming conventions where practical.

## Setup

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If you use FRED pulls, set a FRED API key:

```bash
export FRED_API_KEY="your_key_here"
```

'''
$env:FRED_API_KEY = "your_key_here"
'''

## Inputs

The preferred ETFDB screener input location is:

```text
data/raw/etfdb_screener.csv
```

If that file is absent, the pipeline falls back to the preserved legacy export:

```text
data/exports/legacy_csv_exports/database.csv
```

## Run The Core Panel Build

From the repo root:

```bash
python -m src.pipelines.build_core_panel
```

Useful options:

```bash
python -m src.pipelines.build_core_panel --min-years 5
python -m src.pipelines.build_core_panel --screener-csv data/raw/etfdb_screener.csv
python -m src.pipelines.build_core_panel --output-dir data/processed
```

The pipeline writes CSV outputs only:

```text
data/processed/weekly_returns_long.csv
data/processed/macro_factors_weekly.csv
data/processed/core_panel.csv
```

## Notebooks

The notebooks are for secondary analysis:

```text
notebooks/01_exploration.ipynb
notebooks/02_rolling_risk_metrics.ipynb
```

They import from `src/` and read processed CSVs. They should not duplicate the full ingestion pipeline.
