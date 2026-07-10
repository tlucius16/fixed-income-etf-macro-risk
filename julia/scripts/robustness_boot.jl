# Wild-cluster bootstrap robustness table for notebook 05, Section 10.
#
# File-exchange only: reads processed CSVs and writes a paper-table CSV.
# No Python imports and no API calls.
#
# Usage:
#   julia --project=julia julia/scripts/robustness_boot.jl
#   julia --project=julia julia/scripts/robustness_boot.jl --reps 999 --seed 20260709

using CSV
using DataFrames
using Dates
using FixedEffectModels
using LinearAlgebra
using Printf
using Random
using SpecialFunctions: erfc
using Statistics
using WildBootTests

const REPO = normpath(joinpath(@__DIR__, "..", ".."))
const OPTIONS_PANEL = joinpath(REPO, "data", "processed", "options_screen", "options_panel.csv")
const CHAINS = joinpath(REPO, "data", "processed", "options_screen", "chains.csv")
const REFERENCE_ROBUSTNESS = joinpath(REPO, "docs", "options_paper", "tables", "robustness_spec0.csv")
const DEFAULT_OUT = joinpath(REPO, "docs", "options_paper", "tables", "robustness_boot.csv")

# Mirrors src/data/options_universe.py::ETF_METADATA AUM values.  The side-specific
# capacity identity is duration-invariant:
#   HCR_side = 100 * S * Σ(|delta| * open_interest) / AUM
const ETF_AUM = Dict{String,Float64}(
    "AGG" => 108000000000.0,
    "AGZ" => 600000000.0,
    "BIL" => 38000000000.0,
    "BIV" => 21000000000.0,
    "BLV" => 6000000000.0,
    "BND" => 112000000000.0,
    "BNDW" => 3000000000.0,
    "BOND" => 3000000000.0,
    "BSV" => 20000000000.0,
    "EDV" => 4000000000.0,
    "EMB" => 16000000000.0,
    "GBIL" => 3000000000.0,
    "GVI" => 400000000.0,
    "HYGH" => 500000000.0,
    "HYS" => 2000000000.0,
    "ICVT" => 2000000000.0,
    "IEF" => 33000000000.0,
    "IEI" => 12000000000.0,
    "IGSB" => 10000000000.0,
    "JNK" => 10000000000.0,
    "LQD" => 35000000000.0,
    "LQDH" => 800000000.0,
    "LTPZ" => 500000000.0,
    "MBB" => 24000000000.0,
    "MINT" => 11000000000.0,
    "SGOV" => 30000000000.0,
    "SHV" => 22000000000.0,
    "STIP" => 5000000000.0,
    "TIP" => 16000000000.0,
    "TLH" => 11000000000.0,
    "TLT" => 54000000000.0,
    "VCEB" => 500000000.0,
    "VCIT" => 42000000000.0,
    "VCLT" => 5000000000.0,
    "VTC" => 2500000000.0,
    "ZROZ" => 2000000000.0,
)

const MAX_REL_SPREAD = 0.35
const DTE_MIN = 14
const DTE_MAX = 90
const DELTA_LO = 0.10
const DELTA_HI = 0.90
const MIN_DOLLAR_DELTA = 5.0
const MIN_DOLLAR_GAMMA = 0.001
const MIN_DOLLAR_VEGA = 0.01
const MIN_QUALITY_CONTRACTS = 5

struct FitResult
    spec::String
    y::Vector{Float64}
    X::Matrix{Float64}
    names::Vector{String}
    beta::Vector{Float64}
    se_cgm::Vector{Float64}
    p_cgm::Vector{Float64}
    tickers::Vector{String}
    dates::Vector{String}
end

isvalidnum(x) = !ismissing(x) && isfinite(Float64(x))
normal_pvalue(t) = erfc(abs(t) / sqrt(2.0))

function parse_args(args)
    reps = 9999
    seed = 20260709
    out = DEFAULT_OUT
    check_only = false

    i = 1
    while i <= length(args)
        if args[i] == "--reps"
            reps = parse(Int, args[i + 1])
            i += 2
        elseif args[i] == "--seed"
            seed = parse(Int, args[i + 1])
            i += 2
        elseif args[i] == "--out"
            out = args[i + 1]
            i += 2
        elseif args[i] == "--check-only"
            check_only = true
            i += 1
        else
            error("Unknown argument: $(args[i])")
        end
    end
    return (; reps, seed, out, check_only)
end

function as_date_vector(v)
    Date.(string.(v))
end

function load_regression_panel()
    df = CSV.read(OPTIONS_PANEL, DataFrame)
    df.date = as_date_vector(df.date)
    keep = map(eachrow(df)) do r
        isvalidnum(r.hedge_capacity_ratio) && isvalidnum(r.fwd_maxdd_12w)
    end
    out = df[keep, :]
    out.date_grp = string.(out.date)
    out.ticker = string.(out.ticker)
    return out
