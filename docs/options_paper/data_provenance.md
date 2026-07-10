# Data Provenance — Options Paper

## Input Files

| File | Script | Description |
|---|---|---|
| `data/processed/options_screen/ticker_summary.csv` | `src.data.options.concat_results` | Per-ticker liquidity screen metrics across quarterly snap dates, 2020–2025 |
| `data/processed/options_screen/chains.csv` | `src.data.options.concat_results` | Full call/put option-chain rows with BSM Greeks and open interest |
| `data/processed/options_screen/summary.csv` | `src.data.options.concat_results` | Aggregated per (ticker, snap_date): pass rate and median Greeks |
| `data/processed/options_screen/iv_panel_full.csv` | `scripts/03_build_iv_panel.py` | Weekly near-30-day call/put IV merged with realized vol and forward outcomes |
| `data/processed/options_screen/options_panel.csv` | `scripts/04_build_options_panel.py` | Weekly 36-ticker panel with latest-prior quarterly capacity and IV diagnostics |
| `data/processed/options_screen/call_put_iv_diagnostic.csv` | `scripts/05_build_call_put_iv_diagnostic.py` | Quarterly matched call/put IV diagnostic |
| `data/processed/offline/core_panel.csv` | upstream fragility pipeline | Weekly returns, macro factors, rolling risk metrics for all core tickers |
| `data/raw/options_screen/` | options fetchers | Chain caches plus separate legacy call-only and combined call/put weekly IV caches |

## Universe

A predetermined 36-ticker fixed-income ETF universe is defined in
`src/data/options_universe.py`. The universe is not selected on option liquidity.
The separate `liquid` flag in `ticker_summary.csv` requires
`mean_pass_rate >= 0.25`.

## IV Panel Coverage

- Date range: 2020-01-03 through the available core-panel endpoint (`2026-04-24` in the current snapshot)
- Frequency: weekly (Fridays)
- Source: ThetaData gRPC API (`mdds-01.thetadata.us:443`)
- ATM selection: nearest expiry by distance to 30 DTE and a common near-ATM strike for calls and puts
- Quote quality: positive bid/ask and relative spread no greater than 35%
- Combination: median call/put IV when both sides pass, with call-only or put-only fallback
- BSM inversion: `scipy.optimize.brentq` using the right-specific Black-Scholes price
- Dividend yield: trailing 12-month sum of Yahoo Finance historical dividends divided by underlying close at each snap date (no lookahead)
- Risk-free rate: FRED DTB3 (3-month T-bill), using the nearest available prior observation
- Current panel: 18,058 weekly rows, including 5,886 valid IV observations

## Known Limitations

- Options screen is quarterly (22 configured snapshots); Greek and capacity metrics have limited time-series power
- IV panel coverage varies by ticker — analysis restricted to rows with `iv_30d` not NaN
- `vol_12w_annualized` is a trailing 12-week realized volatility measure from the core panel; it is available before 2020 because the core panel starts in 2016
- Open interest is not executable depth; capacity measures are optimistic upper bounds that omit price impact
