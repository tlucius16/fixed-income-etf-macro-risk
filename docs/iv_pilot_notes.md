# IV Pilot: Methodology and Data Provenance

This document describes the data source, construction methodology, and known limitations for the 2-ticker IV-subsumption pilot (HYG + LQD).  It mirrors the style of `docs/data_provenance.md`.

## Scope

This pilot is additive to the 347-ETF panel.  It does not modify `notebooks/02_*`, `notebooks/03_*`, or the main paper draft.

**In scope**: HYG (iShares iBoxx $ High Yield Corporate Bond ETF) and LQD (iShares iBoxx $ Investment Grade Corporate Bond ETF).

**Explicitly out of scope**: Extending to the full options-liquid fixed-income ETF universe (HYG, LQD, JNK, TLT, IEF, EMB, AGG, SHY, MUB, BKLN, SJNK) is future work.

---

## Data Source: ThetaData

- **Provider**: ThetaData ([thetadata.net](https://thetadata.net))
- **Tier**: OPTION.VALUE ($40/month, bundle: `STOCK.FREE, OPTION.VALUE, INDEX.FREE`)
- **Access mechanism**: ThetaData Python library v1.0.7+ (`pip install thetadata`), gRPC-based.  No Java terminal required.
- **Client initialisation**: `ThetaClient(email=..., password=..., dataframe_type="pandas")`

### Methods Used

| Method | Purpose |
|---|---|
| `client.option_list_expirations(ticker)` | Get all listed option expiries |
| `client.option_list_strikes(ticker, expiration)` | Get strike grid for a given expiry |
| `client.option_history_eod(start_date, end_date, symbol, expiration, strike, right)` | Retrieve end-of-day OHLC + bid/ask for a specific contract |

**Strike units**: Strikes are passed and returned in dollars (no millicent conversion required with the v1.0.7 gRPC library).

### Tier Limitations

The OPTION.VALUE tier does **not** provide:
- Pre-computed implied volatility → `PERMISSION_DENIED`
- Pre-computed Greeks → `PERMISSION_DENIED`
- Intraday quote/tick data

Consequently, IV is not retrieved directly from ThetaData but is instead computed from EOD option prices via Black-Scholes (see below).  The EOD response does include bid/ask alongside OHLC; the pipeline uses `(bid+ask)/2` when available, falling back to the EOD `close`.

Upgrading to ThetaData Standard ($80/month) would provide direct IV access and simplify the pipeline.

### Date Range

ThetaData OPTION.VALUE history is available from approximately 2012 (as evidenced by expirations returned for HYG).  The pilot uses **2022-01-07 onward** as the start date, aligning with the post-COVID rate-hike cycle.

---

## 30-Day ATM IV Construction

### Expiry Selection Rule

For each Friday observation date `t`:
1. Filter listed expirations to those strictly after `t`.
2. Select the expiry `T*` whose calendar distance from `t + 30 days` is minimised:

       T* = argmin_{T > t} |T - (t + 30d)|

### Strike Selection Rule

1. Retrieve the full listed strike grid for `T*` as of date `t`.
2. Select the strike `K*` that minimises the distance to the underlying EOD close price `S`:

       K* = argmin_{K in grid} |K - S|

3. If the EOD close for `(K*, T*, t)` is below `$0.01` (effectively zero, likely no trade), fall back to the next nearest strike (up to ±2 strikes) until a valid price is found.

**Side convention**: Call side only.  The call IV is used as the representative 30-day ATM IV for two reasons: (1) calls are typically more liquid than puts for broad bond ETFs in normal conditions, (2) a consistent convention across the sample simplifies the spread computation.  Note that by put-call parity, ATM call IV ≈ ATM put IV for European options; the approximation is good for short-tenor near-ATM contracts.

### Black-Scholes Implied Volatility Computation

IV is extracted numerically by inverting the Generalised Black-Scholes-Merton (BSM) formula for a European call with continuous dividend yield.

**Model**:

    C = S * exp(-q*T) * N(d1) - K * exp(-r*T) * N(d2)
    d1 = [ln(S/K) + (r - q + 0.5σ²)T] / (σ√T)
    d2 = d1 - σ√T

**Inputs**:

| Symbol | Description | Source |
|---|---|---|
| C | Option EOD close price | ThetaData (EOD endpoint) |
| S | Underlying ETF EOD close | yfinance daily close |
| K | Selected ATM strike (dollars) | ThetaData strike grid |
| T | Days-to-expiry / 365 | Computed from `T* - t` |
| r | Risk-free rate (annualised) | FRED DTB3 (`src.data.macro.fred_series`) |
| q | Continuous dividend yield | yfinance `dividendYield` info field (trailing 12-month, constant over sample) |

**Numerical solver**: `scipy.optimize.brentq` with σ bounds [0.0001, 20.0], convergence tolerances `xtol=rtol=1e-6`, max 200 iterations.

IV is set to `NaN` and the date is logged as skipped when:
- `C ≤ $0.01` (no valid price found near ATM)
- Option price is at or below intrinsic value (IV undefined)
- Brentq fails to bracket a root (deep OTM / near-expiry artefacts)
- No underlying price is available for that date

### Dividend Yield Approximation

The `dividendYield` field from `yfinance.Ticker.info` is the trailing 12-month dividend yield.  It is fetched once at build time and treated as a constant `q` over the full sample.  Approximate values as of mid-2026:

- HYG: ~5.5%
- LQD: ~3.3%

**Limitation**: A time-varying dividend yield would reduce BSM approximation error, particularly for dates when the ETF's distribution rate changed significantly.  The constant-yield approximation is standard for short-horizon research pilots.

---

## Annualisation Convention

`vol_12w` in the core panel is the **rolling standard deviation of weekly simple returns** over a 12-week backward-looking window (dimensionless weekly fraction, e.g. 0.004 ≈ 0.4% per week).

Options IV is quoted as an **annualised volatility** (e.g. 0.08 = 8% per year).

To make both series comparable, `vol_12w` is annualised by multiplying by √52:

    vol_12w_annualized = vol_12w * sqrt(52)

This assumes i.i.d. weekly returns (no autocorrelation scaling) — the same convention used implicitly in `rolling_risk.py`.

---

## Caching

Raw option data is cached to `data/raw/options/{ticker}/{YYYY-MM-DD}.json`, one file per (ticker, observation date).  Each file contains the full input set (S, K, T, r, q, C) alongside the computed IV so that any recomputation bug can be diagnosed without re-fetching from ThetaData.

---

## Output Panel

`data/processed/iv_pilot/iv_pilot_panel.csv` — HYG + LQD, weekly (Friday) dates from 2022-01-07 to the most recent build date.

Columns:

| Column | Description |
|---|---|
| `date` | Friday observation date |
| `ticker` | HYG or LQD |
| `vol_12w` | Rolling 12-week weekly return std (from core panel) |
| `vol_12w_annualized` | `vol_12w * sqrt(52)` |
| `iv_30d` | 30-day ATM call IV (Black-Scholes, annualised) |
| `iv_realized_spread` | `iv_30d - vol_12w_annualized` |
| `fwd_ret_4w` | Compound return over next 4 weeks (from core panel) |
| `fwd_maxdd_12w` | Max drawdown over next 12 weeks (from core panel, ≤ 0) |
| `fwd_vol_12w` | Return volatility over next 12 weeks (from core panel) |

---

## Known Limitations

1. **EOD close vs. mid-quote**: When the EOD response has bid>0, the pipeline uses `(bid+ask)/2`; otherwise it falls back to the last-transaction `close`.  For thinly-traded strikes the `close` may be stale relative to the true mid.

2. **European vs. American approximation**: HYG/LQD options are American-style.  The BSM (European) IV understates the true American IV by the early-exercise premium, which is non-trivial for high-yield calls when the underlying dividend yield is high (HYG ~5.5%).  For near-ATM, short-tenor contracts, the difference is small (~1-2 vol points).

3. **Constant dividend yield**: As noted above, a time-varying `q` would be more accurate but adds pipeline complexity.

4. **2-ticker pilot power**: With ~200 weekly observations per ticker, the regression power is limited.  Statistical insignificance in the joint spec (3) does not rule out an economically meaningful relationship in a larger panel.

5. **ThetaData tier**: The OPTION.VALUE tier provides EOD data but not intraday quotes.  The EOD close may not reflect the closing mid if the last trade was well before market close.

6. **No data gaps imputation**: Dates where no valid EOD option price is found near ATM are left as `NaN` in `iv_30d`.  These are logged during the build and are typically low-volume contract-date combinations.
