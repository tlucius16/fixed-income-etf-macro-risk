"""Build a chains.csv-shaped option panel from scripts/pull_liquid_options.py output.

Offline: reads only completed partitions already on disk under one or more pull
directories. Never fetches, never touches the pinned data/processed/options_screen/
tree the active study reads.

Two screens coexist here, selected by ``build_and_write(..., screen_version=...)``:

- **v1** (``contract_quality`` / ``ticker_summary``, default): the per-contract
  tradeability mask and composite liquidity score ported unchanged from
  legacy/unified/src/data/options.py (``screen_chain`` / ``_build_ticker_summary``).
  Kept as-is, byte-for-byte, so existing v1 outputs stay reproducible.
- **v2** (``quote_eligibility`` / ``strategy_scope`` / ``oi_status`` /
  ``liquidity_profile`` / ``oi_capped_put_menu``): a revised screen that keeps
  quote eligibility (bid/ask/spread), strategy scope (DTE/delta), and OI-based
  sizing as three separate, independently inspectable dimensions instead of one
  fused mask; drops the dollar-greek floors (shown empirically inert on this
  instrument class) and the call/put balance gate (shown to zero out genuine
  one-sided put depth). It has **no composite score and no liquidity flag** --
  a median across a handful of sparse dates answers a different question than
  "is a particular hedge feasible on a particular date," so ``liquidity_profile``
  returns the per-date diagnostics directly and stops there.

Recorded-OI epistemic note (applies to every v2 function): ``oi_status`` and
everything built on it describe what the vendor feed *recorded*, not the true
state of the market. Zero recorded OI is a specific, positive claim (open
interest was reported and was zero); missing OI is unknown, never treated as
zero or as positive. Two pulls agreeing does not independently validate OI if
they share an upstream provider -- it establishes reproducibility of that
provider's feed, nothing more.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

import numpy as np
import pandas as pd

from src.data.hedge_inputs import quote_flags, sha256_file

CONTRACT_KEY = ["expiration", "strike", "right"]
CHAIN_KEY = ["ticker", "snap_date", "expiry", "strike", "right"]
RIGHT_MAP = {"PUT": "P", "CALL": "C"}
CONTRACT_MULTIPLIER = 100  # OCC-standard deliverable shares; matches contract_terms.multiplier

# Ported from legacy/unified/src/config.py and .../data/options_universe.py.
MAX_REL_SPREAD = 0.35
DTE_MIN, DTE_MAX = 14, 90
DELTA_LO, DELTA_HI = 0.10, 0.90
MIN_DOLLAR_DELTA = 5.0
MIN_DOLLAR_GAMMA = 0.001
MIN_DOLLAR_VEGA = 0.01
LIQUIDITY_SCORE_MIN = 100.0
IV_ERROR_ANOMALY_THRESHOLD = 0.05  # diagnostic only; not part of the ported quality mask

CHAIN_COLUMNS = ["ticker", "snap_date", "expiry", "strike", "right", "underlying",
                 "bid", "ask", "open_interest"]
GREEK_COLUMNS = ["delta", "gamma", "vega", "theta", "implied_vol", "iv_error"]


def _read_endpoint(directory: Path, endpoint: str) -> pd.DataFrame:
    path = directory / f"{endpoint}.csv.gz"
    return pd.read_csv(path) if path.is_file() else pd.DataFrame()


def _require_unique_key(frame: pd.DataFrame, source: Path) -> None:
    if frame.duplicated(CONTRACT_KEY).any():
        raise ValueError(f"Duplicate (expiration, strike, right) key in {source}")


def _dedupe_oi(oi: pd.DataFrame, source: Path) -> pd.DataFrame:
    """Collapse an OI file's duplicate (expiration, strike, right) keys.

    Rare in practice -- 10 of 20,073 files in the first full 2016-2026 pull,
    all apparently repeated same-day OI publications -- and, in every instance
    checked, every duplicate row agrees on ``open_interest``. Collapsing is
    safe only because that agreement is verified here, not assumed: a key
    whose duplicate rows disagree raises, the same as any other duplicate this
    module can't explain away. EOD and Greeks files never showed this pattern
    (0 of ~20,000 and ~18,800 files respectively) -- only OI gets this check.
    """
    if not oi.duplicated(CONTRACT_KEY, keep=False).any():
        return oi
    disagreement = oi.groupby(CONTRACT_KEY)["open_interest"].nunique(dropna=False)
    conflicting = disagreement[disagreement > 1]
    if len(conflicting):
        raise ValueError(f"Conflicting open_interest for duplicate key(s) in {source}: "
                         f"{conflicting.index.tolist()}")
    return oi.drop_duplicates(CONTRACT_KEY, keep="last")


def load_partition(ticker_dir: Path, snap_date: str) -> pd.DataFrame | None:
    """One ticker/date pull partition, joined and ready for scoring; ``None`` if unpulled.

    EOD is required; open interest is left-joined so a missing OI record becomes
    an explicit NaN, never a filled zero. ``underlying`` comes from the Greeks
    file's ``underlying_price`` (one spot per ticker/date, not per contract)
    rather than a separate price series -- a ticker/date with EOD (and often
    OI) but no Greeks at all is skipped entirely (returns ``None``, same as an
    unpulled date), since there is then no verified spot to build it from.
    """
    directory = ticker_dir / snap_date
    eod = _read_endpoint(directory, "eod")
    if eod.empty:
        return None
    _require_unique_key(eod, directory / "eod.csv.gz")
    unknown_rights = set(eod["right"].unique()) - set(RIGHT_MAP)
    if unknown_rights:
        raise ValueError(f"Unexpected option right values in {directory}: {sorted(unknown_rights)}")

    frame = eod[CONTRACT_KEY + ["bid", "ask"]].copy()

    oi = _read_endpoint(directory, "open_interest")
    if not oi.empty:
        oi = _dedupe_oi(oi, directory / "open_interest.csv.gz")
        frame = frame.merge(oi[CONTRACT_KEY + ["open_interest"]], on=CONTRACT_KEY, how="left")
    else:
        frame["open_interest"] = np.nan

    greeks = _read_endpoint(directory, "greeks_eod")
    if greeks.empty:
        # A quote (and often OI) can exist with no Greeks at all for that ticker/date --
        # observed for a full trading year (2016) on 5 of 8 tickers in the first full
        # 2016-2026 pull, apparently before ThetaData's Greeks coverage for them began,
        # not an acquisition mistake. Skip this one partition, same as an unpulled date;
        # do not abort the whole multi-year build over it. If --greeks was never used for
        # the entire pull, every partition hits this path and assemble_partitions's
        # "No completed partitions found" check still catches that degenerate case.
        return None
    _require_unique_key(greeks, directory / "greeks_eod.csv.gz")
    spots = greeks["underlying_price"].dropna().unique()
    if len(spots) != 1:
        raise ValueError(f"Non-constant or missing underlying_price in {directory}: {sorted(spots)}")
    available = [c for c in GREEK_COLUMNS if c in greeks.columns]
    frame = frame.merge(greeks[CONTRACT_KEY + available], on=CONTRACT_KEY, how="left")
    for column in GREEK_COLUMNS:
        if column not in frame.columns:
            frame[column] = np.nan

    frame["ticker"] = eod["symbol"].iloc[0]
    frame["snap_date"] = snap_date
    frame["expiry"] = frame["expiration"]
    frame["right"] = frame["right"].map(RIGHT_MAP)
    frame["underlying"] = float(spots[0])
    return frame.drop(columns=["expiration"])


def assemble_partitions(pull_roots: list[Path]) -> pd.DataFrame:
    """Every completed ticker/date partition across one or more pull directories.

    Not yet a lean chains.csv frame -- retains Greek columns needed for the
    liquidity screen. Raises on a contract key duplicated across pull directories
    (use disjoint ticker/date plans, not overlapping re-pulls, across roots).
    """
    frames = []
    for root in pull_roots:
        manifest = json.loads((root / "manifest.json").read_text())
        for ticker in manifest["plan"]["tickers"]:
            ticker_dir = root / ticker
            if not ticker_dir.is_dir():
                continue
            for snap_date in manifest["plan"]["dates"]:
                partition = load_partition(ticker_dir, snap_date)
                if partition is not None:
                    frames.append(partition)
    if not frames:
        raise ValueError("No completed partitions found across the given pull directories")
    panel = pd.concat(frames, ignore_index=True)
    if panel.duplicated(CHAIN_KEY).any():
        raise ValueError("Duplicate contract key across pull directories")
    return panel


def lean_chains(panel: pd.DataFrame) -> pd.DataFrame:
    """The chains.csv schema hedge_inputs.load_chains validates: full chain, no gate."""
    return panel[CHAIN_COLUMNS].sort_values(CHAIN_KEY).reset_index(drop=True)


def contract_quality(panel: pd.DataFrame) -> pd.DataFrame:
    """Per-contract tradeability + economic-significance mask.

    Ported unchanged from legacy/unified/src/data/options.py:screen_chain. Every
    contract-day is scored independently against fixed thresholds; nothing here is
    fit to this sample.
    """
    work = panel.copy()
    bid, ask = work["bid"].fillna(0), work["ask"].fillna(0)
    mid = (bid + ask) / 2
    work["mid"] = mid
    work["rel_spread"] = (ask - bid) / mid.replace(0.0, np.nan)
    work["dte"] = (pd.to_datetime(work["expiry"]) - pd.to_datetime(work["snap_date"])).dt.days
    work["abs_delta"] = work["delta"].abs()
    work["dollar_delta"] = work["delta"] * work["underlying"]
    work["dollar_gamma"] = 0.5 * work["gamma"] * work["underlying"] ** 2 * 0.01 ** 2
    work["dollar_vega"] = work["vega"] * 0.01
    work["quality"] = (
        (bid > 0) & (ask > 0) & (mid > 0)
        & (work["rel_spread"] <= MAX_REL_SPREAD)
        & work["dte"].between(DTE_MIN, DTE_MAX)
        & work["abs_delta"].between(DELTA_LO, DELTA_HI)
        & (work["dollar_delta"].abs() >= MIN_DOLLAR_DELTA)
        & (work["dollar_gamma"] >= MIN_DOLLAR_GAMMA)
        & (work["dollar_vega"] >= MIN_DOLLAR_VEGA)
    )
    return work


def ticker_summary(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per-(ticker, snap_date) liquidity screen and the ticker-level ``liquid`` gate.

    Ported unchanged from legacy/unified/src/data/options.py:_build_ticker_summary.
    ``liq_score`` = sqrt(quality OI premium notional) x (1 - median quote spread) x
    call/put book balance; a ticker is ``liquid`` once its median liq_score across
    the scored dates clears ``LIQUIDITY_SCORE_MIN``. ``anomalous_iv_error_rows`` is
    a new diagnostic (not part of the ported gate): ThetaData's ``iv_error`` field
    is undocumented beyond "model vs. quoted value"; some rows carry values wildly
    outside the near-zero range everything else takes, so the count is surfaced for
    manual review rather than silently trusted or silently dropped.
    """
    work = contract_quality(panel)
    passing = work[work["quality"]].copy()
    group = ["ticker", "snap_date"]

    total = work.groupby(group).size().rename("total_contracts")
    n_pass = passing.groupby(group).size().rename("passing_contracts")
    oi = passing["open_interest"].fillna(0).clip(lower=0)
    passing["oi_premium_notional"] = oi * CONTRACT_MULTIPLIER * passing["mid"]
    notional = passing.groupby(group)["oi_premium_notional"].sum()
    side = (passing.groupby(group + ["right"])["oi_premium_notional"].sum()
            .unstack("right").reindex(columns=["C", "P"]).fillna(0.0))
    both = side["C"] + side["P"]
    balance = (2.0 * side[["C", "P"]].min(axis=1) / both.replace(0.0, np.nan)).fillna(0.0)
    spread_med = passing.groupby(group)["rel_spread"].median()
    anomalous = work.groupby(group)["iv_error"].apply(
        lambda s: int((s.abs() > IV_ERROR_ANOMALY_THRESHOLD).sum()))

    summary = (pd.concat([total, n_pass], axis=1).fillna({"passing_contracts": 0})
              .join(pd.DataFrame({"quality_oi_notional": notional, "book_balance": balance,
                                  "median_quality_spread": spread_med,
                                  "anomalous_iv_error_rows": anomalous}), how="left")
              .reset_index())
    summary["sqrt_oi_notional"] = summary["quality_oi_notional"].pow(0.5)
    summary["liq_score"] = (summary["sqrt_oi_notional"]
                            * (1.0 - summary["median_quality_spread"]).clip(lower=0.0)
                            * summary["book_balance"])
    summary["pass_rate"] = (summary["passing_contracts"] / summary["total_contracts"]).round(4)

    ticker_level = summary.groupby("ticker").agg(
        dates_screened=("snap_date", "count"), mean_pass_rate=("pass_rate", "mean"),
        median_liq_score=("liq_score", "median")).reset_index()
    ticker_level["liquid"] = ticker_level["median_liq_score"].fillna(0.0) >= LIQUIDITY_SCORE_MIN
    return summary, ticker_level


