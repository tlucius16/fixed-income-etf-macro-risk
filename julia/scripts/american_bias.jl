# American-exercise repricing bias for the fixed-income ETF option chains.
#
# File-exchange only: reads data/processed/options_screen/chains.csv and writes
# docs/hedge_capacity/tables/american_bias.csv.  The output is a summary by
# ticker × right × |delta| moneyness bucket.
#
# Usage:
#   julia --project=julia julia/scripts/american_bias.jl
#   julia --project=julia julia/scripts/american_bias.jl --steps 751 --max-rows 1000

using CSV
using DataFrames
using Dates
using Printf
using Statistics
using RateSpace

const REPO = normpath(joinpath(@__DIR__, "..", ".."))
const CHAINS = joinpath(REPO, "data", "processed", "options_screen", "chains.csv")
const DEFAULT_OUT = joinpath(REPO, "docs", "hedge_capacity", "tables", "american_bias.csv")

const MIN_OPTION_PRICE = 0.01
const IV_LO = 1e-4
const IV_HI = 20.0

isvalidnum(x) = !ismissing(x) && isfinite(Float64(x))

function parse_args(args)
    steps = 751
    out = DEFAULT_OUT
    max_rows = 0
    row_out = ""
    progress_every = 5000

    i = 1
    while i <= length(args)
        if args[i] == "--steps"
            steps = parse(Int, args[i + 1])
            i += 2
        elseif args[i] == "--out"
            out = args[i + 1]
            i += 2
        elseif args[i] == "--max-rows"
            max_rows = parse(Int, args[i + 1])
            i += 2
        elseif args[i] == "--row-out"
            row_out = args[i + 1]
            i += 2
        elseif args[i] == "--progress-every"
            progress_every = parse(Int, args[i + 1])
            i += 2
        else
            error("Unknown argument: $(args[i])")
        end
    end
    steps >= 501 || error("--steps must be >= 501 for the paper check")
    return (; steps, out, max_rows, row_out, progress_every)
end

@inline function payoff(spot::Float64, K::Float64, right::Symbol)
    right === :call ? max(spot - K, 0.0) : max(K - spot, 0.0)
end

function crr_price(
    S::Real, K::Real, dte::Integer, r::Real, σ::Real, q::Real;
    right::Symbol = :call,
    american::Bool = true,
    steps::Int = 501,
)
    T = dte / 365.0
    S = Float64(S)
    K = Float64(K)
    r = Float64(r)
    σ = Float64(σ)
    q = Float64(q)
    if T <= 0 || S <= 0 || K <= 0 || σ <= 0 || !all(isfinite, (S, K, r, σ, q))
        return NaN
    end

    n = max(steps, 1)
    dt = T / n
    sqrt_dt = sqrt(dt)
    u = exp(σ * sqrt_dt)
    d = inv(u)
    denom = u - d
    denom <= 0 && return NaN

    growth = exp((r - q) * dt)
    p = (growth - d) / denom
    if p < -1e-10 || p > 1 + 1e-10 || !isfinite(p)
        return NaN
    end
    p = clamp(p, 0.0, 1.0)
    disc = exp(-r * dt)
    ud = u / d

    values = Vector{Float64}(undef, n + 1)
    spot = S * d^n
    @inbounds for j in 0:n
        values[j + 1] = payoff(spot, K, right)
        spot *= ud
    end

    @inbounds for step in (n - 1):-1:0
        spot = S * d^step
        for j in 0:step
            continuation = disc * ((1 - p) * values[j + 1] + p * values[j + 2])
            if american
                values[j + 1] = max(continuation, payoff(spot, K, right))
            else
                values[j + 1] = continuation
            end
            spot *= ud
        end
    end
    return values[1]
end

function american_implied_vol(
    target::Float64, S::Float64, K::Float64, dte::Int, r::Float64, q::Float64,
    right::Symbol, eur_iv::Float64;
    steps::Int,
    iv_tol::Float64 = 1e-5,
    price_tol::Float64 = 1e-6,
    max_iter::Int = 60,
)
    if target <= MIN_OPTION_PRICE || S <= 0 || K <= 0 || dte <= 0 || eur_iv <= 0
        return NaN
    end

    f(σ) = crr_price(S, K, dte, r, σ, q; right, american = true, steps) - target

    lo = IV_LO
    flo = f(lo)
    !isfinite(flo) && return NaN
    # Market price is below the near-zero-vol American lower bound.
    flo > price_tol && return NaN

    hi = clamp(max(eur_iv, 1e-3), lo * 10, IV_HI)
    fhi = f(hi)
    !isfinite(fhi) && return NaN
    while fhi < 0 && hi < IV_HI
        hi = min(IV_HI, max(hi * 1.6, hi + 0.05))
        fhi = f(hi)
        !isfinite(fhi) && return NaN
    end
    fhi < -price_tol && return NaN

    for _ in 1:max_iter
        mid = (lo + hi) / 2
        fmid = f(mid)
        !isfinite(fmid) && return NaN
        if abs(fmid) <= price_tol || (hi - lo) <= iv_tol
            return mid
        elseif fmid > 0
            hi = mid
        else
            lo = mid
        end
    end
    return (lo + hi) / 2
