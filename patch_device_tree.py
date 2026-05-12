#!/usr/bin/env python3
"""Apply per-device tree patches required to wire vendor/extras into a build.

Two operations, both idempotent:

1. Inject a conditional include of vendor/extras/extras.mk into the device .mk
   file, immediately after the adevtool inherit-product line.

2. Rename the runtime_resource_overlay module in
   vendor/google_devices/<device>/overlays/framework-res__<device>__auto_generated_rro_product/Android.bp
   by appending a trailing underscore — works around a name collision the
   auto-generated overlay has with our overlay package.

Usage:
  ./patch_device_tree.py --tree <AOSP_ROOT> --device <name>
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

INCLUDE_BLOCK = """
# Include Customizations
ifneq ($(wildcard $(TOP)/vendor/extras/extras.mk),)
    include $(TOP)/vendor/extras/extras.mk
endif
"""


def patch_device_mk(tree: Path, device: str) -> str:
    path = tree / "vendor" / "google_devices" / device / f"{device}.mk"
    if not path.is_file():
        raise SystemExit(f"error: device mk not found: {path}")

    text = path.read_text()
    if "vendor/extras/extras.mk" in text:
        return f"device.mk: already patched ({path})"

    anchor = re.compile(
        rf"^\s*\$\(call\s+inherit-product\s*,\s*vendor/adevtool/[^)]*{re.escape(device)}\.mk\s*\)\s*$",
        re.MULTILINE,
    )
    match = anchor.search(text)
    if not match:
        raise SystemExit(
            f"error: anchor line not found in {path}\n"
            f"  expected something like: $(call inherit-product, vendor/adevtool/config/mk/google_devices/device/{device}/{device}.mk)"
        )

    insert_at = match.end()
    new_text = text[:insert_at] + "\n" + INCLUDE_BLOCK.rstrip() + "\n" + text[insert_at:]
    path.write_text(new_text)
    return f"device.mk: patched ({path})"


def patch_rro_bp(tree: Path, device: str) -> str:
    rro_dir = (
        tree
        / "vendor"
        / "google_devices"
        / device
        / "overlays"
        / f"framework-res__{device}__auto_generated_rro_product"
    )
    path = rro_dir / "Android.bp"
    if not path.is_file():
        raise SystemExit(
            f"error: RRO bp not found: {path}\n"
            f"  expected after adevtool has unpacked vendor files for '{device}';\n"
            f"  has the AOSP tree finished syncing?"
        )

    text = path.read_text()
    old_name = f"framework-res__{device}__auto_generated_rro_product"
    new_name = old_name + "_"

    if re.search(rf'name:\s*"{re.escape(new_name)}"', text):
        return f"RRO bp: already renamed ({path})"

    pattern = re.compile(rf'(name:\s*")({re.escape(old_name)})(")')
    new_text, count = pattern.subn(rf"\1{new_name}\3", text)
    if count == 0:
        raise SystemExit(f"error: could not find module name {old_name!r} in {path}")

    path.write_text(new_text)
    return f"RRO bp: renamed module {old_name!r} -> {new_name!r}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tree", required=True, type=Path, help="AOSP root path")
    ap.add_argument("--device", required=True, help="device codename (e.g., akita, tokay, comet)")
    args = ap.parse_args()

    if not args.tree.is_dir():
        raise SystemExit(f"error: --tree {args.tree} is not a directory")

    print(patch_device_mk(args.tree, args.device))
    print(patch_rro_bp(args.tree, args.device))
    return 0


if __name__ == "__main__":
    sys.exit(main())
