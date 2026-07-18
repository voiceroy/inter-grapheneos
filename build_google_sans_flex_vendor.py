#!/usr/bin/env python3
"""Build the GrapheneOS vendor/extras overlay for Google Sans Flex.

GoogleSansFlex-Regular.ttf is supplied by the Pixel product partition, so this
package only installs the font customization XML and framework resource overlay.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATE_DIR = ROOT / "frozen_fonts"
OUTPUT = ROOT / "vendor_extras_google_sans_flex.tar.gz"

OVERLAY_REL = Path("overlay/common/frameworks/base/core/res/res/values")
TEMPLATES = {
    "extras.mk": Path("extras.mk"),
    "fonts_customization.xml": Path("prebuilt/etc/fonts_customization.xml"),
    "Android.bp": Path("prebuilt/etc/Android.bp"),
    "config.xml": OVERLAY_REL / "config.xml",
}


def assemble_tree(tmp: Path) -> Path:
    tree = tmp / "vendor" / "extras"
    (tree / "prebuilt" / "etc").mkdir(parents=True)
    (tree / OVERLAY_REL).mkdir(parents=True)

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
    parser.add_argument("--check", action="store_true", help="validate templates without building")
    args = parser.parse_args()

    for name in TEMPLATES:
        if not (TEMPLATE_DIR / name).exists():
            raise SystemExit(f"missing template: {TEMPLATE_DIR / name}")
    if args.check:
        print("Google Sans Flex overlay templates are present")
        return 0

    out = build()
    print(f"built {out.name} ({out.stat().st_size // 1024} KiB)")
    print(f"deploy with: tar -xzf {out.name} -C /path/to/grapheneos-source")
    return 0


if __name__ == "__main__":
    sys.exit(main())
