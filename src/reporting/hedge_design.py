"""Read-only research views and write-once paper artifacts; no hedge estimation."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import stat

import numpy as np
import pandas as pd


MENUS = ("direct", "treasury_substitute", "combined")
LABELS = {"direct": "Direct LQD", "treasury_substitute": "Treasury substitute", "combined": "Combined"}
COLORS = {"direct": "#bd6333", "treasury_substitute": "#307d8c", "combined": "#293f70"}
CAUTION = "Conditional research | OI is not executable depth | Not evidence of hedge performance"
REPORT_SOURCES = (
    "src/reporting/hedge_design.py", "scripts/reproduce_hedge_paper.py",
    "notebooks/06_hedge_frontiers.ipynb", "docs/missing_hedge_draft.md",
    "requirements.txt",
)
REPORT_VERSIONS = (
    "numpy", "pandas", "matplotlib", "pillow", "fonttools", "contourpy", "kiwisolver",
    "nbformat", "nbclient", "nbconvert", "ipykernel", "ipython", "jupyter_client", "jinja2",
)


def identified_directory(root: Path, identifier: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", identifier):
        raise ValueError("Invalid run/build ID")
    return safe_path(root, identifier)


def safe_path(root: Path, name: str) -> Path:
    if root.is_symlink():
        raise ValueError(f"Symlink artifact root: {root}")
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError(f"Unsafe artifact path: {name}")
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Symlink artifact path: {name}")
    if not current.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Escaping artifact path: {name}")
    return current


def digest(path: Path) -> str:
    if getattr(path.stat(), "st_flags", 0) & getattr(stat, "SF_DATALESS", 0):
        raise ValueError(f"Cloud-only input; no implicit hydration: {path}")
    result = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def verify_hashes(root: Path, hashes: dict) -> None:
    if not hashes:
        raise ValueError("Empty artifact inventory")
    for name, expected in hashes.items():
        if digest(safe_path(root, name)) != expected:
            raise ValueError(f"Changed artifact: {name}")


def load_run(root: Path, run_id: str) -> tuple[dict, dict[str, pd.DataFrame]]:
    """Check saved-output integrity, not source versions or economic readiness."""
    directory = identified_directory(root / "results/hedge_design", run_id)
    manifest = json.loads(safe_path(directory, "manifest.json").read_text())
    if manifest["run_id"] != run_id or not manifest.get("phase3"):
        raise ValueError("A completed Phase 3 run is required")
    verify_hashes(directory, manifest["outputs"])
    frames = {Path(name).stem: pd.read_csv(directory / name)
              for name in manifest["outputs"] if name.endswith(".csv")}
    for name in ("robust_frontier", "quote_sensitivity_frontier", "robust_duals"):
        if not frames[name]["verified"].eq(True).all():
            raise ValueError(f"Unverified research results: {name}")
    for name in ("robust_invariants", "quote_sensitivity_invariants"):
        if not frames[name]["ok"].eq(True).all():
            raise ValueError(f"Failed research invariant: {name}")
    return manifest, frames


def access_labels(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["access"] = result["oi_fraction"].map(
        lambda value: "Uncapped" if pd.isna(value) else f"{value:.0%} OI assumption")
    return result


def loss_units(frame: pd.DataFrame, position_usd: float) -> pd.DataFrame:
    result = access_labels(frame)
    for name in frame.columns:
        if name.endswith("_usd"):
            result[name.removesuffix("_usd") + "_bps"] = frame[name] / position_usd * 10000
    return result


def market_anatomy(chains: pd.DataFrame) -> pd.DataFrame:
    """Recorded OI stocks by date/ETF/side, never summed through time as volume."""
    keys = ["ticker", "snap_date", "right", "expiry", "strike"]
    if chains[keys].isna().any().any() or chains.duplicated(keys).any():
        raise ValueError("Missing or duplicate contract keys in anatomy input")
    if not chains["right"].isin(["C", "P"]).all():
        raise ValueError("Unknown option side")
    work = chains.copy()
    interest = pd.to_numeric(work["open_interest"], errors="coerce")
    valid = np.isfinite(interest) & interest.ge(0)
    work["valid_oi"] = interest.where(valid)
    work["unknown_or_invalid_oi"] = ~valid
    work["zero_oi"] = valid & interest.eq(0)
    return work.groupby(["snap_date", "ticker", "right"], as_index=False).agg(
        contract_rows=("strike", "size"),
        recorded_oi=("valid_oi", lambda values: values.sum(min_count=1)),
        unknown_or_invalid_oi=("unknown_or_invalid_oi", "sum"),
        zero_oi=("zero_oi", "sum"),
    )


def validate_common_outcomes(frame: pd.DataFrame, summary: pd.DataFrame, position_usd: float) -> None:
    work = access_labels(frame)
    reported = access_labels(summary)
    keys = ["policy", "access", "decision_date"]
    if work.duplicated(keys).any() or work[keys].isna().any().any():
        raise ValueError("Duplicate or missing outcome keys")
    reference = set(work["decision_date"])
    if set(work["access"]) != {"Uncapped", "5% OI assumption"}:
        raise ValueError("Both uncapped and 5% OI comparisons are required")
    if not reference or reported.duplicated(["policy", "access"]).any():
        raise ValueError("Invalid outcome summary")
    expected = {(policy, access) for policy in ["unhedged", "duration"] +
                [f"{method}__{menu}" for method in ("nominal", "robust") for menu in MENUS]
                for access in work["access"].unique()}
    if set(work.groupby(["policy", "access"]).groups) != expected:
        raise ValueError("Incomplete common-policy comparison")
    if set(reported.groupby(["policy", "access"]).groups) != expected:
        raise ValueError("Incomplete outcome summary")
    for (policy, access), rows in work.groupby(["policy", "access"]):
        if set(rows["decision_date"]) != reference:
            raise ValueError("Policies do not share identical outcome dates")
        losses = rows["realized_net_loss_usd"] / position_usd * 10000
        saved = reported.loc[(reported.policy == policy) & (reported.access == access)].iloc[0]
        actual = [len(rows), losses.mean(), losses.max(), rows.spent_usd.mean() / position_usd * 10000]
        if not np.isfinite(losses).all() or not np.allclose(
            actual, saved[["matched_dates", "mean_loss_bps", "worst_loss_bps", "mean_spent_bps"]].astype(float),
            atol=1e-8, rtol=1e-10,
        ):
            raise ValueError("Saved outcome summary disagrees with common-date outcomes")


def paper_tables(manifest: dict, frames: dict, chains: pd.DataFrame) -> dict[str, pd.DataFrame]:
    position = manifest["config"]["position_usd"]
    validate_common_outcomes(frames["robust_held_out_outcomes"], frames["robust_held_out_summary"], position)
    candidates = frames["robust_candidates"].query("menu == 'combined'")
    moneyness = candidates.groupby("ticker", as_index=False).agg(
        eligible_puts=("strike", "size"), min_strike_spot=("strike_spot_ratio", "min"),
        max_strike_spot=("strike_spot_ratio", "max"),
        zero_oi=("open_interest", lambda values: values.eq(0).sum()),
        unknown_oi=("open_interest", lambda values: values.isna().sum()),
    )
    frontier = loss_units(frames["robust_frontier"], position)
    return {
        "market_anatomy": market_anatomy(chains), "moneyness": moneyness,
        "frontiers": frontier,
        "design_comparison": frontier.loc[(frontier.budget_bps == 50) &
            (frontier.tail_level == .9) & frontier.oi_fraction.isna(),
            ["menu", "method", "nominal_cvar_bps", "worst_model_cvar_bps", "spent_bps"]],
        "quote_sensitivity": loss_units(frames["quote_sensitivity_frontier"], position),
        "outcomes": access_labels(frames["robust_held_out_summary"]),
        "paired_outcomes": access_labels(frames["robust_held_out_paired"]),
        "support": frames["robust_support"].copy(),
        "tlt_control": access_labels(frames["control_cvar_frontier"]),
        "scale_control": frames["cvar_scale_control"].copy(),
        "selected_positions": frames["robust_positions"].copy(),
        "subsequent_dates": frames["robust_held_out_dates"].copy(),
        "duals": frames["robust_duals"].copy(),
    }


def markdown_table(frame: pd.DataFrame) -> str:
    def format_value(value):
        if pd.isna(value):
            return "—"
        if isinstance(value, (float, np.floating)):
            return f"{value:.2f}"
        return str(value).replace("|", "\\|").replace("\n", " ")
    rows = ["| " + " | ".join(map(str, frame.columns)) + " |",
            "| " + " | ".join(["---"] * len(frame.columns)) + " |"]
    rows.extend("| " + " | ".join(format_value(value) for value in row) + " |"
                for row in frame.itertuples(index=False, name=None))
    return "\n".join(rows)


def render_draft(template: str, tables: dict, metrics: dict) -> str:
    def replace(match):
        kind, name = match.groups()
        if kind == "table":
            return markdown_table(tables[name])
        return str(metrics[name])
    rendered = re.sub(r"\{\{(table|metric):([a-z_]+)\}\}", replace, template)
    if "{{" in rendered:
        raise ValueError("Unresolved draft placeholder")
    return rendered


def draw_figures(directory: Path, tables: dict, manifest: dict, frames: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "figure.facecolor": "white", "savefig.facecolor": "white"})
    directory.mkdir()

    def save(figure, name):
        figure.text(.02, .015, CAUTION, fontsize=8, color="#555555")
        figure.tight_layout(rect=(0, .055, 1, .97))
        figure.savefig(directory / f"{name}.png", dpi=170)
        plt.close(figure)

    date = manifest["config"]["decision_date"]
    anatomy = tables["market_anatomy"].query("snap_date == @date")
    figure, axis = plt.subplots(figsize=(9, 4.6))
    tickers = manifest["config"]["tickers"]
    for offset, side, color in [(-.19, "C", "#293f70"), (.19, "P", "#bd6333")]:
        values = anatomy.query("right == @side").set_index("ticker").reindex(tickers).recorded_oi
        axis.bar(np.arange(len(tickers)) + offset, values, width=.36, color=color,
                 label="Calls" if side == "C" else "Puts")
    axis.set(xticks=np.arange(len(tickers)), xticklabels=tickers, ylabel="Recorded OI (contracts)",
             title=f"Observed book at {date} | all strikes and expirations")
    axis.legend(frameon=False)
    save(figure, "market_anatomy")

    figure, axes = plt.subplots(2, 2, figsize=(10, 7), sharex=True, sharey="row")
    frontier = tables["frontiers"].query("method == 'nominal'")
    for row_index, alpha in enumerate([.9, .95]):
        for column_index, access in enumerate(["Uncapped", "5% OI assumption"]):
            axis = axes[row_index, column_index]
            for menu in MENUS:
                rows = frontier.query("tail_level == @alpha and access == @access and menu == @menu").sort_values("budget_bps")
                axis.plot(rows.budget_bps, rows.nominal_cvar_bps, marker="o", markersize=4,
                          color=COLORS[menu], label=LABELS[menu], linestyle=":" if menu == "combined" else "-")
            axis.set(title=f"{alpha:.0%} historical CVaR | {access}", ylabel="Loss (bps)", xlabel="Upfront budget (bps)")
            axis.grid(alpha=.15)
    axes[0, 0].legend(frameon=False, fontsize=8)
    save(figure, "nominal_frontiers")

    figure, axis = plt.subplots(figsize=(9, 4.6))
    candidates = frames["robust_candidates"].query("menu == 'combined'")
    for index, ticker in enumerate(tickers):
        values = candidates.query("ticker == @ticker").strike_spot_ratio
        axis.scatter(values, np.full(len(values), index), marker="|", s=220, color="#293f70")
    axis.axvspan(.95, 1.05, color="#307d8c", alpha=.15, label="Matched-moneyness sensitivity band")
    axis.axvline(1, color="#888888", linewidth=.8)
    axis.set(yticks=np.arange(len(tickers)), yticklabels=tickers, xlabel="Strike / entry spot",
             title="Eligible puts are not moneyness-matched", ylim=(-.6, len(tickers) - .4))
    axis.legend(frameon=False, loc="upper right", fontsize=8)
    save(figure, "moneyness")

    figure, axes = plt.subplots(1, 2, figsize=(10, 4.8), sharey=True)
    comparison = tables["design_comparison"]
    for axis, column, title in zip(axes, ["nominal_cvar_bps", "worst_model_cvar_bps"],
                                 ["Historical CVaR", "Worst of three model CVaRs"]):
        for offset, method, color in [(-.18, "nominal", "#307d8c"), (.18, "robust", "#293f70")]:
            values = comparison.query("method == @method").set_index("menu").reindex(MENUS)[column]
            axis.bar(np.arange(3) + offset, values, .34, label=method.title(), color=color)
        axis.set(xticks=np.arange(3), xticklabels=["Direct", "Treasury", "Combined"], title=title, ylabel="Loss (bps)")
        axis.legend(frameon=False)
    axes[0].set_ylim(0, comparison.worst_model_cvar_bps.max() * 1.22)
    figure.suptitle("Same policies under both risk measures | 50 bp budget, 90% tail, uncapped", fontsize=11)
    save(figure, "model_tradeoff")

    paired = tables["paired_outcomes"]
    figure, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True, sharey=True)
    for axis, access in zip(axes, ["Uncapped", "5% OI assumption"]):
        for menu in MENUS:
            rows = paired.query("access == @access and menu == @menu").sort_values("decision_date")
            axis.plot(rows.decision_date, rows.robust_minus_nominal_bps, marker="o", markersize=4,
                      color=COLORS[menu], label=LABELS[menu])
        axis.axhline(0, color="#777777", linewidth=.8)
        axis.set(title=f"{access} | positive = robust loses more", ylabel="Robust minus nominal (bps)")
    axes[0].legend(frameon=False, fontsize=8)
    axes[1].tick_params(axis="x", rotation=60)
    save(figure, "paired_outcomes")

    quote = pd.concat([tables["frontiers"], tables["quote_sensitivity"]], ignore_index=True)
    quote = quote.query("method == 'nominal' and tail_level == .9 and budget_bps == 50 and access == 'Uncapped'")
    rules = ["baseline", "tight_spread", "zero_bid", "matched_moneyness"]
    figure, axis = plt.subplots(figsize=(10, 4.8))
    for index, menu in enumerate(MENUS):
        rows = quote.query("menu == @menu").set_index("quote_rule").reindex(rules)
        axis.bar(np.arange(4) + (index - 1) * .25, rows.nominal_cvar_bps, .24,
                 label=LABELS[menu], color=COLORS[menu])
    axis.set(xticks=np.arange(4), xticklabels=["Baseline", "20% spread", "Add zero bids", "0.95–1.05 strike/spot"],
             ylabel="Historical CVaR (bps)", title="Quote sensitivity | 50 bp budget, 90% tail, uncapped")
    axis.legend(frameon=False, fontsize=8)
    axis.set_ylim(0, quote.nominal_cvar_bps.max() * 1.23)
    save(figure, "quote_sensitivity")


def build_paper(root: Path, run_id: str, build_id: str) -> Path:
    destination = identified_directory(root / "results/hedge_paper", build_id)
    if destination.exists():
        raise ValueError(f"Refusing to overwrite {destination}")
    manifest, frames = load_run(root, run_id)
    if manifest["config"] != json.loads((root / "study_config.json").read_text()):
        raise ValueError("This paper template requires the pinned study_config.json experiment")
    chain_name = "data/processed/options_screen/chains.csv"
    verify_hashes(root, {chain_name: manifest["sources"][chain_name]})
    chains = pd.read_csv(root / chain_name)
    tables = paper_tables(manifest, frames, chains)
    metrics = {"run_id": run_id, "chain_rows": len(chains), "etfs": chains.ticker.nunique(),
               "snapshots": chains.snap_date.nunique(), "first_snapshot": chains.snap_date.min(),
               "last_snapshot": chains.snap_date.max(), "scenario_count": manifest["scenario_count"],
               "training_end": manifest["last_training_end"], "sessions": manifest["trading_sessions"],
               "matched_dates": manifest["phase3"]["matched_dates"]}
    draft = render_draft((root / "docs/missing_hedge_draft.md").read_text(), tables, metrics)
    sources = {name: digest(root / name) for name in REPORT_SOURCES}
    sources[chain_name] = manifest["sources"][chain_name]
    sources[f"results/hedge_design/{run_id}/manifest.json"] = digest(
        root / "results/hedge_design" / run_id / "manifest.json")
    destination.mkdir(parents=True)
    (destination / "tables").mkdir()
    for name, frame in tables.items():
        frame.to_csv(destination / "tables" / f"{name}.csv", index=False)
    draw_figures(destination / "figures", tables, manifest, frames)
    (destination / "missing_hedge_draft.md").write_text(draft)
    (destination / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    bundle = {"schema_version": 1, "build_id": build_id, "run_id": run_id,
              "status": "conditional_research_not_publication_certified", "sources": sources,
              "versions": {name: importlib.metadata.version(name) for name in REPORT_VERSIONS},
              "outputs": {path.relative_to(destination).as_posix(): digest(path)
                          for path in sorted(destination.rglob("*")) if path.is_file()}}
    (destination / "manifest.json").write_text(json.dumps(bundle, indent=2) + "\n")
    return destination


def load_bundle(root: Path, build_id: str) -> tuple[dict, dict[str, pd.DataFrame]]:
    """Notebook reader: saved artifacts only; no market inputs or solver imports."""
    directory = identified_directory(root / "results/hedge_paper", build_id)
    manifest = json.loads(safe_path(directory, "manifest.json").read_text())
    if manifest["build_id"] != build_id or manifest["schema_version"] != 1:
        raise ValueError("Invalid paper manifest")
    verify_hashes(directory, manifest["outputs"])
    return manifest, {Path(name).stem: pd.read_csv(directory / name)
                      for name in manifest["outputs"] if name.startswith("tables/") and name.endswith(".csv")}


def verify_paper(root: Path, build_id: str) -> dict:
    manifest, _ = load_bundle(root, build_id)
    verify_hashes(root, manifest["sources"])
    for name, version in manifest["versions"].items():
        if importlib.metadata.version(name) != version:
            raise ValueError(f"Changed reporting dependency: {name}")
    return manifest
