"""Create, verify, or restore a local source snapshot without credentials or data refresh."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import platform
import re
import subprocess
import sys
import sysconfig
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SUFFIXES = {".py", ".ipynb", ".md", ".json", ".toml", ".jl", ".txt",
                   ".sh", ".ps1", ".latex", ".tex", ".css"}


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def source_paths(root: Path) -> list[Path]:
    paths = set()
    for folder in ("src", "scripts", "tests", "notebooks", "docs", "julia", "legacy"):
        paths.update(path for path in (root / folder).rglob("*")
                     if path.is_file() and path.suffix in SOURCE_SUFFIXES
                     and not any(part in {"__pycache__", ".ipynb_checkpoints", "figures", "tables", "arxiv_submission"}
                                 for part in path.relative_to(root).parts)
                     and not path.is_relative_to(root / "legacy/unified/data"))
    paths.update((root / "data/manifests").glob("*.json"))
    paths.update(root.glob("requirements*.txt"))
    for name in ("README.md", "REPRODUCING.md", "LICENSE", ".gitignore", ".gitattributes", "pyrightconfig.json", "study_config.json"):
        if (root / name).is_file():
            paths.add(root / name)
    return sorted(paths)


def snapshot(root: Path, snapshot_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", snapshot_id):
        raise ValueError("Use a simple snapshot ID")
    destination = root / "results/preservation" / snapshot_id
    if destination.exists():
        raise FileExistsError("Snapshot exists; verify it or choose a new ID")
    contents = {}
    for path in source_paths(root):
        if path.is_symlink() or getattr(path.stat(), "st_flags", 0) & 0x40000000:
            raise ValueError(f"Source must be a local regular file: {path}")
        contents[path.relative_to(root).as_posix()] = path.read_bytes()
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                              text=True, check=True).stdout.strip()
    environment = dict(path.name.removesuffix(".dist-info").rsplit("-", 1)
                       for path in Path(sysconfig.get_path("purelib")).glob("*.dist-info"))
    manifest = {"schema_version": 1, "snapshot_id": snapshot_id, "base_revision": revision,
                "files": {name: digest(payload) for name, payload in contents.items()},
                "python": platform.python_version(), "platform": platform.platform(),
                "distributions": dict(sorted(environment.items())),
                "environment_source": "installed dist-info directory names; no metadata hydration",
                "data_included": False, "credentials_included": False,
                "legacy_empirical_reproduction_certified": False}
    destination.mkdir(parents=True)
    with zipfile.ZipFile(destination / "sources.zip", "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in contents.items():
            archive.writestr(name, payload)
    manifest["archive_sha256"] = digest((destination / "sources.zip").read_bytes())
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    verify(destination)
    return destination


def verify(destination: Path) -> dict:
    manifest = json.loads((destination / "manifest.json").read_text())
    archive_path = destination / "sources.zip"
    if digest(archive_path.read_bytes()) != manifest["archive_sha256"]:
        raise ValueError("Archive hash mismatch")
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != set(manifest["files"]):
            raise ValueError("Archive inventory mismatch")
        for name in names:
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name:
                raise ValueError("Unsafe archive path")
            if digest(archive.read(name)) != manifest["files"][name]:
                raise ValueError(f"Source hash mismatch: {name}")
    return manifest


def restore(destination: Path, target: Path) -> None:
    manifest = verify(destination)
    if target.exists():
        raise FileExistsError("Restore target must not exist")
    target.mkdir(parents=True)
    with zipfile.ZipFile(destination / "sources.zip") as archive:
        for name in manifest["files"]:
            path = target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(archive.read(name))
    for name, expected in manifest["files"].items():
        if digest((target / name).read_bytes()) != expected:
            raise ValueError(f"Restoration mismatch: {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-id", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--restore-to", type=Path)
    args = parser.parse_args()
    try:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.snapshot_id):
            raise ValueError("Use a simple snapshot ID")
        destination = ROOT / "results/preservation" / args.snapshot_id
        if args.restore_to is not None:
            restore(destination, args.restore_to)
        elif args.verify:
            verify(destination)
        else:
            snapshot(ROOT, args.snapshot_id)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print(f"Preservation failed: {exc}", file=sys.stderr)
        return 1
    print("Source snapshot verified. Licensed data and empirical legacy recovery remain separate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
