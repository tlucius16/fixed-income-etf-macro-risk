# Wild-cluster bootstrap for the fragility paper's H4 amplification specs.
#
# Reproduces scripts/08_fragility_h4.py point estimates (parity-gated against
# data/exports/tables/fragility_h4_reference.csv), then reports wild-cluster
# bootstrap p-values (Rademacher) clustered by Date — the binding dimension,
# since stress varies only at the week level — and by Symbol for comparison.
#
# Usage:
#   julia --project=julia julia/scripts/fragility_boot.jl [--reps 9999] [--check-only]

using CSV, DataFrames, Dates, LinearAlgebra, Printf, Random, Statistics
using SpecialFunctions: erfc
using WildBootTests

const REPO = normpath(joinpath(@__DIR__, "..", ".."))
const CORE = joinpath(REPO, "data", "processed", "offline", "core_panel.csv")
const REF  = joinpath(REPO, "data", "exports", "tables", "fragility_h4_reference.csv")
const OUT  = joinpath(REPO, "data", "exports", "tables", "fragility_boot.csv")

const FRAG   = ["vol_12w", "downside_vol_12w", "maxdd_12w"]
const STRUCT = ["log_assets", "ER_clean", "age_years"]

normal_pvalue(t) = erfc(abs(t) / sqrt(2.0))
isvalidnum(x) = !ismissing(x) && isfinite(Float64(x))

function parse_cli(args)
    reps, seed, check_only = 9999, 20260711, false
    i = 1
    while i <= length(args)
        if args[i] == "--reps"
            reps = parse(Int, args[i+1]); i += 2
        elseif args[i] == "--seed"
            seed = parse(Int, args[i+1]); i += 2
        elseif args[i] == "--check-only"
            check_only = true; i += 1
        else
            error("Unknown argument: $(args[i])")
        end
    end
    (; reps, seed, check_only)
end

function load_reg3()
    df = CSV.read(CORE, DataFrame)
    df.Date = Date.(string.(df.Date))
    df.year = year.(df.Date)
    needed = vcat(["fwd_maxdd_12w", "high_stress", "stress_index"], FRAG, STRUCT)
    keep = map(eachrow(df)) do r
        (!ismissing(r.category_bucket)) && String(r.category_bucket) != "Other" &&
            all(isvalidnum(r[Symbol(c)]) for c in needed)
    end
    df[keep, :]
end

# patsy-compatible treatment coding: sorted levels, first dropped
function dummies!(cols, names, vals, prefix)
    levels = sort(unique(string.(vals)))
    for lev in levels[2:end]
        push!(cols, Float64.(string.(vals) .== lev))
        push!(names, "$prefix[$lev]")
    end
end

function design(df::DataFrame, interact_with::String)
    n = nrow(df)
    cols = Vector{Vector{Float64}}(); names = String[]
    push!(cols, ones(n)); push!(names, "(Intercept)")
    for c in ["vol_12w", interact_with]
        push!(cols, Float64.(df[!, c])); push!(names, c)
    end
    push!(cols, Float64.(df.vol_12w) .* Float64.(df[!, interact_with]))
    push!(names, "vol_12w:$interact_with")
    for c in ["downside_vol_12w", "maxdd_12w", "log_assets", "ER_clean", "age_years"]
        push!(cols, Float64.(df[!, c])); push!(names, c)
    end
    dummies!(cols, names, df.category_bucket, "C(category_bucket)")
    dummies!(cols, names, df.year, "C(year)")
    hcat(cols...), names
end

cluster_ids(v) = begin
    levels = sort(unique(v)); idmap = Dict(l => i for (i, l) in enumerate(levels))
    Int64[idmap[x] for x in v]
end

function main()
    args = parse_cli(ARGS)
    df = load_reg3()
    y = Float64.(df.fwd_maxdd_12w)
    stress_weeks = length(unique(df.Date[df.high_stress .== 1]))
    @printf("reg3: %d rows, %d funds, %d weeks (%d high-stress)\n",
            nrow(df), length(unique(df.Symbol)), length(unique(df.Date)), stress_weeks)

    ref = CSV.read(REF, DataFrame)
    refmap = Dict((String(r.spec), String(r.var)) => Float64(r.coef) for r in eachrow(ref))
    pmap   = Dict((String(r.spec), String(r.var)) =>
                  (p_symbol = Float64(r.p_symbol), p_date = Float64(r.p_date),
                   p_cgm = Float64(r.p_cgm)) for r in eachrow(ref))

    id_date = cluster_ids(df.Date)
    id_sym  = cluster_ids(string.(df.Symbol))

    out = NamedTuple[]
    for (spec, ivar, focal) in [
        ("H4 binary (m3b)", "high_stress",
         ["vol_12w", "high_stress", "vol_12w:high_stress"]),
        ("H4 continuous (m3c)", "stress_index",
         ["vol_12w", "stress_index", "vol_12w:stress_index"]),
    ]
        X, names = design(df, ivar)
        beta = X \ y
        ok = true
        for v in focal
            idx = findfirst(==(v), names)
            Δ = beta[idx] - refmap[(spec, v)]
            pass = abs(Δ) <= 5e-6
            ok &= pass
            @printf("  parity %-22s %-22s coef=% .6f Δ=%+.2e %s\n",
                    spec, v, beta[idx], Δ, pass ? "OK" : "FAIL")
        end
        ok || error("Point-estimate parity failed for $spec; aborting.")
        args.check_only && continue

        for v in focal
            v == "vol_12w" && continue   # bootstrap the stress terms only
            idx = findfirst(==(v), names)
            R = zeros(1, length(names)); R[1, idx] = 1.0
            p_wd = Float64(WildBootTests.p(wildboottest(R, [0.0]; resp = y,
                predexog = X, clustid = id_date, reps = args.reps,
                rng = MersenneTwister(args.seed), auxwttype = :rademacher,
                getci = false, getplot = false)))
            p_ws = Float64(WildBootTests.p(wildboottest(R, [0.0]; resp = y,
                predexog = X, clustid = id_sym, reps = args.reps,
                rng = MersenneTwister(args.seed), auxwttype = :rademacher,
                getci = false, getplot = false)))
            r = pmap[(spec, v)]
            @printf("  boot   %-22s %-22s p_sym=%.4f p_date=%.4f p_cgm=%.4f p_wild_date=%.4f p_wild_sym=%.4f\n",
                    spec, v, r.p_symbol, r.p_date, r.p_cgm, p_wd, p_ws)
            push!(out, (spec = spec, var = v, coef = beta[idx],
                        p_symbol = r.p_symbol, p_date = r.p_date, p_cgm = r.p_cgm,
                        p_wild_date = p_wd, p_wild_symbol = p_ws,
                        n_reps = args.reps, seed = args.seed,
                        stress_weeks = stress_weeks))
        end
    end

    if !args.check_only
        CSV.write(OUT, DataFrame(out))
        println("\nWrote $OUT")
    else
        println("\nCheck-only complete; no bootstrap CSV written.")
    end
end

main()
