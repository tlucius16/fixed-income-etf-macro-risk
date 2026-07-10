# Parity check: RateSpace.jl vs the Python reference implementation.
#
# Reads the cached chains.csv (whose iv/greeks columns were produced by
# src/data/options.py) and recomputes, for every contract row:
#   * implied vol from option_price      (vs the cached `iv`)
#   * all Greeks at the cached Python IV (vs the cached greek columns)
#
# Usage:
#   julia --project=julia julia/scripts/parity_check.jl [--sample N]
#
# Exits 0 when all differences are within tolerance, 1 otherwise.

using CSV, DataFrames, Statistics, Random
using RateSpace

const REPO = normpath(joinpath(@__DIR__, "..", ".."))
const CHAINS = joinpath(REPO, "data", "processed", "options_screen", "chains.csv")

const IV_TOL    = 5e-6    # both sides Brent at xtol 1e-6
const GREEK_TOL = 1e-8    # AD vs closed form: near machine precision

function main()
    sample = 0
    i = findfirst(==("--sample"), ARGS)
    i !== nothing && (sample = parse(Int, ARGS[i + 1]))

    df = CSV.read(CHAINS, DataFrame)
    if sample > 0 && sample < nrow(df)
        df = df[shuffle(MersenneTwister(42), 1:nrow(df))[1:sample], :]
    end
    println("Parity check on $(nrow(df)) contract rows")

    iv_diffs      = Float64[]
    iv_nan_agree  = 0
    iv_nan_clash  = 0
    greek_diffs   = Dict(c => Float64[] for c in
        ("delta", "gamma", "vega", "theta_daily",
         "dollar_delta", "dollar_gamma", "dollar_vega"))

    for row in eachrow(df)
        right = row.right == "P" ? :put : :call
        S, K, dte = row.underlying, row.strike, row.dte
        r, q = row.rf_annual, row.div_yield

        # IV round-trip from the same mid the Python pipeline inverted
        if !ismissing(row.option_price) && !ismissing(row.iv)
            iv_jl = implied_vol(row.option_price, S, K, dte, r, q; right)
            py_nan = ismissing(row.iv) || isnan(row.iv)
            if isnan(iv_jl) && py_nan
                iv_nan_agree += 1
            elseif isnan(iv_jl) != py_nan
                iv_nan_clash += 1
            else
                push!(iv_diffs, abs(iv_jl - row.iv))
            end
        end

        # Greeks at the cached Python IV
        if !ismissing(row.iv) && !isnan(row.iv) && row.iv > 0
            g = greeks(S, K, dte, r, row.iv, q; right)
            for (col, val) in pairs(g)
                py = row[col]
                (ismissing(py) || isnan(py)) && continue
                push!(greek_diffs[String(col)], abs(val - py))
            end
        end
    end

    ok = true
    if !isempty(iv_diffs)
        mx = maximum(iv_diffs)
        println("IV        n=$(length(iv_diffs))  max|Δ|=$(mx)  " *
                "p99=$(quantile(iv_diffs, 0.99))  nan-agree=$iv_nan_agree  nan-clash=$iv_nan_clash")
        mx > IV_TOL && (ok = false)
        iv_nan_clash > 0 && (ok = false)
    end
    for (col, d) in sort(collect(greek_diffs); by = first)
        isempty(d) && continue
        mx = maximum(d)
        println(rpad(col, 13) * "n=$(length(d))  max|Δ|=$(mx)")
        mx > GREEK_TOL && (ok = false)
    end

    println(ok ? "\nPARITY OK" : "\nPARITY FAILED")
    exit(ok ? 0 : 1)
end

main()