# ---------------------------------------------------------------------------
# v2: quote eligibility, strategy scope, and OI-based sizing kept separate.
# ---------------------------------------------------------------------------

def quote_eligibility(panel: pd.DataFrame) -> pd.Series:
    """Pure tradeability: a valid, non-crossed two-sided quote within a bounded
    relative spread, on a finite positive spot/strike and a real, unexpired put/call.

    Delegates to ``hedge_inputs.quote_flags`` (the same screen ``chains.csv``
    consumers already trust) rather than reimplementing it: a naive
    ``rel_spread <= max`` check alone lets a crossed quote (ask < bid) through,
    since a negative spread trivially satisfies "<= 0.35". ``quote_flags``
    catches that explicitly, plus nonfinite quotes and invalid spot/strike/
    right/expiration -- all real tradeability conditions, not scope choices.

    No strategy scope (DTE/delta), no dollar-greek floor, no OI requirement --
    those are separate, independently inspectable questions (see
    ``strategy_scope``, ``oi_status``, ``oi_capped_size``). A contract can be
    quote-eligible and still sit outside this study's scope, or have no
    recorded interest; neither changes whether the quote itself is tradeable.
    """
    return quote_flags(panel, max_rel_spread=MAX_REL_SPREAD)["quote_eligible"]


