# Fresh liquid-ticker option pull on Windows

This is a new raw acquisition, separate from the preserved study and from the
later universe screen. Run it on the Windows machine with the upgraded ThetaData
account. The Mac cannot inspect or launch that machine's existing pull.

## Scope

- **Default tickers:** EDV, EMB, IEF, LQD, TIP, TLT, VCLT, ZROZ. These eight names
  are flagged `liquid=True` in the Mac's current
  `data/processed/options_screen/ticker_summary.csv`. Earlier prose says six;
  this explicit list follows the file, not that older count. It is a historical
  selection, not a newly verified liquid universe. Override `--tickers` if the
  Windows screen has a different agreed list; do not silently change it mid-run.
- **Pilot:** LQD/TLT/IEF on 2020-04-01, 2025-01-02, and 2026-09-11. These cover
  an older observation, the disputed study menu, and a recent completed session.
- **Full pull:** every weekday from 2020-01-02 through 2026-09-11 inclusive.
  Holidays are attempted and retained as `no_data`, not silently moved to a
  different date. This weekday schedule is not a certified exchange calendar.
- Both calls and puts, all strikes and all expirations. No bid, spread, OI,
  moneyness, IV or Greek screen during acquisition. Optional `--max-dte 90`
  restricts the request horizon, but then it is not an all-expiration book.
- Separate EOD quote and OI files; `--greeks` adds separate vendor EOD Greeks.
  Missing IV never removes an EOD quote. Missing OI stays distinct from zero.
- One ticker/date/endpoint per request, sequentially, with bounded transient
  retries. No per-contract synthetic fallback or substitution.

The legacy `fetch_full_chain` skips rows with missing implied volatility and
reuses existing caches. Use this collector for fresh evidence instead.

## 1. Copy and install

Copy `scripts/pull_liquid_options.py` and this guide to the Windows checkout,
preserving their relative paths. No other project modules are needed. Run the
following from that checkout in PowerShell (Python 3.12 shown):

```powershell
py -3.12 -m venv .venv-theta-pull
.\.venv-theta-pull\Scripts\python.exe -m pip install --upgrade pip
.\.venv-theta-pull\Scripts\python.exe -m pip install --upgrade pandas requests thetadata
```

The default uses the current Python SDK's `ThetaClient(email=..., password=...,
dataframe_type="pandas")`. Credentials come from `THETADATA_USERNAME` and
`THETADATA_PASSWORD`, or interactive prompts; the password prompt is hidden.
Credentials and raw exception messages are not written to the result bundle.

If your working Windows setup uses **Theta Terminal v3 REST**, start and log in
to that terminal as usual, and append `--backend rest` to each command. Default
base URL: `http://127.0.0.1:25503/v3`; override with `--base-url` if needed.
The SDK path does not use the local terminal. No v2 compatibility is assumed.

## 2. Inspect the plan, then run the pilot

```powershell
.\.venv-theta-pull\Scripts\python.exe scripts\pull_liquid_options.py --output data\raw\hedge_design\theta-liquid-pilot-20260914 --tickers LQD TLT IEF --dates 2020-04-01 2025-01-02 2026-09-11 --greeks --dry-run
.\.venv-theta-pull\Scripts\python.exe scripts\pull_liquid_options.py --output data\raw\hedge_design\theta-liquid-pilot-20260914 --tickers LQD TLT IEF --dates 2020-04-01 2025-01-02 2026-09-11 --greeks
```

The pilot makes 27 requests. Inspect `coverage.csv` and individual endpoint JSON
records. Before the long run, confirm EOD, OI and Greeks return data on the known
study date, and inspect LQD's January 31, 2025 expiration for the near-ATM menu.
Compare quote keys against OI keys; preserve unmatched records. A successful
request does not certify that every contract is covered or executable.

Access denial stops with exit code 2 and `permission_denied`; it is not an empty
market. If Greeks are not entitled, the quote/OI files already collected remain
safe. Fix the entitlement and resume, or deliberately start a new folder without
`--greeks` and label the narrower scope. Unknown/schema errors also stop the run.

## 3. Pull the full history after inspecting the pilot

