"""Explicit offline science-to-paper build; never refresh inputs or overwrite runs."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.reporting.hedge_design import (
    build_paper, digest, identified_directory, verify_hashes, verify_paper,
)


def science(run_id: str, verify: bool) -> None:
    if not verify and not json.loads((ROOT / "study_config.json").read_text()).get("robust_enabled"):
        raise ValueError("Paper builds require robust_enabled: true in study_config.json")
    command = [sys.executable, str(ROOT / "scripts/run_hedge_design.py"), "--run-id", run_id]
    command += ["--verify"] if verify else ["--config", "study_config.json"]
    subprocess.run(command, cwd=ROOT, check=True)


def execute_review(destination: Path) -> None:
    import nbformat
    from nbclient import NotebookClient
    from nbconvert import HTMLExporter
    from jupyter_client import KernelManager

    review = destination / "review"
    review.mkdir()
    notebook = nbformat.read(ROOT / "notebooks/06_hedge_frontiers.ipynb", as_version=4)
    environment = dict(os.environ, HEDGE_PAPER_BUILD=destination.name)
    manager = KernelManager(kernel_name="python3")
    manager.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
    client = NotebookClient(notebook, timeout=180, kernel_name="python3", km=manager,
                            resources={"metadata": {"path": str(ROOT)}})
    client.execute(env=environment, cleanup_kc=True)
    nbformat.write(notebook, review / "06_hedge_frontiers.ipynb")
    html, _ = HTMLExporter().from_notebook_node(notebook)
    (review / "06_hedge_frontiers.html").write_text(html)
    manifest = {"paper_manifest_sha256": digest(destination / "manifest.json"),
                "outputs": {path.name: digest(path) for path in sorted(review.iterdir())}}
    (review / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def verify_review(destination: Path) -> None:
    review = destination / "review"
    manifest = json.loads((review / "manifest.json").read_text())
    if digest(destination / "manifest.json") != manifest["paper_manifest_sha256"]:
        raise ValueError("Review no longer matches paper bundle")
    verify_hashes(review, manifest["outputs"])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-id", required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--reuse-run", action="store_true", help="Verify and report an existing run instead of solving")
    parser.add_argument("--verify", action="store_true", help="Check science, reporting sources, artifacts and executed review")
    args = parser.parse_args(argv)
    if args.verify and (args.reuse_run or args.run_id):
        parser.error("--verify only needs --build-id")
    if not args.verify and not args.run_id:
        parser.error("--run-id is required for a new build")
    try:
        destination = identified_directory(ROOT / "results/hedge_paper", args.build_id)
        if args.verify:
            manifest = verify_paper(ROOT, args.build_id)
            science(manifest["run_id"], verify=True)
            verify_review(destination)
            print("Science, paper and executed review MATCH; empirical validation remains conditional.")
            return 0
        identified_directory(ROOT / "results/hedge_design", args.run_id)
        if destination.exists():
            raise ValueError("Build ID already exists; use a new ID")
        if not args.reuse_run:
            science(args.run_id, verify=False)
        science(args.run_id, verify=True)
        destination = build_paper(ROOT, args.run_id, args.build_id)
        execute_review(destination)
        verify_paper(ROOT, args.build_id)
        verify_review(destination)
        print(f"Created {destination.relative_to(ROOT)} (paper, figures, tables, executed notebook and HTML)")
        print("Conditional research only. No acquisition or legacy stages were invoked.")
        return 0
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(f"Paper reproduction failed: {exc}. Existing/partial outputs are preserved; use new IDs.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