def strategy_scope(panel: pd.DataFrame) -> pd.Series:
    """Near-term, mid-delta window -- a scope choice, not a liquidity criterion.

    A contract outside this DTE/delta band can be genuinely liquid; this only
    flags whether it sits in the range ``liquidity_profile`` summarizes by
    default. Pass ``require_scope=False`` there (or use ``quote_eligibility``
    alone) to see the full quote-eligible surface instead.
    """
    dte = (pd.to_datetime(panel["expiry"]) - pd.to_datetime(panel["snap_date"])).dt.days
    abs_delta = panel["delta"].abs()
    return dte.between(DTE_MIN, DTE_MAX) & abs_delta.between(DELTA_LO, DELTA_HI)


def oi_status(panel: pd.DataFrame) -> pd.Series:
    """``missing`` / ``zero`` / ``positive`` / ``invalid`` -- never filled to zero.

    Same state buckets already used elsewhere in this pipeline (e.g.
    ``src/hedge_design/experiment.py:_menu_contracts_table``): ``missing`` means
    no OI record joined at all; ``invalid`` means a recorded value that isn't a
    finite non-negative integer; ``zero`` and ``positive`` are recorded, verified
    OI.
    """
    oi = panel["open_interest"]
    valid = np.isfinite(oi) & (oi >= 0) & (oi % 1 == 0)
    status = pd.Series(np.where(valid & oi.eq(0), "zero",
                                np.where(valid & oi.gt(0), "positive", "invalid")),
                       index=panel.index)
    status[oi.isna()] = "missing"
    return status