```powershell
.\.venv-theta-pull\Scripts\python.exe scripts\pull_liquid_options.py --output data\raw\hedge_design\theta-liquid-daily-20260914 --start 2020-01-02 --end 2026-09-11 --greeks --dry-run
.\.venv-theta-pull\Scripts\python.exe scripts\pull_liquid_options.py --output data\raw\hedge_design\theta-liquid-daily-20260914 --start 2020-01-02 --end 2026-09-11 --greeks
```

With the defaults above, the plan contains 1,747 weekdays and 41,928 requests
including Greeks (27,952 without Greeks). Request count is printed before
connecting. All-expiration daily pulls can be
large; inspect the pilot's elapsed time and file sizes before estimating storage
or duration. No runtime estimate or upgraded-tier coverage is assumed.

To resume after interruption, rerun the **same command**. Successful partitions
are checksum-verified and reused; failed partitions are retried. Add
`--retry-empty` to reattempt saved `no_data` responses. A changed ticker/date/
endpoint/DTE/backend plan or collector source requires a new output directory.
Use one process per output directory. Do not edit, merge or delete saved parts.

Exit 0 means all planned requests reached `ok` or `no_data`, **not** that the
dataset is complete. Review no-data dates against an exchange calendar and
compare availability across endpoints/tickers before promoting the data.

## 4. Return the evidence bundle

Each folder contains:

```text
manifest.json                         scope, source hash, versions, run status
coverage.csv                          latest invocation's request status/row counts
LQD/2025-01-02/eod.csv.gz              all returned quote fields, including sizes
LQD/2025-01-02/eod.json                exact request, retrieval time, SHA-256
LQD/2025-01-02/open_interest.csv.gz    independent OI observations and timestamps
LQD/2025-01-02/open_interest.json
LQD/2025-01-02/greeks_eod.csv.gz       optional independent Greek observations
LQD/2025-01-02/greeks_eod.json
```

The CSVs preserve returned columns and rows in portable CSV form, not the wire
encoding. Nulls are blank CSV fields; numeric zero remains zero. There is no
quote/OI inner join, fill-forward, timezone conversion or timestamp shifting.
Per-endpoint JSON files are the authoritative resume records. On an interrupted
resume, `coverage.csv` describes only requests visited in that invocation.

Copy the complete pilot and daily folders back to the Mac, together with the
exact collector used. For large bundles use a shared folder or an archive tool
that supports the resulting size; the files are already gzip-compressed. Keep
the existing Windows outputs too. Do not replace the pinned `chains.csv`, alter
`study_config.json`, or regenerate paper conclusions during this pull.

Next validation on the Mac: compare overlapping exact contracts with the old
snapshot, explain missing near-ATM LQD quotes, inspect OI timestamp semantics,
identify endpoint gaps/duplicates and spot mismatches, then build a separately
pinned analysis dataset. Underlying price/distribution updates, issuer-action
checks and deliverable verification are separate from this option-only pull.

## Timestamp interpretation and API references

ThetaData documents EOD reports as generated at 17:15 ET, with `created` holding
report-generation time and `last_trade` holding the last trade time. The reported
quote is the last NBBO at report generation; `created` is not the last quote's
event timestamp. This is EOD research data, not a certified executable 16:00 quote.
[EOD documentation](https://docs.thetadata.us/operations_python/option_history_eod.html)

OI normally arrives around 06:30 ET and represents the previous trading day's
closing OI. An absent OI message must not be converted into a measured zero.
[OI documentation](https://docs.thetadata.us/operations_python/option_history_open_interest.html)

The EOD Greeks endpoint supports wildcard expirations with day-by-day requests.
Vendor dividend/rate/model defaults remain vendor assumptions in this raw pull.
[Greeks documentation](https://docs.thetadata.us/operations_python/option_history_greeks_eod.html)

The optional REST adapter targets the documented v3 CSV endpoint.
[REST EOD documentation](https://docs.thetadata.us/operations/option_history_eod.html)

Local automated checks use simulated responses. Live entitlement, the Windows
runtime, and actual returned schemas must be confirmed by the pilot.