end

function run_convergence_checks(steps::Int)
    cases = [
        (100.0, 100.0, 45, 0.05, 0.20, 0.00, :call),
        (100.0, 100.0, 45, 0.05, 0.20, 0.00, :put),
        (100.0, 90.0, 120, 0.04, 0.30, 0.02, :call),
        (100.0, 110.0, 120, 0.04, 0.30, 0.02, :put),
    ]
    max_euro_gap = 0.0
    for (S, K, dte, r, σ, q, right) in cases
        T = dte / 365.0
        bsm = bs_price(S, K, T, r, σ, q; right)
        eur_tree = crr_price(S, K, dte, r, σ, q; right, american = false, steps)
        gap = abs(eur_tree - bsm)
        max_euro_gap = max(max_euro_gap, gap)
        gap < 1e-3 || error("European CRR/BMS convergence gap $(gap) >= 1e-3 for $(right)")
    end

    call_cases = [
        (100.0, 80.0, 180, 0.05, 0.25, 0.0),
        (100.0, 100.0, 180, 0.05, 0.25, 0.0),
        (100.0, 120.0, 180, 0.05, 0.25, 0.0),
    ]
    max_call_gap = 0.0
    for (S, K, dte, r, σ, q) in call_cases
        eur_tree = crr_price(S, K, dte, r, σ, q; right = :call, american = false, steps)
        amer_tree = crr_price(S, K, dte, r, σ, q; right = :call, american = true, steps)
        gap = abs(amer_tree - eur_tree)
        max_call_gap = max(max_call_gap, gap)
        gap < 1e-8 || error("American call with q=0 differs from European by $(gap)")
    end

    @printf("CRR checks OK: max European/BSM gap %.3g; max no-div call early-ex gap %.3g\n",
            max_euro_gap, max_call_gap)
end

function moneyness_bucket(delta)
    a = abs(Float64(delta))
    if a < 0.35
        return "abs_delta_lt_0.35"
    elseif a <= 0.65
        return "abs_delta_0.35_0.65"
    else
        return "abs_delta_gt_0.65"
    end
end

function finite_values(v)
    vals = Float64[]
    for x in v
        if !ismissing(x) && isfinite(Float64(x))
            push!(vals, Float64(x))
        end
    end
    return vals
end

function positive_values(v)
    vals = Float64[]
    for x in v
        if !ismissing(x) && isfinite(Float64(x)) && Float64(x) > 0
            push!(vals, Float64(x))
        end
    end
    return vals
end

q_or_nan(vals, p) = isempty(vals) ? NaN : quantile(vals, p)

function summarize_rows(rows::DataFrame)
    grouped = groupby(rows, [:ticker, :right, :moneyness_bucket], sort = true)
    out = NamedTuple[]
    for g in grouped
        iv_bias = finite_values(g.iv_bias)
        abs_iv_bias = abs.(iv_bias)
        eep_pct = finite_values(g.eep_pct_mid)
        amer_iv = finite_values(g.american_iv)
        pos_q = positive_values(g.div_yield)
        pos_q_mask = g.div_yield .> 0
        pos_q_iv_bias = finite_values(g.iv_bias[pos_q_mask])
        pos_q_eep_pct = finite_values(g.eep_pct_mid[pos_q_mask])
        push!(out, (
            ticker = String(g.ticker[1]),
            right = String(g.right[1]),
            moneyness_bucket = String(g.moneyness_bucket[1]),
            rows = nrow(g),
            valid_american_iv = length(amer_iv),
            no_solution = nrow(g) - length(amer_iv),
            median_div_yield = q_or_nan(finite_values(g.div_yield), 0.50),
            p75_div_yield = q_or_nan(finite_values(g.div_yield), 0.75),
            max_div_yield = q_or_nan(finite_values(g.div_yield), 1.0),
            share_positive_div_yield = mean(Float64.(g.div_yield .> 0)),
            positive_div_yield_rows = length(pos_q),
            median_positive_div_yield = q_or_nan(pos_q, 0.50),
            median_euro_iv = q_or_nan(finite_values(g.euro_iv), 0.50),
            median_american_iv = q_or_nan(amer_iv, 0.50),
            median_iv_bias = q_or_nan(iv_bias, 0.50),
            p95_iv_bias = q_or_nan(iv_bias, 0.95),
            p95_abs_iv_bias = q_or_nan(abs_iv_bias, 0.95),
            median_iv_bias_vol_bp = 10_000 * q_or_nan(iv_bias, 0.50),
            p95_abs_iv_bias_vol_bp = 10_000 * q_or_nan(abs_iv_bias, 0.95),
            median_eep_pct_mid = q_or_nan(eep_pct, 0.50),
            p95_eep_pct_mid = q_or_nan(eep_pct, 0.95),
            median_positive_q_iv_bias_vol_bp = 10_000 * q_or_nan(pos_q_iv_bias, 0.50),
            median_positive_q_eep_pct_mid = q_or_nan(pos_q_eep_pct, 0.50),
        ))
    end
    return DataFrame(out)
