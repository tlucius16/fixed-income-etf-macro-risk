"""
    RateSpace

Quant layer for the unified paper's hedge-capacity extension, mirroring the Python
reference implementation in `src/data/options.py` (BSM pricing, IV inversion)
and `src/features/rate_space.py` (rate-space translation) — with two upgrades
the language provides:

  * Greeks come from automatic differentiation of `bs_price`, not
    hand-transcribed closed forms.
  * Rate-space quantities carry `Unitful` units (`USD`, `bp`), so the
    D_i cancellation identity and every dollars-per-basis-point conversion
    are enforced by the type system instead of documented in comments.

Conventions match Python exactly: T = dte/365, vega per unit sigma, theta per
calendar day, dollar_gamma = 0.5*Gamma*S^2*0.01^2, dollar_vega = vega*0.01.
"""
module RateSpace

using ForwardDiff
using Roots
using SpecialFunctions: erfc
using Unitful
using Unitful: @dimension, @refunit, @unit

export bs_price, greeks, implied_vol, rate_dv01, rate_conv, fund_dv01
export USD, bp

# ── Units: currency dimension + basis point ─────────────────────────────────
@dimension 𝐂 "𝐂" Currency true
@refunit USD "USD" USDollar 𝐂 false
# 1 bp = 0.01 percent = 1e-4 (dimensionless): the 1e-4 that Python carries as
# a bare constant lives in the unit itself.
@unit bp "bp" BasisPoint 0.01Unitful.percent false

const _MIN_OPTION_PRICE = 0.01        # matches Python _MIN_OPTION_PRICE
const _IV_LO, _IV_HI    = 1e-4, 20.0  # matches Python _IV_SEARCH_BOUNDS
const _MULTIPLIER       = 100.0       # option contract multiplier

Φ(x) = erfc(-x / sqrt(oftype(float(x), 2))) / 2

# ── Pricing (generic over Real so ForwardDiff duals flow through) ───────────
function bs_price(S::Real, K::Real, T::Real, r::Real, σ::Real, q::Real;
                  right::Symbol = :call)
    if T <= 0
        return right === :call ? max(S - K, zero(S - K)) : max(K - S, zero(K - S))
    end
    sqrtT = sqrt(T)
    d1 = (log(S / K) + (r - q + σ^2 / 2) * T) / (σ * sqrtT)
    d2 = d1 - σ * sqrtT
    if right === :call
        S * exp(-q * T) * Φ(d1) - K * exp(-r * T) * Φ(d2)
    else
        K * exp(-r * T) * Φ(-d2) - S * exp(-q * T) * Φ(-d1)
    end
end

# ── Greeks via automatic differentiation ────────────────────────────────────
"""
    greeks(S, K, dte, r, σ, q; right=:call) -> NamedTuple

AD-derived Greeks with the Python `compute_greeks` conventions:
delta = ∂P/∂S, gamma = ∂²P/∂S², vega = ∂P/∂σ (per unit σ),
theta_daily = −(∂P/∂T)/365, plus the dollar transforms.
Invalid inputs (T ≤ 0, σ ≤ 0, S ≤ 0, K ≤ 0) return all-NaN, as in Python.
"""
function greeks(S::Real, K::Real, dte::Integer, r::Real, σ::Real, q::Real;
                right::Symbol = :call)
    T = dte / 365.0
    if T <= 0 || σ <= 0 || S <= 0 || K <= 0
        nanval = oftype(float(S), NaN)
        return (delta = nanval, gamma = nanval, vega = nanval,
                theta_daily = nanval, dollar_delta = nanval,
                dollar_gamma = nanval, dollar_vega = nanval)
    end
    price_S(s) = bs_price(s, K, T, r, σ, q; right)
    delta = ForwardDiff.derivative(price_S, float(S))
    gamma = ForwardDiff.derivative(s -> ForwardDiff.derivative(price_S, s), float(S))
    vega  = ForwardDiff.derivative(σ_ -> bs_price(S, K, T, r, σ_, q; right), float(σ))
    theta_daily = -ForwardDiff.derivative(T_ -> bs_price(S, K, T_, r, σ, q; right), T) / 365.0
    (delta = delta,
     gamma = gamma,
     vega  = vega,
     theta_daily = theta_daily,
     dollar_delta = delta * S,
     dollar_gamma = 0.5 * gamma * S^2 * 0.01^2,
     dollar_vega  = vega * 0.01)
end

# ── IV inversion (Brent, same guards/bounds/tolerances as Python) ───────────
function implied_vol(option_price::Real, S::Real, K::Real, dte::Integer,
                     r::Real, q::Real = 0.0; right::Symbol = :call)
    T = dte / 365.0
    (T <= 0 || option_price <= _MIN_OPTION_PRICE || S <= 0 || K <= 0) && return NaN
    intrinsic = right === :put ?
        max(K * exp(-r * T) - S * exp(-q * T), 0.0) :
        max(S * exp(-q * T) - K * exp(-r * T), 0.0)
    option_price <= intrinsic + 1e-6 && return NaN
    f(σ) = bs_price(S, K, T, r, σ, q; right) - option_price
    try
        # x-based tolerances tighter than scipy's brentq(xtol=1e-6): the Julia
        # root is then effectively exact and any parity gap is Python's own
        # solver tolerance, not ours.
        return find_zero(f, (_IV_LO, _IV_HI), Roots.Brent(); xatol = 1e-10, xrtol = 4e-12)
    catch
        return NaN
    end
end

# ── Rate-space translation (unit-typed) ─────────────────────────────────────
"""
    rate_dv01(D_i, S, delta) -> Quantity{USD/bp}

Per-contract dollar P&L per 1bp yield move. The bp unit carries the 1e-4,
so `rate_dv01(...) * 1bp` is plain USD — and in
`rate_dv01 / fund_dv01` the bp (and D_i) cancel, leaving a dimensionless
capacity ratio: the cancellation identity, enforced by types.
"""
rate_dv01(D_i::Real, S::Real, delta::Real) =
    D_i * S * abs(delta) * _MULTIPLIER * USD / bp / 10_000

"""
    fund_dv01(D_i, aum) -> Quantity{USD/bp}
"""
fund_dv01(D_i::Real, aum::Real) = D_i * aum * USD / bp / 10_000

"""
    rate_conv(D_i, S, delta, gamma) -> Quantity{USD/bp²}

Signed second-order dollars per (1bp)²: 0.5·D_i²·S·(Δ + S·Γ)·multiplier.
"""
rate_conv(D_i::Real, S::Real, delta::Real, gamma::Real) =
    0.5 * D_i^2 * S * (delta + S * gamma) * _MULTIPLIER * USD / bp^2 / 10_000^2

const localunits = Unitful.basefactors
function __init__()
    merge!(Unitful.basefactors, localunits)
    Unitful.register(RateSpace)
end

end # module
