#!/usr/bin/env python3
"""Build a GrapheneOS vendor/extras overlay with Google Sans Flex.

Downloads GoogleSansFlex-Regular.ttf from Android's official source and
assembles it with the font customization XML and framework resource overlay.
"""

from __future__ import annotations

import argparse
import base64
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATE_DIR = ROOT / "frozen_fonts"
OUTPUT = ROOT / "vendor_extras_google_sans_flex.tar.gz"
FONT_NAME = "GoogleSansFlex-Regular.ttf"
FONT_URL = (
    "https://android.googlesource.com/platform/external/robolectric/+/"
    "refs/heads/main/nativeruntime/src/main/resources/fonts/"
    f"{FONT_NAME}?format=TEXT"
)
USER_AGENT = "grapheneos-google-sans-flex-builder/1"

OVERLAY_REL = Path("overlay/common/frameworks/base/core/res/res/values")
TEMPLATES = {
    "extras.mk": Path("extras.mk"),
    "fonts_customization.xml": Path("prebuilt/etc/fonts_customization.xml"),
    "Android.bp": Path("prebuilt/etc/Android.bp"),
    "config.xml": OVERLAY_REL / "config.xml",
}


def download_font(dst: Path) -> None:
    print(f"  downloading {FONT_NAME}")
    request = urllib.request.Request(FONT_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        encoded = response.read()

    try:
        font = base64.b64decode(encoded)
    except ValueError as exc:
        raise SystemExit(f"invalid base64 font response: {exc}") from exc
    if not font.startswith((b"\x00\x01\x00\x00", b"OTTO")):
        raise SystemExit("downloaded file is not an OpenType/TrueType font")
    dst.write_bytes(font)


def assemble_tree(tmp: Path) -> Path:
    tree = tmp / "vendor" / "extras"
    (tree / "prebuilt" / "fonts").mkdir(parents=True)
    (tree / "prebuilt" / "etc").mkdir(parents=True)
    (tree / OVERLAY_REL).mkdir(parents=True)

    download_font(tree / "prebuilt" / "fonts" / FONT_NAME)

    for name, rel in TEMPLATES.items():
        src = TEMPLATE_DIR / name
        if not src.exists():
            raise SystemExit(f"missing template: {src}")
        shutil.copy2(src, tree / rel)

    return tree.parent


def build() -> Path:
    with tempfile.TemporaryDirectory(prefix="google-sans-flex-build-", dir=ROOT) as tmp_s:
        vendor_root = assemble_tree(Path(tmp_s))
        if OUTPUT.exists():
            OUTPUT.unlink()
        with tarfile.open(OUTPUT, "w:gz") as tar:
            tar.add(vendor_root, arcname="vendor")
    return OUTPUT


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--check", action="store_true", help="validate templates and font download")
    args = parser.parse_args()

    for name in TEMPLATES:
        if not (TEMPLATE_DIR / name).exists():
            raise SystemExit(f"missing template: {TEMPLATE_DIR / name}")
    if args.check:
        with tempfile.TemporaryDirectory(prefix="google-sans-flex-check-") as tmp_s:
            download_font(Path(tmp_s) / FONT_NAME)
        print("Google Sans Flex templates and download are valid")
        return 0

    out = build()
    print(f"built {out.name} ({out.stat().st_size // 1024} KiB)")
    print(f"deploy with: tar -xzf {out.name} -C /path/to/grapheneos-source")
    return 0


if __name__ == "__main__":
    sys.exit(main())
