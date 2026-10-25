#!/usr/bin/env python3
"""Build deterministic Claude plugin/source ZIPs without third-party packages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VALID_NAME = re.compile(r"[A-Za-z0-9 _./(),-]+\Z")
ARCHIVE_TIME = (2026, 10, 26, 0, 0, 0)


def collect_files(root: Path) -> list[Path]:
    files = []
    for path in root.rglob("*"):
        relative_parts = path.relative_to(root).parts
        if any(part in {".git", "__pycache__", ".pytest_cache"} for part in relative_parts):
            continue
        if path.is_symlink():
            raise ValueError(f"Symlinks cannot be packaged: {path}")
        if not path.is_file():
            continue
        archive_path = f"{root.name}/{path.relative_to(root).as_posix()}"
        if not VALID_NAME.fullmatch(archive_path) or len(archive_path) > 472:
            raise ValueError(f"Unsupported Claude ZIP path: {archive_path}")
        if path.suffix.lower() in {".zip", ".plugin"}:
            raise ValueError(f"Nested release archive is forbidden: {path}")
        files.append(path)
    if len(files) > 5000 or sum(p.stat().st_size for p in files) > 200_000_000:
        raise ValueError("Release exceeds Claude archive limits")
    return sorted(files, key=lambda p: p.relative_to(root).as_posix())


def package(source: Path, destination: Path):
    files = collect_files(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9, strict_timestamps=True) as out:
        for path in files:
            member = f"{source.name}/{path.relative_to(source).as_posix()}"
            info = zipfile.ZipInfo(member, date_time=ARCHIVE_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            out.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED,
                         compresslevel=9)
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise ValueError(f"ZIP CRC test failed: {destination}")
        if sum(x.filename.endswith(".claude-plugin/plugin.json") for x in archive.infolist()) != 1:
            raise ValueError("Claude plugin ZIP needs exactly one manifest")
    print(f"{destination}: {len(files)} files, {destination.stat().st_size} bytes")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    version = json.loads((ROOT / ".claude-plugin/plugin.json").read_text("utf-8"))["version"]
    install = args.output_dir / f"project-graphify-plugin-v{version}.zip"
    source = args.output_dir / f"project-graphify-github-source-v{version}.zip"
    package(ROOT, install)
    shutil.copyfile(install, source)
    print(f"{source}: byte-identical GitHub source archive")


if __name__ == "__main__":
    main()