def oi_capped_size(panel: pd.DataFrame, oi_fraction: float) -> np.ndarray:
    """Contracts sizeable at ``oi_fraction`` of recorded OI.

    Missing, zero, or invalid OI sizes to zero -- explicitly unusable, never
    silently unconstrained or silently assumed liquid. Mirrors
    ``_oi_upper_bound``'s convention in ``src/hedge_design/experiment.py``.
    """
    if not np.isfinite(oi_fraction) or not 0 < oi_fraction <= 1:
        raise ValueError("oi_fraction must be in (0, 1]")
    positive = oi_status(panel).eq("positive")
    return np.where(positive, oi_fraction * panel["open_interest"].fillna(0), 0.0)


def liquidity_profile(panel: pd.DataFrame, *, require_scope: bool = True) -> pd.DataFrame:
    """Per-(ticker, snap_date) put/call diagnostics. This is the primary v2 output.

    Deliberately no composite score and no liquidity flag: a median across a
    handful of sparse dates answers a different question than "is a hedge
    feasible on a particular date," and collapsing highly variable per-date OI
    into one number hides exactly the variation that matters (see the module
    docstring for why the v1 score and gate are not carried forward). Read the
    date-specific rows directly instead of aggregating across dates.

    Quote eligibility and strategy scope are composed explicitly (set
    ``require_scope=False`` to report the full quote-eligible surface instead of
    only the DTE/delta scope). No dollar-greek floor. No call/put balance gate --
    put and call notional are reported side by side, so a one-sided book no
    longer zeroes a real one-sided number. ``recorded_oi_premium_notional`` uses
    positive recorded OI only (see the module docstring's epistemic note);
    missing/zero/invalid OI contributes nothing and is counted separately in the
    ``oi_*_count`` columns, never filled.
    """
    work = panel.copy()
    bid, ask = work["bid"].fillna(0), work["ask"].fillna(0)
    work["mid"] = (bid + ask) / 2
    work["rel_spread"] = (ask - bid) / work["mid"].replace(0.0, np.nan)
    work["eligible"] = quote_eligibility(work)
    work["in_scope"] = strategy_scope(work)
    work["oi_status"] = oi_status(work)

    included = work["eligible"] & (work["in_scope"] if require_scope else True)
    passing = work[included].copy()
    group = ["ticker", "snap_date"]

    total = work.groupby(group).size().rename("total_contracts")
    n_pass = passing.groupby(group).size().rename("eligible_contracts")
    oi_counts = (passing.groupby(group)["oi_status"].value_counts().unstack(fill_value=0)
                .reindex(columns=["missing", "zero", "invalid", "positive"], fill_value=0)
                .add_prefix("oi_").add_suffix("_count"))

    has_oi = passing["oi_status"].eq("positive")
    passing["oi_premium_notional"] = np.where(
        has_oi, passing["open_interest"] * CONTRACT_MULTIPLIER * passing["mid"], 0.0)
    notional = passing.groupby(group)["oi_premium_notional"].sum().rename("recorded_oi_premium_notional")
    side = (passing.groupby(group + ["right"])["oi_premium_notional"].sum()
           .unstack("right").reindex(columns=["C", "P"]).fillna(0.0)
           .rename(columns={"C": "call_notional", "P": "put_notional"}))
    spread_med = passing.groupby(group)["rel_spread"].median().rename("median_spread")

    summary = (pd.concat([total, n_pass], axis=1).fillna({"eligible_contracts": 0})
              .join(oi_counts, how="left").join(notional, how="left")
              .join(side, how="left").join(spread_med, how="left").reset_index())
    count_columns = ["oi_missing_count", "oi_zero_count", "oi_invalid_count", "oi_positive_count",
                     "recorded_oi_premium_notional", "call_notional", "put_notional", "eligible_contracts"]
    for column in count_columns:
        summary[column] = summary[column].fillna(0)
    summary["eligibility_rate"] = (summary["eligible_contracts"] / summary["total_contracts"]).round(4)
    # median_spread stays NaN (undefined) for a date with zero eligible
    # contracts -- it is not given a value here, unlike the count/notional
    # columns above where zero is the correct fact, not a filled-in guess.
    return summary


