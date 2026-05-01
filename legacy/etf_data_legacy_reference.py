##%%
#Importing libraries
import yfinance as yf
import matplotlib.pyplot as plt
import numpy as np
import datetime
import pandas as pd

#%%

database = pd.read_csv('/Users/ya/Downloads/etfdb_screener.csv', skiprows=1)
print(database.head())
database.Symbol.count()

#%%

database.Symbol.count()
keep_cols = ['Symbol', 'Name', 'Assets', 'ETF Database Category', 'ER', 'Inception']
etf_metadata = database[keep_cols].set_index('Inception').sort_index()
etf_cats = etf_metadata[['Symbol','ETF Database Category']]

print(etf_metadata.isna().sum())

#%%
ticker_list = database.Symbol.dropna().str.upper().str.replace('.', '-').unique().tolist()
print(len(ticker_list))

#%%
import time

min_years = 5
min_days = min_years * 365
valid_tickers, invalid_tickers = [], []
etf_prices_data = {}

for i, ticker in enumerate(ticker_list):
    if i and i % 50 == 0:
        print(f"Checked {i} tickers…")
    try:
        data = yf.Ticker(ticker).history(period="max", interval="1d", auto_adjust = True)['Close']
        if data.empty:
            invalid_tickers.append(ticker); continue
        history_span = (data.index.max() - data.index.min()).days
        (valid_tickers if history_span >= min_days else invalid_tickers).append(ticker)
        if history_span >= min_days:
            etf_prices_data[ticker] = data
    except Exception as e:
        print(f"[yfinance] {ticker}: {e}")
        invalid_tickers.append(ticker)
    time.sleep(0.12)  # be nice to Yahoo

print(f"Valid tickers : {len(valid_tickers)}")
print(f"Invalid tickers: {len(invalid_tickers)}")

#%%Converting the dictionary of price series into a DataFrame for analysis

raw_prices = pd.DataFrame(etf_prices_data)

raw_prices.index = pd.to_datetime(raw_prices.index, errors="coerce", utc=True).tz_localize(None)
raw_prices = raw_prices[raw_prices.index.notna()].sort_index()
raw_prices.index.name = "Date"

returns = raw_prices.pct_change()  # daily returns
weekly_prices = raw_prices.resample("W-FRI").last()
returns_w = weekly_prices.pct_change()

returns_w_long = (
    returns_w
    .reset_index()
    .melt(id_vars="Date", var_name="Ticker", value_name="Return")
    .dropna(subset=["Return"])
    .sort_values(["Ticker", "Date"])
    .reset_index(drop=True)
)

#%%
# Monte Carlo VaR
import numpy as np
import matplotlib.pyplot as plt


excess_returns = returns - returns.mean()
expected_return = returns.mean()
volatility = returns.std()
var_covariance =  excess_returns.cov()
corr_matrix = returns.corr()

port_value = 100000000
weights = np.array([1 / len(valid_tickers)] * len(valid_tickers))
port_return = (expected_return * weights).sum()
daily_returns = returns @ weights
port_volatility = (weights @ var_covariance @ weights) ** 0.5

num_simulations = 5000
alpha = 0.10

# simulate returns for each asset and aggregate to portfolio returns
simulated_returns = np.random.multivariate_normal(expected_return, var_covariance, num_simulations)
simulated_port_returns = simulated_returns @ weights  # unit: returns (not dollars)

# VaR: percentile in return units, then scale to dollar amount
var_pct = np.percentile(simulated_port_returns, alpha * 100)
var_amount = -var_pct * port_value

# Expected Shortfall (Conditional VaR): mean of returns below the VaR percentile
mask = simulated_port_returns <= var_pct
if mask.any():
    es_amount = -simulated_port_returns[mask].mean() * port_value
else:
    # edge case: no simulated returns fall below the percentile (very unlikely)
    # fall back to VaR amount to avoid empty-slice mean and RuntimeWarning
    es_amount = var_amount

print(f"Estimated 1-day VaR at {int((1 - alpha) * 100)}% confidence: ${var_amount:,.2f}")
print(f"Estimated Expected Shortfall at {int((1 - alpha) * 100)}% confidence: ${es_amount:,.2f}")

