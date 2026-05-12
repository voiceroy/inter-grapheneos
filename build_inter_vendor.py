#!/usr/bin/env python3
"""Build a GrapheneOS vendor/extras tarball with feature-frozen Inter fonts.

Queries the rsms/inter GitHub release feed, downloads the latest Inter zip,
applies feature-freezing via pyftfeatfreeze (run with `uvx`), and assembles a
ready-to-extract `vendor/extras/` tree as `vendor_extras_inter-<version>.tar.gz`.

Usage:
  ./build_inter_vendor.py            rebuild if a newer Inter release exists
  ./build_inter_vendor.py --force    rebuild regardless of state file
  ./build_inter_vendor.py --check    print latest vs current tag and exit
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATE_DIR = ROOT / "frozen_fonts"
STATE_FILE = ROOT / ".inter_version"

FEATURES = "zero,cv03,cv04,cv09,cv12,cv13"
TTFS = ("InterVariable.ttf", "InterVariable-Italic.ttf")
RELEASE_API = "https://api.github.com/repos/rsms/inter/releases/latest"
USER_AGENT = "grapheneos-inter-builder/1"

OVERLAY_REL = Path("overlay/common/frameworks/base/core/res/res/values")
TEMPLATES = {
    "extras.mk": Path("extras.mk"),
    "fonts_customization.xml": Path("prebuilt/etc/fonts_customization.xml"),
    "Android.bp": Path("prebuilt/etc/Android.bp"),
    "config.xml": OVERLAY_REL / "config.xml",
}


def _http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def latest_release() -> tuple[str, str]:
    data = json.loads(_http_get(RELEASE_API))
    tag = data["tag_name"]
    version = tag.lstrip("v")
    target = f"Inter-{version}.zip"
    for asset in data["assets"]:
        if asset["name"] == target:
            return tag, asset["browser_download_url"]
    raise SystemExit(f"asset {target} not found in release {tag}")


def current_version() -> str | None:
    return STATE_FILE.read_text().strip() if STATE_FILE.exists() else None


def download(url: str, dst: Path) -> None:
    print(f"  downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as r, dst.open("wb") as f:
        shutil.copyfileobj(r, f)


def freeze(src: Path, dst: Path) -> None:
    print(f"  freezing {src.name}  features={FEATURES}")
    subprocess.run(
        [
            "uvx",
            "--quiet",
            "--from",
            "opentype-feature-freezer",
            "pyftfeatfreeze",
            "-f",
            FEATURES,
            str(src),
            str(dst),
        ],
        check=True,
    )


def assemble_tree(tmp: Path, ttf_src: Path) -> Path:
    tree = tmp / "vendor" / "extras"
    (tree / "prebuilt" / "fonts").mkdir(parents=True)
    (tree / "prebuilt" / "etc").mkdir(parents=True)
    (tree / OVERLAY_REL).mkdir(parents=True)

    for ttf in TTFS:
        freeze(ttf_src / ttf, tree / "prebuilt" / "fonts" / ttf)

    for name, rel in TEMPLATES.items():
        src = TEMPLATE_DIR / name
        if not src.exists():
            raise SystemExit(f"missing template: {src}")
        shutil.copy2(src, tree / rel)

    return tree.parent  # .../vendor


def build(tag: str, url: str) -> Path:
    version = tag.lstrip("v")
    with tempfile.TemporaryDirectory(prefix="inter-build-", dir=ROOT) as tmp_s:
        tmp = Path(tmp_s)
        zip_path = tmp / f"Inter-{version}.zip"
        download(url, zip_path)

        extract_dir = tmp / "inter"
        with zipfile.ZipFile(zip_path) as z:
            for member in TTFS:
                z.extract(member, extract_dir)

        vendor_root = assemble_tree(tmp, extract_dir)

        out = ROOT / f"vendor_extras_inter-{version}.tar.gz"
        if out.exists():
            out.unlink()
        with tarfile.open(out, "w:gz") as tar:
            tar.add(vendor_root, arcname="vendor")
        return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="rebuild even if state file matches latest")
    ap.add_argument("--check", action="store_true", help="print latest vs current tag and exit")
    args = ap.parse_args()

    tag, url = latest_release()
    current = current_version()
    print(f"latest:  {tag}")
    print(f"current: {current or '(none)'}")
    if args.check:
        return 0
    if current == tag and not args.force:
        print("already up to date — pass --force to rebuild")
        return 0

    out = build(tag, url)
    STATE_FILE.write_text(tag + "\n")
    size_kib = out.stat().st_size // 1024
    print(f"\nbuilt {out.name} ({size_kib} KiB)")
    print(f"deploy with: tar -xzf {out.name} -C /path/to/grapheneos-source")
    return 0


if __name__ == "__main__":
    sys.exit(main())
