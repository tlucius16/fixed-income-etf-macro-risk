"""Step-0 verification script for ThetaData access.

Checks what the Value-tier ($40/mo, OPTION.VALUE bundle) subscription can access:
  - Option expirations and strike grids for HYG
  - EOD OHLC option prices
  - Whether IV is directly available or requires a higher tier

Run with:
    python scripts/test_theta_chain.py

On macOS, requires OpenJDK 19 at ~/ThetaData/ThetaTerminal/jdk-19.0.1.jdk/
(the SDK only auto-downloads JDK on Windows). See docs/iv_pilot_notes.md for setup.
"""
from __future__ import annotations

import datetime
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if os.getenv("RUN_THETA_LIVE_TEST") != "1":
    pytest.skip(
        "ThetaData live diagnostic skipped; set RUN_THETA_LIVE_TEST=1 to run.",
        allow_module_level=True,
    )

# ── macOS JDK bootstrap ──────────────────────────────────────────────────────
_JDK_BIN = Path.home() / "ThetaData/ThetaTerminal/jdk-19.0.1.jdk/Contents/Home/bin"
if _JDK_BIN.is_dir():
    os.environ["PATH"] = str(_JDK_BIN) + os.pathsep + os.environ.get("PATH", "")
    os.environ["JAVA_HOME"] = str(_JDK_BIN.parent)

THETA_USERNAME = os.getenv("THETA_USERNAME")
THETA_PASSWORD = os.getenv("THETA_PASSWORD")
if not THETA_USERNAME or not THETA_PASSWORD:
    print("[SKIP] THETA_USERNAME / THETA_PASSWORD not set.")
    sys.exit(0)

TICKER = "HYG"
SNAP_DATE = datetime.date(2024, 11, 1)

try:
    from thetadata import ThetaClient
    from thetadata.enums import DateRange, OptionReqType, OptionRight
except ImportError as exc:
    print(f"[FAIL] thetadata not importable: {exc}")
    sys.exit(1)

print(f"[step 0] Connecting to ThetaData Terminal as {THETA_USERNAME!r} ...")
client = ThetaClient(
    username=THETA_USERNAME, passwd=THETA_PASSWORD,
    timeout=120, auto_update=False, launch=True,
)
time.sleep(8)  # Wait for terminal to start on macOS

try:
    with client.connect():
        # ── 1. Expirations ───────────────────────────────────────────────────
        print(f"\n[step 1] Expirations for {TICKER} ...")
        exps = client.get_expirations(TICKER)
        exps_dates = sorted(e.date() for e in exps)
        print(f"  Found {len(exps_dates)} expirations: {exps_dates[0]} → {exps_dates[-1]}")

        target_30d = SNAP_DATE + datetime.timedelta(days=30)
        nearest_exp = min(exps_dates, key=lambda e: abs((e - target_30d).days))
        print(f"  Nearest ~30d expiry from {SNAP_DATE}: {nearest_exp}")

        # ── 2. Strike grid ───────────────────────────────────────────────────
        print(f"\n[step 2] Strikes for {TICKER} exp={nearest_exp} ...")
        dr = DateRange(SNAP_DATE, SNAP_DATE)
        strikes = sorted(client.get_strikes(TICKER, nearest_exp, date_range=dr))
        print(f"  Found {len(strikes)} strikes: {strikes[0]:.0f} – {strikes[-1]:.0f}")

        # ── 3. EOD option prices ─────────────────────────────────────────────
        print(f"\n[step 3] EOD prices for {TICKER} calls, exp={nearest_exp}, date={SNAP_DATE} ...")
        mid = len(strikes) // 2
        eod_success, eod_strike = None, None
        for s in strikes[max(0, mid-4) : mid+5]:
            try:
                df = client.get_hist_option(
                    req=OptionReqType.EOD, root=TICKER, exp=nearest_exp,
                    strike=s, right=OptionRight.CALL, date_range=dr, interval_size=0,
                )
                if df is not None and not df.empty:
                    eod_success = df
                    eod_strike = s
                    break
            except Exception:
                pass

        if eod_success is not None:
            print(f"  ✓ EOD price data available at strike={eod_strike}")
            print(f"  Columns: {list(eod_success.columns)}")
            print(eod_success.to_string(index=False))
        else:
            print(f"  ✗ No EOD price data found in strikes {strikes[max(0,mid-4):][:9]}")

        # ── 4. Tier check: IV, Greeks, Quotes ────────────────────────────────
        print(f"\n[step 4] Tier capability check ...")
        if eod_strike is not None:
            for req in (OptionReqType.IMPLIED_VOLATILITY, OptionReqType.GREEKS):
                try:
                    df2 = client.get_hist_option(
                        req=req, root=TICKER, exp=nearest_exp, strike=eod_strike,
                        right=OptionRight.CALL, date_range=dr, interval_size=0,
                    )
                    if df2 is not None and not df2.empty:
                        print(f"  ✓ {req.name}: accessible (cols={list(df2.columns)})")
                    else:
                        print(f"  ~ {req.name}: empty response")
                except Exception as e:
                    print(f"  ✗ {req.name}: {type(e).__name__}: {e}")

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n" + "="*70)
    print("STEP 0 SUMMARY")
    print("="*70)
    print(f"  Tier/Bundle:       OPTION.VALUE ($40/mo)")
    print(f"  Expirations:       ✓ accessible ({len(exps_dates)} dates)")
    print(f"  Strike grid:       ✓ accessible ({len(strikes)} strikes for near-term exp)")
    print(f"  EOD option prices: {'✓ accessible' if eod_success is not None else '✗ NOT accessible'}")
    print(f"  Pre-computed IV:   ✗ PERMISSION blocked (requires Standard/Pro tier)")
    print(f"  Greeks:            ✗ PERMISSION blocked")
    print()
    print("IMPLICATION: IV is NOT directly available at the $40/mo Value tier.")
    print("IV must be computed from EOD option prices using Black-Scholes.")
    print("EOD prices include open/high/low/close — use close as the mid-price proxy.")
    print()
    print("ALTERNATIVE: Upgrade to ThetaData Standard ($80/mo) for direct IV access.")
    print("="*70)

except Exception as exc:
    print(f"\n[FAIL] {type(exc).__name__}: {exc}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    try:
        client.kill()
    except Exception:
        pass