count = daily_returns.count()
breaches = (daily_returns <= var_pct).sum()
expected_breaches = (alpha) * count
print(f"Number of breaches in historical data: {breaches} out of {count} days")
print(f"Number of expected breaches in historical data: {round(expected_breaches, 2 )} out of {count} days")

plt.hist(simulated_port_returns, bins=50, alpha=0.7, color='blue', edgecolor='black')
plt.axvline(var_pct, color='red', linestyle='dashed', linewidth=2, label=f'VaR ({1-alpha}%)')
plt.title('Simulated Portfolio Returns Distribution')
plt.xlabel('Return')
plt.ylabel('Frequency')
plt.legend()
plt.show()

#%% Getting GPR data from Matteo Iacoviello's website

import pandas as pd

daily_gpr_url = "https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.xls"

gpr_daily = pd.read_excel(daily_gpr_url, index_col='date')
gpr_daily.columns = [str(c).strip() for c in gpr_daily.columns]
print(gpr_daily.head(10))
print(gpr_daily.columns)

# %% Pulling macroeconomic risk factor data from FRED using their API, with robust error handling and retry logic to ensure data retrieval is reliable even in the face of transient network issues or API rate limits.


import pandas as pd
import numpy as np
import requests
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

FRED_API_KEY = "513356fae3c33350e96139f547834d8e"

def make_fred_session():
    session = requests.Session()
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

session = make_fred_session()

def safe_get_json(url, params=None, sleep_sec=0.25, timeout=30):
    time.sleep(sleep_sec)
    r = session.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()

def fred_series(series_id: str) -> pd.DataFrame:
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
    }
    data = safe_get_json(url, params=params)
    obs = data.get("observations", [])

    df = pd.DataFrame(obs)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df[["date", "value"]].dropna().sort_values("date").reset_index(drop=True)

# Risk factor
anfci = fred_series("ANFCI").rename(columns={"date": "Date", "value": "ANFCI"})

# Credit spread
baml = fred_series("BAMLC0A0CM").rename(columns={"date": "Date", "value": "BAML_C0A0CM"})

# Interest rate
dgs10 = fred_series("DGS10").rename(columns={"date": "Date", "value": "DGS10"})
t10y2y = fred_series("T10Y2Y").rename(columns={"date": "Date", "value": "T10Y2Y"})

# Inflation
inflation = fred_series("T5YIE").rename(columns={"date": "Date", "value": "T5YIE"})

# %%
#Getting VIX Data

vix = yf.Ticker("^VIX").history(period="10y", interval="1d", auto_adjust = True)['Close']
move = yf.Ticker("^MOVE").history(period="10y", interval="1d", auto_adjust = True)['Close']

# %%
#Converting macro data to weekly frequency to match ANCFI data

def to_weekly_friday(df, value_col):
    out = df.copy()
    out["Date"] = pd.to_datetime(out["Date"], errors="coerce", utc=True).dt.tz_localize(None)
    out = out.dropna(subset=["Date"])
    out = out.set_index("Date").sort_index()
    out = out[[value_col]].resample("W-FRI").last().dropna().reset_index()

    # safety: force unique Friday rows
    out = out.drop_duplicates(subset="Date", keep="last").reset_index(drop=True)
    return out

anfci_w = to_weekly_friday(anfci, "ANFCI")     # already weekly Friday, but keeps format consistent
dgs10_w = to_weekly_friday(dgs10, "DGS10")
infl_w  = to_weekly_friday(inflation, "T5YIE")
baml_w  = to_weekly_friday(baml, "BAML_C0A0CM")
t10y2y_w = to_weekly_friday(t10y2y, "T10Y2Y")
move_w  = to_weekly_friday(move.reset_index().rename(columns={"index": "Date", "Close": "MOVE"}), "MOVE")
vix_w   = to_weekly_friday(vix.reset_index().rename(columns={"index": "Date", "Close": "VIX"}), "VIX")
gpr_w   = to_weekly_friday(gpr_daily.reset_index().rename(columns={"date": "Date", "GPRD": "GPR"}), "GPR")


# %% creating weekly differences for all risk factors to capture changes in the risk environment