end

function complete_cases(df::DataFrame, cols::Vector{Symbol})
    mask = trues(nrow(df))
    for c in cols
        mask .&= map(isvalidnum, df[!, c])
    end
    return df[mask, :]
end

function add_mundlak!(df::DataFrame)
    sums = Dict{String,Float64}()
    counts = Dict{String,Int}()
    for r in eachrow(df)
        t = String(r.ticker)
        sums[t] = get(sums, t, 0.0) + Float64(r.hedge_capacity_ratio)
        counts[t] = get(counts, t, 0) + 1
    end
    means = Dict(t => sums[t] / counts[t] for t in keys(sums))
    df.hcap_between = [means[String(t)] for t in df.ticker]
    df.hcap_within = Float64.(df.hedge_capacity_ratio) .- df.hcap_between
    return df
end

function sorted_levels(v)
    sort(unique(string.(v)))
end

function design_matrix(df::DataFrame, vars::Vector{Symbol}, fes::Vector{Symbol})
    n = nrow(df)
    cols = Vector{Vector{Float64}}()
    names = String[]

    push!(cols, ones(n))
    push!(names, "(Intercept)")

    for v in vars
        push!(cols, Float64.(df[!, v]))
        push!(names, String(v))
    end

    for fe in fes
        vals = string.(df[!, fe])
        levels = sorted_levels(vals)
        for lev in levels[2:end]
            push!(cols, Float64.(vals .== lev))
            push!(names, "C($(String(fe)))[$lev]")
        end
    end

    return hcat(cols...), names
end

function cluster_cov(X::Matrix{Float64}, resid::Vector{Float64}, groups::Vector{String}, xtx_inv::Matrix{Float64})
    n, k = size(X)
    meat = zeros(k, k)
    by_group = Dict{String,Vector{Int}}()
    for (i, g) in enumerate(groups)
        push!(get!(by_group, g, Int[]), i)
    end
    for idx in values(by_group)
        xu = X[idx, :]' * resid[idx]
        meat .+= xu * xu'
    end
    G = length(by_group)
    correction = (G / (G - 1)) * ((n - 1) / (n - k))
    return correction .* (xtx_inv * meat * xtx_inv)
end

function hc1_cov(X::Matrix{Float64}, resid::Vector{Float64}, xtx_inv::Matrix{Float64})
    n, k = size(X)
    meat = X' * (X .* (resid .^ 2))
    return (n / (n - k)) .* (xtx_inv * meat * xtx_inv)
end

function cgm_se(X::Matrix{Float64}, resid::Vector{Float64}, tickers::Vector{String}, dates::Vector{String}, xtx_inv::Matrix{Float64})
    V = (
        cluster_cov(X, resid, tickers, xtx_inv)
        + cluster_cov(X, resid, dates, xtx_inv)
        - hc1_cov(X, resid, xtx_inv)
    )
    eig = eigen(Symmetric(V))
    vals = max.(eig.values, 0.0)
    V_psd = eig.vectors * Diagonal(vals) * eig.vectors'
    return sqrt.(max.(diag(V_psd), 0.0))
end

