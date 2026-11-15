#!/usr/bin/env python3
"""Prepare the ChartSearchAI ESM overlay directory for the frontend image."""

from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
from pathlib import Path

APP_KEY = "@openmrs/esm-chartsearchai-app"
ENTRYPOINT_JS = "openmrs-esm-chartsearchai-app.js"
PRECOMPRESS_SUFFIXES = {".js", ".css", ".json", ".map"}


def write_gzip(path: Path) -> None:
    """Write a deterministic .gz sibling alongside path."""
    compressed = gzip.compress(path.read_bytes(), compresslevel=9, mtime=0)
    gz_path = path.with_name(f"{path.name}.gz")
    gz_path.write_bytes(compressed)
    os.chmod(gz_path, 0o644)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-importmap", type=Path, required=True)
    parser.add_argument("--base-registry", type=Path, required=True)
    parser.add_argument("--esm-dist", type=Path, required=True)
    parser.add_argument("--esm-sha", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    esm_sha = args.esm_sha.strip()
    if len(esm_sha) < 12:
        raise ValueError(f"--esm-sha must be at least 12 characters: {esm_sha!r}")

    entrypoint = args.esm_dist / ENTRYPOINT_JS
    routes_file = args.esm_dist / "routes.json"
    if not entrypoint.is_file():
        raise FileNotFoundError(f"Missing built ESM entrypoint: {entrypoint}")
    if not routes_file.is_file():
        raise FileNotFoundError(f"Missing built routes manifest: {routes_file}")

    if args.out_dir.exists():
        shutil.rmtree(args.out_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    bundle_dir_name = f"openmrs-esm-chartsearchai-app-1.0.0-git{esm_sha[:12]}"
    bundle_dest = args.out_dir / bundle_dir_name
    shutil.copytree(args.esm_dist, bundle_dest)
    for root, dirs, files in os.walk(bundle_dest):
        os.chmod(root, 0o755)
        for d in dirs:
            os.chmod(Path(root) / d, 0o755)
        for f in files:
            p = Path(root) / f
            os.chmod(p, 0o644)
            if p.suffix in PRECOMPRESS_SUFFIXES:
                write_gzip(p)

    importmap = json.loads(args.base_importmap.read_text(encoding="utf-8"))
    imports = importmap.setdefault("imports", {})
    if not isinstance(imports, dict):
        raise ValueError("importmap.json 'imports' must be a JSON object")
    imports[APP_KEY] = f"./{bundle_dir_name}/{ENTRYPOINT_JS}"
    importmap_out = args.out_dir / "importmap.json"
    importmap_out.write_text(
        json.dumps(importmap, indent=2) + "\n", encoding="utf-8"
    )
    os.chmod(importmap_out, 0o644)
    write_gzip(importmap_out)

    registry = json.loads(args.base_registry.read_text(encoding="utf-8"))
    if not isinstance(registry, dict):
        raise ValueError("routes.registry.json must be a JSON object")
    registry[APP_KEY] = json.loads(routes_file.read_text(encoding="utf-8"))
    registry_out = args.out_dir / "routes.registry.json"
    registry_out.write_text(
        json.dumps(registry, indent=2) + "\n", encoding="utf-8"
    )
    os.chmod(registry_out, 0o644)
    write_gzip(registry_out)

    sha_out = args.out_dir / "chartsearchai-esm.sha"
    sha_out.write_text(f"{esm_sha}\n", encoding="utf-8")
    os.chmod(sha_out, 0o644)
    write_gzip(sha_out)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