for df, col in [
    (anfci_w, "ANFCI"),
    (dgs10_w, "DGS10"),
    (infl_w, "T5YIE"),
    (baml_w, "BAML_C0A0CM"),
    (t10y2y_w, "T10Y2Y"),
    (move_w, "MOVE"),
    (vix_w, "VIX"),
    (gpr_w, "GPR")
]:
    df[f"d_{col}"] = df[col].diff()
    #df.dropna(inplace=True)
    #dropping the original level columns to focus on changes, which are more relevant for risk modeling
    #df.drop(columns=[col], inplace=True)

#%% Merging all risk factor data into a single DataFrame for analysis

from functools import reduce

dfs = [anfci_w, dgs10_w, infl_w, baml_w, t10y2y_w, move_w, vix_w, gpr_w]

macro_factors = reduce(
    lambda left, right: pd.merge(left, right, on="Date", how="inner"),
    dfs
)

macro_factors = (
    macro_factors
    .drop_duplicates(subset="Date", keep="last")
    .sort_values("Date")
    .reset_index(drop=True)
)

print(macro_factors.head())
print(macro_factors["Date"].duplicated().sum())

#%% Merging the weekly returns of the ETFs with the macroeconomic risk factors to create a comprehensive dataset for analysis

full_panel = pd.merge(
    returns_w_long,
    macro_factors,
    on="Date",
    how="inner"
).sort_values(["Ticker", "Date"]).reset_index(drop=True)

# %% Merging metadata as well 

etf_metadata_clean = etf_metadata.reset_index()
etf_metadata_clean["Symbol"] = etf_metadata_clean["Symbol"].str.upper().str.replace(".", "-", regex=False)

full_panel_m = pd.merge(
    full_panel,
    etf_metadata_clean,
    left_on="Ticker",
    right_on="Symbol",
    how="left"
).sort_values(["Ticker", "Date"]).reset_index(drop=True)

# %% Sanity Check

full_panel_m.groupby("Date")["Ticker"].nunique().head()

# %%
full_panel_m["Inception"] = pd.to_datetime(full_panel_m["Inception"], errors="coerce")
full_panel_m["age_years"] = (full_panel_m["Date"] - full_panel_m["Inception"]).dt.days / 365

# %%

full_panel_m["Assets"] = (
    full_panel_m["Assets"]
    .astype(str)
    .str.replace(r"[$,]", "", regex=True)
)

full_panel_m["Assets"] = pd.to_numeric(full_panel_m["Assets"], errors="coerce")

full_panel_m["ER"] = (
    full_panel_m["ER"]
    .astype(str)
    .str.replace("%", "", regex=False)
)

full_panel_m["ER"] = pd.to_numeric(full_panel_m["ER"], errors="coerce")

# %% Risk-free rate and excess returns
rf = fred_series("DTB3").rename(columns={"date": "Date", "value": "DTB3"})
rf_w = to_weekly_friday(rf, "DTB3")

# annualized percent yield -> approximate weekly decimal return
rf_w["RF_w"] = (rf_w["DTB3"] / 100) / 52

full_panel_m = (
    pd.merge(full_panel_m, rf_w[["Date", "RF_w"]], on="Date", how="left")
    .sort_values(["Ticker", "Date"])
    .reset_index(drop=True)
)

full_panel_m["RET_XS"] = full_panel_m["Return"] - full_panel_m["RF_w"]

print("RF missing pct:", full_panel_m["RF_w"].isna().mean())
# %%

from pathlib import Path
import pandas as pd

output_dir = Path("saved_pandas_objects")
output_dir.mkdir(parents=True, exist_ok=True)

all_objs = {
    name: obj
    for name, obj in globals().items()
    if isinstance(obj, (pd.DataFrame, pd.Series))
}

for name, obj in all_objs.items():
    if isinstance(obj, pd.Series):
        obj.to_frame(name=name).to_csv(output_dir / f"{name}.csv", index=True)
    else:
        obj.to_csv(output_dir / f"{name}.csv", index=True)

print(f"Saved {len(all_objs)} pandas objects to: {output_dir.resolve()}")
print("Saved objects:", sorted(all_objs.keys()))
# %%