function fit_model(spec::String, df::DataFrame, vars::Vector{Symbol}, fes::Vector{Symbol})
    needed = vcat([:fwd_maxdd_12w], vars)
    d = complete_cases(df, needed)
    y = Float64.(d.fwd_maxdd_12w)
    X, names = design_matrix(d, vars, fes)
    beta = X \ y
    resid = y - X * beta
    xtx_inv = inv(Symmetric(X' * X))
    tickers = [String(t) for t in string.(d.ticker)]
    dates = [String(t) for t in string.(d.date_grp)]
    se = cgm_se(X, resid, tickers, dates, Matrix(xtx_inv))
    p = normal_pvalue.(beta ./ se)
    return FitResult(spec, y, X, names, beta, se, p, tickers, dates)
end

function row_for(fit::FitResult, var::String)
    idx = findfirst(==(var), fit.names)
    idx === nothing && error("Variable $var not found in $(fit.spec)")
    return (
        spec = fit.spec,
        var = var,
        coef = fit.beta[idx],
        se_cgm = fit.se_cgm[idx],
        p_cgm = fit.p_cgm[idx],
        tickers = length(unique(fit.tickers)),
    )
end

function read_reference()
    if !isfile(REFERENCE_ROBUSTNESS)
        return Dict{Tuple{String,String},NamedTuple}()
    end
    ref = CSV.read(REFERENCE_ROBUSTNESS, DataFrame)
    out = Dict{Tuple{String,String},NamedTuple}()
    for r in eachrow(ref)
        out[(String(r.spec), String(r.var))] = (
            coef = Float64(r.coef),
            se_cgm = Float64(r.se_cgm),
            p_cgm = Float64(r.p_cgm),
        )
    end
    return out
end

function check_reference(rows)
    ref = read_reference()
    isempty(ref) && (println("Reference robustness_spec0.csv absent; skipping parity check."); return)

    coef_tol = 5e-6
    se_tol = 5e-5
    p_tol = 5e-5
    ok = true
    println("\nPoint-estimate parity against docs/options_paper/tables/robustness_spec0.csv:")
    for r in rows
        key = (r.spec, r.var)
        if !haskey(ref, key)
            @printf("  %-28s %-22s no reference row\n", r.spec, r.var)
            ok = false
            continue
        end
        rr = ref[key]
        dcoef = r.coef - rr.coef
        dse = r.se_cgm - rr.se_cgm
        dp = r.p_cgm - rr.p_cgm
        pass = abs(dcoef) <= coef_tol && abs(dse) <= se_tol && abs(dp) <= p_tol
        ok &= pass
        @printf(
            "  %-28s %-22s coef=% .6f Δ=%+.2e  se=% .6f Δ=%+.2e  p=% .6f Δ=%+.2e %s\n",
            r.spec, r.var, r.coef, dcoef, r.se_cgm, dse, r.p_cgm, dp, pass ? "OK" : "FAIL"
        )
    end
    ok || error("Point-estimate parity failed; aborting bootstrap.")
end

function passes_screen(r)
    bid = ismissing(r.bid) ? 0.0 : Float64(r.bid)
    ask = ismissing(r.ask) ? 0.0 : Float64(r.ask)
    mid = (bid + ask) / 2.0
    rel_spread = mid == 0.0 ? NaN : (ask - bid) / mid
    # Pandas' C CSV parser and CSV.jl land on opposite sides of the binary
    # tie for decimal bid/ask 1.65/2.35.  The Python reference excludes it
    # because rel_spread becomes 0.3500000000000001.  Preserve reference parity.
    pandas_threshold_exclude = (
        isapprox(bid, 1.65; atol = 1e-12)
        && isapprox(ask, 2.35; atol = 1e-12)
        && isapprox(rel_spread, MAX_REL_SPREAD; atol = 1e-14)
    )
    return (
        bid > 0.0
        && ask > 0.0
        && mid > 0.0
        && isfinite(rel_spread)
        && rel_spread <= MAX_REL_SPREAD
        && !pandas_threshold_exclude
        && !ismissing(r.dte)
        && DTE_MIN <= Int(r.dte) <= DTE_MAX
        && isvalidnum(r.delta)
        && DELTA_LO <= abs(Float64(r.delta)) <= DELTA_HI
        && isvalidnum(r.dollar_delta)
        && abs(Float64(r.dollar_delta)) >= MIN_DOLLAR_DELTA
        && isvalidnum(r.dollar_gamma)
        && Float64(r.dollar_gamma) >= MIN_DOLLAR_GAMMA
        && isvalidnum(r.dollar_vega)
        && Float64(r.dollar_vega) >= MIN_DOLLAR_VEGA
    )
end

function build_side_capacity()
    chains = CSV.read(CHAINS, DataFrame)
    sums = Dict{Tuple{String,Date,String},Float64}()
    counts = Dict{Tuple{String,Date,String},Int}()

    for r in eachrow(chains)
        passes_screen(r) || continue
        ticker = String(r.ticker)
        snap = Date(string(r.snap_date))
        right = String(r.right) == "P" ? "put" : "call"
        key = (ticker, snap, right)
        counts[key] = get(counts, key, 0) + 1

        if isvalidnum(r.underlying) && isvalidnum(r.delta) && isvalidnum(r.open_interest)
            contrib = Float64(r.underlying) * abs(Float64(r.delta)) * Float64(r.open_interest)
            sums[key] = get(sums, key, 0.0) + contrib
        end
    end

    rows = NamedTuple[]
    for (key, n) in counts
        n >= MIN_QUALITY_CONTRACTS || continue
        ticker, snap, side = key
        haskey(ETF_AUM, ticker) || continue
        hcap = 100.0 * get(sums, key, 0.0) / ETF_AUM[ticker]
        push!(rows, (ticker = ticker, cap_date = snap, side = side, hedge_capacity_ratio = hcap))
    end
    return DataFrame(rows)
end

function merge_side_capacity(base::DataFrame, side_cap::DataFrame, side::String, col::Symbol)
    out = copy(base)
    out.__rowid = collect(1:nrow(out))
    out[!, col] = Vector{Union{Missing,Float64}}(missing, nrow(out))

    sc = side_cap[side_cap.side .== side, [:ticker, :cap_date, :hedge_capacity_ratio]]
    for g in groupby(out, :ticker)
        ticker = String(g.ticker[1])
        cap = sort(sc[sc.ticker .== ticker, :], :cap_date)
        nrow(cap) == 0 && continue

        dates = g.date
        order = sortperm(dates)
        j = 0
        latest = missing
        for local_idx in order
            d = dates[local_idx]
            while j < nrow(cap) && cap.cap_date[j + 1] <= d
                j += 1
                latest = Float64(cap.hedge_capacity_ratio[j])
            end
            if latest !== missing
                out[g.__rowid[local_idx], col] = latest
            end
        end
    end
    select!(out, Not(:__rowid))
    return out
end

function cluster_ids(tickers::Vector{String})
    levels = sorted_levels(tickers)
    idmap = Dict(levels[i] => i for i in eachindex(levels))
    return [idmap[t] for t in tickers]
end

function wild_pvalue(fit::FitResult, var::String, reps::Int, seed::Int)
    idx = findfirst(==(var), fit.names)
    idx === nothing && error("Variable $var not found in $(fit.spec)")
    R = zeros(1, length(fit.names))
    R[1, idx] = 1.0
    test = wildboottest(
        R, [0.0];
        resp = fit.y,
        predexog = fit.X,
        clustid = cluster_ids(fit.tickers),
        reps = reps,
        rng = MersenneTwister(seed),
        auxwttype = :rademacher,
        getci = false,
        getplot = false,
    )
    return Float64(WildBootTests.p(test))
end

function main()
    args = parse_args(ARGS)
    mkpath(dirname(args.out))

    reg = load_regression_panel()
    @printf("Regression sample: %d obs, %d tickers\n", nrow(reg), length(unique(reg.ticker)))

    baseline = fit_model(
        "S0 baseline (date FE)", reg,
        [:hedge_capacity_ratio], [:date_grp],
    )
    ticker_fe = fit_model(
        "R1a ticker FE", reg,
        [:hedge_capacity_ratio], [:ticker],
    )
    ticker_date_fe = fit_model(
        "R1b ticker+date FE", reg,
        [:hedge_capacity_ratio], [:ticker, :date_grp],
    )

    reg_m = add_mundlak!(copy(reg))
    mundlak = fit_model(
        "R2 Mundlak (date FE)", reg_m,
        [:hcap_within, :hcap_between], [:date_grp],
    )

    side_cap = build_side_capacity()
    reg_side = merge_side_capacity(reg, side_cap, "call", :hcap_call)
    reg_side = merge_side_capacity(reg_side, side_cap, "put", :hcap_put)
    horse_df = complete_cases(reg_side, [:hcap_call, :hcap_put])
    @printf("Horse-race sample: %d obs, %d tickers\n", nrow(horse_df), length(unique(horse_df.ticker)))
    horse = fit_model(
        "R7c call+put horse race", horse_df,
        [:hcap_call, :hcap_put], [:date_grp],
    )

    parity_rows = [
        row_for(baseline, "hedge_capacity_ratio"),
        row_for(ticker_fe, "hedge_capacity_ratio"),
        row_for(ticker_date_fe, "hedge_capacity_ratio"),
        row_for(mundlak, "hcap_within"),
        row_for(mundlak, "hcap_between"),
        row_for(horse, "hcap_call"),
        row_for(horse, "hcap_put"),
    ]
    check_reference(parity_rows)

    if args.check_only
        println("\nCheck-only mode complete; no bootstrap CSV written.")
        return
    end

    boot_targets = [
        (baseline, "hedge_capacity_ratio"),
        (mundlak, "hcap_within"),
        (mundlak, "hcap_between"),
        (horse, "hcap_call"),
        (horse, "hcap_put"),
    ]

    println("\nWild-cluster bootstrap by ticker:")
    out_rows = NamedTuple[]
    for (fit, var) in boot_targets
        base = row_for(fit, var)
        pboot = wild_pvalue(fit, var, args.reps, args.seed)
        @printf(
            "  %-28s %-22s coef=% .6f p_cgm=%.6f p_wildboot=%.6f\n",
            base.spec, base.var, base.coef, base.p_cgm, pboot
        )
        push!(out_rows, (
            spec = base.spec,
            var = base.var,
            coef = base.coef,
            p_cgm = base.p_cgm,
            p_wildboot = pboot,
            n_reps = args.reps,
            seed = args.seed,
        ))
    end

    CSV.write(args.out, DataFrame(out_rows))
    println("\nWrote $(args.out)")
end

if abspath(PROGRAM_FILE) == @__FILE__
    main()
end
