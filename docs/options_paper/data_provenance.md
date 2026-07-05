# Data Provenance — Options Paper

## Input Files

| File | Script | Description |
|---|---|---|
| `data/processed/options_screen/ticker_summary.csv` | `scripts/02_run_options_screen.py` | Per-ticker liquidity screen metrics (22–24 quarterly snap dates, 2020–2025) |
| `data/processed/options_screen/chains.csv` | `scripts/02_run_options_screen.py` | Full option chain rows with BSM Greeks per (ticker, snap_date, expiry, strike) |
| `data/processed/options_screen/summary.csv` | `scripts/02_run_options_screen.py` | Aggregated per (ticker, snap_date): pass_rate, median Greeks |
| `data/processed/options_screen/iv_panel_full.csv` | `scripts/03_build_iv_panel.py` | Weekly (Friday) ATM 30-day IV merged with realized vol and forward outcomes |
| `data/processed/offline/core_panel.csv` | upstream fragility pipeline | Weekly returns, macro factors, rolling risk metrics for all core tickers |
| `data/raw/options/` | `scripts/03_build_iv_panel.py` | Per (ticker, date) JSON cache; stores option_price, strike, underlying_close, rf_annual, div_yield, iv_30d |

## Universe

36 tickers with `mean_pass_rate >= 0.50` across quarterly snap dates.
Liquid classification lives in `ticker_summary.csv` (`liquid` column).
The `src/options_paper/universe.py` module maps each ticker to a category and duration bucket for cross-sectional analysis.

## IV Panel Coverage

- Date range: 2020-01-03 through the available core-panel endpoint (`2026-04-24` in the current snapshot)
- Frequency: weekly (Fridays)
- Source: ThetaData gRPC API (`mdds-01.thetadata.us:443`)
- ATM selection: nearest-expiry option with DTE closest to 30 days; candidate strikes are searched by distance from underlying; mid-quote pricing with close-price fallback
- BSM inversion: `scipy.optimize.brentq` on Black-Scholes call price
- Dividend yield: trailing 12-month sum of Yahoo Finance historical dividends divided by underlying close at each snap date (no lookahead)
- Risk-free rate: FRED DTB3 (3-month T-bill), using the nearest available prior observation
- 22 of 36 tickers achieve >=70% fill rate over the 2020-onward IV window in the current snapshot

## Known Limitations

- Options screen is quarterly (24 snap dates in the current processed snapshot); Greek-based metrics have limited time-series power
- IV panel coverage varies by ticker — analysis restricted to rows with `iv_30d` not NaN
- `vol_12w_annualized` is a trailing 12-week realized volatility measure from the core panel; it is available before 2020 because the core panel starts in 2016
