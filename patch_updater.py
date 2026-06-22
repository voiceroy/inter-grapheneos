#!/usr/bin/env python3
"""Point the GrapheneOS Updater app at a custom OTA release server.

The Updater hardcodes its update server in two resource files:

    packages/apps/Updater/res/values/config.xml          <string name="url">...</string>
    packages/apps/Updater/res/xml/network_security_config.xml   <domain>...</domain>

This rewrites the `url` string and the pinned `<domain>` to your server. The
certificate `<pin-set>` is left untouched: a Let's Encrypt-issued cert (e.g. via
Fly.io) still chains to the pinned ISRG roots, so pinning keeps working. If you
ever move off a Let's Encrypt issuer, edit the pin-set separately.

Both edits are idempotent and device-independent.

Usage:
  ./patch_updater.py --tree <AOSP_ROOT> --url https://releases.graphene.voiceroy.dev/
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_UPDATER_PATH = Path("packages/apps/Updater")
CONFIG_REL = Path("res/values/config.xml")
NSC_REL = Path("res/xml/network_security_config.xml")

# <string name="url" ...>VALUE</string>
URL_RE = re.compile(r'(<string name="url"[^>]*>)([^<]*)(</string>)')
# <domain ...>VALUE</domain>  (the Updater config has exactly one)
DOMAIN_RE = re.compile(r'(<domain\b[^>]*>)([^<]*)(</domain>)')


def _read(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(
            f"error: file not found: {path}\n"
            f"  Is --updater-path correct, and has the tree finished syncing?\n"
            f"  grep -rn 'releases.grapheneos.org' packages/apps/Updater"
        )
    return path.read_text()


def patch_config(updater: Path, url: str) -> str:
    path = updater / CONFIG_REL
    text = _read(path)

    m = URL_RE.search(text)
    if not m:
        raise SystemExit(f"error: <string name=\"url\"> not found in {path}")
    if m.group(2) == url:
        return f"config.xml: url already {url} ({path})"

    new_text = URL_RE.sub(lambda mm: mm.group(1) + url + mm.group(3), text, count=1)
    path.write_text(new_text)
    return f"config.xml: url {m.group(2)} -> {url} ({path})"


def patch_nsc(updater: Path, domain: str) -> str:
    path = updater / NSC_REL
    text = _read(path)

    m = DOMAIN_RE.search(text)
    if not m:
        raise SystemExit(f"error: <domain> not found in {path}")
    if m.group(2) == domain:
        return f"network_security_config.xml: domain already {domain} ({path})"

    new_text = DOMAIN_RE.sub(
        lambda mm: mm.group(1) + domain + mm.group(3), text, count=1
    )
    path.write_text(new_text)
    return (
        f"network_security_config.xml: domain {m.group(2)} -> {domain} "
        f"(pin-set left untouched) ({path})"
    )


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--tree", required=True, type=Path, help="AOSP root path")
    ap.add_argument(
        "--url",
        required=True,
        help="update server base URL, e.g. https://releases.graphene.voiceroy.dev/",
    )
    ap.add_argument(
        "--updater-path",
        type=Path,
        default=DEFAULT_UPDATER_PATH,
        help=f"Updater app path relative to --tree (default: {DEFAULT_UPDATER_PATH})",
    )
    args = ap.parse_args()

    if not args.tree.is_dir():
        raise SystemExit(f"error: --tree {args.tree} is not a directory")

    # Normalise: the Updater concatenates url + "<device>-<channel>", so it must
    # end with a slash.
    url = args.url if args.url.endswith("/") else args.url + "/"

    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise SystemExit(f"error: --url must be an https:// URL with a host: {args.url}")
    domain = parsed.hostname

    updater = args.tree / args.updater_path
    if not updater.is_dir():
        raise SystemExit(
            f"error: Updater app not found at {updater}\n"
            f"  pass --updater-path if it lives elsewhere in the tree"
        )

    print(patch_config(updater, url))
    print(patch_nsc(updater, domain))
    return 0


if __name__ == "__main__":
    sys.exit(main())
