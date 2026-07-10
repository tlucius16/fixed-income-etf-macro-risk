"""Universe and static metadata for the 36-ticker fixed-income ETF options paper.

UNIVERSE         : ticker → asset-class category
DURATION_BUCKET  : category → duration bucket label
BUCKET_ORDER     : display order for bucket-level tables/charts
ETF_METADATA     : per-ticker AUM, effective duration/convexity, expense ratio
"""
from __future__ import annotations

# ── Universe ──────────────────────────────────────────────────────────────────

# ticker → asset class category
UNIVERSE: dict[str, str] = {
    # T-bills / ultra-short
    "BIL":  "tbill",
    "GBIL": "tbill",
    "MINT": "tbill",
    "SGOV": "tbill",
    "SHV":  "tbill",
    # Short-term government / agency
    "AGZ":  "gov_short",
    "BSV":  "gov_short",
    "GVI":  "gov_short",
    "IEI":  "gov_short",
    # Intermediate government
    "BIV":  "gov_int",
    "IEF":  "gov_int",
    # Long government
    "BLV":  "gov_long",
    "EDV":  "gov_long",
    "TLH":  "gov_long",
    "TLT":  "gov_long",
    "ZROZ": "gov_long",
    # TIPS / inflation-linked
    "STIP": "tips",
    "TIP":  "tips",
    "LTPZ": "tips_long",
    # Broad aggregate
    "AGG":  "agg",
    "BND":  "agg",
    "BNDW": "agg",
    "BOND": "agg",
    # Investment-grade credit
    "IGSB": "ig_short",
    "LQDH": "ig_short",
    "VCEB": "ig_int",
    "LQD":  "ig_int",
    "VCIT": "ig_int",
    "VTC":  "ig_int",
    "VCLT": "ig_long",
    # High yield
    "HYS":  "hy",
    "HYGH": "hy",
    "JNK":  "hy",
    # Mortgage-backed
    "MBB":  "mbs",
    # Emerging markets
    "EMB":  "em",
    # Other
    "ICVT": "other",
}

# category → duration bucket used in cross-sectional analysis
DURATION_BUCKET: dict[str, str] = {
    "tbill":     "short",
    "gov_short": "short",
    "gov_int":   "intermediate",
    "gov_long":  "long",
    "tips":      "intermediate",
    "tips_long": "long",
    "agg":       "intermediate",
    "ig_short":  "short",
    "ig_int":    "intermediate",
    "ig_long":   "long",
    "hy":        "credit",
    "mbs":       "intermediate",
    "em":        "intermediate",
    "other":     "other",
}

# Ordered for display (short → long → credit)
BUCKET_ORDER = ["short", "intermediate", "long", "credit", "other"]

# Liquidity gate: median composite liquidity score across snap dates,
#   liq_score = √(quality OI premium notional) × (1 − median spread) × book balance.
# Monotone increasing in √notional by construction; units are √$ damped by two
# factors in (0, 1]. Calibrated on the 2020-2025 quarterly chains (provisional —
# see the per-ticker distribution before finalizing).
LIQUIDITY_SCORE_MIN = 100.0


def ticker_bucket(ticker: str) -> str:
    cat = UNIVERSE.get(ticker, "other")
    return DURATION_BUCKET.get(cat, "other")


# ── Static ETF metadata ───────────────────────────────────────────────────────
# Values from fund fact sheets (iShares, Vanguard, PIMCO, SPDR) as of ~Q1 2025.
# Refresh from fact sheets before final submission.
#
# Fields:
#   aum           : assets under management in USD (approximate)
#   eff_duration  : published effective duration in years
#   eff_convexity : published effective convexity (years²/100); None if not published
#   expense_ratio : annual expense ratio as decimal (0.0015 = 15 bps)