def oi_capped_put_menu(panel: pd.DataFrame, *, oi_fraction: float, right: str = "P",
                       require_scope: bool = True) -> pd.DataFrame:
    """Per-(ticker, snap_date) menu of contracts with positive recorded OI, and
    the premium required to buy ``oi_fraction`` of each one's recorded OI
    *simultaneously* (``full_menu_premium_cost_usd``, priced at the ask).

    Every observed (ticker, snap_date) in ``panel`` gets a row, including dates
    with zero candidates of the requested ``right`` -- an empty menu is a real,
    visible result (``candidate_contracts=0``), not a dropped one; its spread
    and moneyness columns are correctly undefined (NaN), not zero.

    ``total_menu_contracts_continuous`` is ``oi_fraction`` of recorded OI per
    contract, summed -- a modeled, continuous quantity (matching this
    pipeline's existing continuous-position convention elsewhere, e.g.
    ``src/hedge_design/optimize.py``), not a whole-contract trading limit.
    Flooring each contract's individual cap before summing would be needed for
    a whole-lot count; that isn't done here.

    ``full_menu_premium_cost_usd`` is priced at the ask -- an illustrated
    purchase premium, not a guaranteed execution price. This is not an
    optimized hedge, not a chosen hedge size, and not a measure of protection:
    it is the cost of purchasing the entire OI-capped menu across every
    qualifying strike at once. It answers "does a menu with recorded depth
    exist, at what aggregate premium, over what moneyness range" -- nothing
    about whether that premium is well spent, how much loss it would offset,
    or how it compares across tickers. Comparing tickers on this premium alone
    is not a comparison of hedge capacity: that needs a common portfolio,
    horizon, budget, and risk-reduction measure, none of which are computed
    here (see ``src/hedge_design/`` for the actual CVaR accounting).
    """
    work = panel.copy()
    bid, ask = work["bid"].fillna(0), work["ask"].fillna(0)
    work["mid"] = (bid + ask) / 2
    work["rel_spread"] = (ask - bid) / work["mid"].replace(0.0, np.nan)
    eligible = quote_eligibility(work)
    in_scope = strategy_scope(work) if require_scope else pd.Series(True, index=work.index)
    work["oi_status"] = oi_status(work)
    work["menu_contracts"] = oi_capped_size(work, oi_fraction)
    work["candidate"] = eligible & in_scope & work["right"].eq(right)

    rows = []
    for (ticker, date), full_group in work.groupby(["ticker", "snap_date"]):
        group = full_group[full_group["candidate"]]
        priced = group[group["menu_contracts"] > 0]
        moneyness = priced["strike"] / priced["underlying"]
        rows.append({
            "ticker": ticker, "snap_date": date, "right": right,
            "candidate_contracts": len(group),
            "oi_missing": int((group["oi_status"] == "missing").sum()),
            "oi_zero": int((group["oi_status"] == "zero").sum()),
            "oi_invalid": int((group["oi_status"] == "invalid").sum()),
            "oi_positive": int((group["oi_status"] == "positive").sum()),
            "menu_strikes": len(priced),
            "total_menu_contracts_continuous": float(priced["menu_contracts"].sum()),
            "full_menu_premium_cost_usd": float(
                (priced["menu_contracts"] * CONTRACT_MULTIPLIER * priced["ask"]).sum()),
            "median_spread_of_menu": float(priced["rel_spread"].median()) if len(priced) else float("nan"),
            "min_strike_spot": float(moneyness.min()) if len(priced) else float("nan"),
            "max_strike_spot": float(moneyness.max()) if len(priced) else float("nan"),
        })
    columns = ["ticker", "snap_date", "right", "candidate_contracts", "oi_missing", "oi_zero",
              "oi_invalid", "oi_positive", "menu_strikes", "total_menu_contracts_continuous",
              "full_menu_premium_cost_usd", "median_spread_of_menu", "min_strike_spot",
              "max_strike_spot"]
    return pd.DataFrame(rows, columns=columns)