end

function row_bias(r; steps::Int)
    ticker = String(r.ticker)
    right_str = String(r.right)
    right = right_str == "P" ? :put : :call
    S = Float64(r.underlying)
    K = Float64(r.strike)
    dte = Int(r.dte)
    target = Float64(r.option_price)
    rf = Float64(r.rf_annual)
    q = Float64(r.div_yield)
    delta = Float64(r.delta)

    T = dte / 365.0
    eur_iv = implied_vol(target, S, K, dte, rf, q; right)
    euro_price = bs_price(S, K, T, rf, eur_iv, q; right)

    american_price = NaN
    american_iv = NaN
    status = "ok"

    if right === :call && abs(q) < 1e-14
        american_price = euro_price
        american_iv = eur_iv
        status = "no_div_call_identity"
    else
        american_price = crr_price(S, K, dte, rf, eur_iv, q; right, american = true, steps)
        if !isfinite(american_price)
            status = "price_nan"
        else
            eep_raw = american_price - euro_price
            # If the early-exercise premium is economically zero, do not let
            # finite-tree discretization create artificial IV bias.
            if max(eep_raw, 0.0) <= max(1e-8, target * 1e-8)
                american_iv = eur_iv
                status = "zero_premium"
            else
                american_iv = american_implied_vol(
                    target, S, K, dte, rf, q, right, eur_iv; steps,
                )
                if !isfinite(american_iv)
                    status = "no_solution"
                end
            end
        end
    end

    eep = isfinite(american_price) ? max(american_price - euro_price, 0.0) : NaN
    eep_pct = isfinite(eep) && target > 0 ? 100 * eep / target : NaN
    iv_bias = isfinite(american_iv) ? american_iv - eur_iv : NaN

    return (
        ticker = ticker,
        snap_date = Date(string(r.snap_date)),
        right = right_str,
        moneyness_bucket = moneyness_bucket(delta),
        div_yield = q,
        euro_iv = eur_iv,
        american_iv = american_iv,
        iv_bias = iv_bias,
        eep_pct_mid = eep_pct,
        status = status,
    )
end

function main()
    args = parse_args(ARGS)
    mkpath(dirname(args.out))
    run_convergence_checks(args.steps)

    chains = CSV.read(CHAINS, DataFrame)
    if args.max_rows > 0 && args.max_rows < nrow(chains)
        chains = chains[1:args.max_rows, :]
    end
    @printf("American bias run: %d rows, steps=%d\n", nrow(chains), args.steps)

    n = nrow(chains)
    rows = Vector{NamedTuple}(undef, n)
    progress = Threads.Atomic{Int}(0)
    print_lock = ReentrantLock()
    Threads.@threads for i in 1:n
        rows[i] = row_bias(chains[i, :]; steps = args.steps)
        done = Threads.atomic_add!(progress, 1) + 1
        if args.progress_every > 0 && (done % args.progress_every == 0 || done == n)
            lock(print_lock)
            try
                @printf("  processed %d / %d rows\n", done, n)
                flush(stdout)
            finally
                unlock(print_lock)
            end
        end
    end
    row_df = DataFrame(rows)
    summary = summarize_rows(row_df)
    CSV.write(args.out, summary)
    println("Wrote $(args.out)")

    if args.row_out != ""
        mkpath(dirname(args.row_out))
        CSV.write(args.row_out, row_df)
        println("Wrote row diagnostics $(args.row_out)")
    end

    status_counts = combine(groupby(row_df, :status), nrow => :rows)
    println("Status counts:")
    show(status_counts, allrows = true, allcols = true)
    println()
end

if abspath(PROGRAM_FILE) == @__FILE__
    main()
end
