#!/usr/bin/env python3
"""Disable Seedvault in an AOSP/GrapheneOS tree.

Seedvault is pulled into every product image via a single
`PRODUCT_PACKAGES += Seedvault` line in AOSP's core product makefile:

    build/make/target/product/media_system.mk

There is no build flag to toggle it off, so we comment that line out.
The edit is idempotent and device-independent.

Usage:
  ./patch_seedvault.py --tree <AOSP_ROOT>
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REL_PATH = Path("build/make/target/product/media_system.mk")
MARKER = "# disabled by Inter customisation"

# Active (uncommented) inclusion line.
ACTIVE = re.compile(r"^PRODUCT_PACKAGES \+= Seedvault\s*$", re.MULTILINE)
# Already commented out by us.
DISABLED = re.compile(r"^#\s*PRODUCT_PACKAGES \+= Seedvault\b", re.MULTILINE)


def patch_seedvault(tree: Path) -> str:
    path = tree / REL_PATH
    if not path.is_file():
        raise SystemExit(f"error: makefile not found: {path}")

    text = path.read_text()

    if DISABLED.search(text):
        return f"seedvault: already disabled ({path})"

    new_text, count = ACTIVE.subn(
        f"# PRODUCT_PACKAGES += Seedvault  {MARKER}", text
    )
    if count == 0:
        raise SystemExit(
            f"error: 'PRODUCT_PACKAGES += Seedvault' line not found in {path}\n"
            f"  AOSP may have moved Seedvault's inclusion point; grep the tree:\n"
            f"  grep -rn 'Seedvault' --include='*.mk' ."
        )

    path.write_text(new_text)
    return f"seedvault: disabled {count} line(s) ({path})"


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--tree", required=True, type=Path, help="AOSP root path")
    args = ap.parse_args()

    if not args.tree.is_dir():
        raise SystemExit(f"error: --tree {args.tree} is not a directory")

    print(patch_seedvault(args.tree))
    return 0


if __name__ == "__main__":
    sys.exit(main())