def build_and_write(pull_roots: list[Path], output_root: Path, dataset_id: str,
                    *, screen_version: str = "v1") -> Path:
    if screen_version not in {"v1", "v2"}:
        raise ValueError("screen_version must be 'v1' or 'v2'")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", dataset_id):
        raise ValueError("dataset-id must contain only letters, digits, underscores, and hyphens")
    destination = output_root / dataset_id
    if destination.exists():
        raise FileExistsError(f"Dataset already exists: {destination}; use a new dataset-id")
    panel = assemble_partitions(pull_roots)
    chains = lean_chains(panel)  # identical regardless of screen_version -- the score never gates it

    ticker_level = None
    notes = None
    if screen_version == "v1":
        contract_summary, ticker_level = ticker_summary(panel)
        thresholds = {"max_rel_spread": MAX_REL_SPREAD, "dte_min": DTE_MIN, "dte_max": DTE_MAX,
                     "delta_lo": DELTA_LO, "delta_hi": DELTA_HI,
                     "min_dollar_delta": MIN_DOLLAR_DELTA, "min_dollar_gamma": MIN_DOLLAR_GAMMA,
                     "min_dollar_vega": MIN_DOLLAR_VEGA, "liquidity_score_min": LIQUIDITY_SCORE_MIN}
        liquid_tickers = sorted(ticker_level.loc[ticker_level["liquid"], "ticker"].tolist())
    else:
        contract_summary = liquidity_profile(panel)
        thresholds = {"max_rel_spread": MAX_REL_SPREAD, "dte_min": DTE_MIN, "dte_max": DTE_MAX,
                     "delta_lo": DELTA_LO, "delta_hi": DELTA_HI}
        liquid_tickers = None  # no composite score or liquidity flag in v2 -- see notes and summary.csv
        notes = ("No composite score or liquidity flag is produced for v2 by design -- a "
                "sparse-date median was judged a poor answer to whether a hedge is feasible on "
                "a particular date. See summary.csv for date-specific put/call diagnostics. "
                "No dollar-greek floor, no call/put balance gate. OI missing/zero/invalid kept "
                "distinct, never filled.")

    destination.mkdir(parents=True)
    chains.to_csv(destination / "chains.csv", index=False)
    contract_summary.to_csv(destination / "summary.csv", index=False)
    if ticker_level is not None:
        ticker_level.to_csv(destination / "ticker_summary.csv", index=False)
    manifest = {
        "schema_version": 1, "dataset_id": dataset_id, "screen_version": screen_version,
        "source_pulls": {str(root): sha256_file(root / "manifest.json") for root in pull_roots},
        "thresholds": thresholds,
        "chain_rows": len(chains), "tickers": sorted(chains["ticker"].unique().tolist()),
        "snap_dates": sorted(chains["snap_date"].unique().tolist()),
        "liquid_tickers": liquid_tickers,  # a sorted list for v1; null for v2 (not computed) -- see notes
        "underlying_source": "greeks_eod.underlying_price (one spot per ticker/date)",
    }
    if notes is not None:
        manifest["notes"] = notes
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    return destination