ETF_METADATA: dict[str, dict] = {
    # ── T-bills / ultra-short ──────────────────────────────────────────────
    "BIL": {
        "aum": 38_000_000_000,
        "eff_duration":  0.10,
        "eff_convexity": None,
        "expense_ratio": 0.0014,
    },
    "GBIL": {
        "aum": 3_000_000_000,
        "eff_duration":  0.25,
        "eff_convexity": None,
        "expense_ratio": 0.0012,
    },
    "MINT": {
        "aum": 11_000_000_000,
        "eff_duration":  0.35,
        "eff_convexity": None,
        "expense_ratio": 0.0035,
    },
    "SGOV": {
        "aum": 30_000_000_000,
        "eff_duration":  0.10,
        "eff_convexity": None,
        "expense_ratio": 0.0007,
    },
    "SHV": {
        "aum": 22_000_000_000,
        "eff_duration":  0.30,
        "eff_convexity": None,
        "expense_ratio": 0.0015,
    },
    # ── Short-term government / agency ────────────────────────────────────
    "AGZ": {
        "aum": 600_000_000,
        "eff_duration":  3.50,
        "eff_convexity": None,
        "expense_ratio": 0.0020,
    },
    "BSV": {
        "aum": 20_000_000_000,
        "eff_duration":  2.80,
        "eff_convexity": None,
        "expense_ratio": 0.0004,
    },
    "GVI": {
        "aum": 400_000_000,
        "eff_duration":  4.50,
        "eff_convexity": None,
        "expense_ratio": 0.0020,
    },
    "IEI": {
        "aum": 12_000_000_000,
        "eff_duration":  4.50,
        "eff_convexity": 0.11,
        "expense_ratio": 0.0015,
    },
    # ── Intermediate government ───────────────────────────────────────────
    "BIV": {
        "aum": 21_000_000_000,
        "eff_duration":  6.40,
        "eff_convexity": None,
        "expense_ratio": 0.0004,
    },
    "IEF": {
        "aum": 33_000_000_000,
        "eff_duration":  7.50,
        "eff_convexity": 0.72,
        "expense_ratio": 0.0015,
    },
    # ── Long government ───────────────────────────────────────────────────
    "BLV": {
        "aum": 6_000_000_000,
        "eff_duration":  14.50,
        "eff_convexity": 2.50,
        "expense_ratio": 0.0004,
    },
    "EDV": {
        "aum": 4_000_000_000,
        "eff_duration":  24.70,
        "eff_convexity": 8.00,
        "expense_ratio": 0.0006,
    },
    "TLH": {
        "aum": 11_000_000_000,
        "eff_duration":  12.10,
        "eff_convexity": 1.80,
        "expense_ratio": 0.0015,
    },
    "TLT": {
        "aum": 54_000_000_000,
        "eff_duration":  16.50,
        "eff_convexity": 3.70,
        "expense_ratio": 0.0015,
    },
    "ZROZ": {
        "aum": 2_000_000_000,
        "eff_duration":  27.20,
        "eff_convexity": 9.50,
        "expense_ratio": 0.0015,
    },
    # ── TIPS / inflation-linked ───────────────────────────────────────────
    "STIP": {
        "aum": 5_000_000_000,
        "eff_duration":  2.70,
        "eff_convexity": None,
        "expense_ratio": 0.0005,
    },
    "TIP": {
        "aum": 16_000_000_000,
        "eff_duration":  7.20,
        "eff_convexity": 0.60,
        "expense_ratio": 0.0019,
    },
    "LTPZ": {
        "aum": 500_000_000,
        "eff_duration":  20.50,
        "eff_convexity": 5.50,
        "expense_ratio": 0.0020,
    },
    # ── Broad aggregate ───────────────────────────────────────────────────
    "AGG": {
        "aum": 108_000_000_000,
        "eff_duration":  6.30,
        "eff_convexity": 0.57,
        "expense_ratio": 0.0003,
    },
    "BND": {
        "aum": 112_000_000_000,
        "eff_duration":  6.50,
        "eff_convexity": 0.58,
        "expense_ratio": 0.0003,
    },
    "BNDW": {
        "aum": 3_000_000_000,
        "eff_duration":  6.30,
        "eff_convexity": None,
        "expense_ratio": 0.0005,
    },
    "BOND": {
        "aum": 3_000_000_000,
        "eff_duration":  6.00,
        "eff_convexity": None,
        "expense_ratio": 0.0055,
    },
    # ── Investment-grade credit ───────────────────────────────────────────
    "IGSB": {
        "aum": 10_000_000_000,
        "eff_duration":  2.60,
        "eff_convexity": None,
        "expense_ratio": 0.0006,
    },
    "LQDH": {
        "aum": 800_000_000,
        "eff_duration":  0.40,
        "eff_convexity": None,
        "expense_ratio": 0.0025,
    },
    "VCEB": {
        "aum": 500_000_000,
        "eff_duration":  8.00,
        "eff_convexity": None,
        "expense_ratio": 0.0012,
    },
    "LQD": {
        "aum": 35_000_000_000,
        "eff_duration":  8.40,
        "eff_convexity": 1.20,
        "expense_ratio": 0.0014,
    },
    "VCIT": {
        "aum": 42_000_000_000,
        "eff_duration":  6.70,
        "eff_convexity": None,
        "expense_ratio": 0.0004,
    },
    "VTC": {
        "aum": 2_500_000_000,
        "eff_duration":  7.50,
        "eff_convexity": None,
        "expense_ratio": 0.0004,
    },
    "VCLT": {
        "aum": 5_000_000_000,
        "eff_duration":  13.70,
        "eff_convexity": 2.10,
        "expense_ratio": 0.0004,
    },
    # ── High yield ────────────────────────────────────────────────────────
    "HYS": {
        "aum": 2_000_000_000,
        "eff_duration":  2.20,
        "eff_convexity": None,
        "expense_ratio": 0.0055,
    },
    "HYGH": {
        "aum": 500_000_000,
        "eff_duration":  0.40,
        "eff_convexity": None,
        "expense_ratio": 0.0055,
    },
    "JNK": {
        "aum": 10_000_000_000,
        "eff_duration":  3.50,
        "eff_convexity": None,
        "expense_ratio": 0.0040,
    },
    # ── Mortgage-backed ───────────────────────────────────────────────────
    "MBB": {
        "aum": 24_000_000_000,
        "eff_duration":  6.20,
        "eff_convexity": None,
        "expense_ratio": 0.0004,
    },
    # ── Emerging markets ──────────────────────────────────────────────────
    "EMB": {
        "aum": 16_000_000_000,
        "eff_duration":  7.30,
        "eff_convexity": None,
        "expense_ratio": 0.0039,
    },
    # ── Other ─────────────────────────────────────────────────────────────
    "ICVT": {
        "aum": 2_000_000_000,
        "eff_duration":  2.50,
        "eff_convexity": None,
        "expense_ratio": 0.0020,
    },
}


def get_metadata(ticker: str) -> dict:
    """Return metadata for *ticker*; raises KeyError if not in universe."""
    try:
        return ETF_METADATA[ticker]
    except KeyError:
        raise KeyError(
            f"{ticker!r} not found in ETF_METADATA. "
            f"Available tickers: {sorted(ETF_METADATA)}"
        )
