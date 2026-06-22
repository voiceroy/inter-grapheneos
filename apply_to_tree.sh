#!/usr/bin/env bash
# Patch a fresh GrapheneOS/AOSP tree with feature-frozen Inter fonts.
#
# Designed to run on a clean cloud build server after:
#   git clone <this-repo> && cd Inter
#
# Usage:
#   ./apply_to_tree.sh <AOSP_ROOT>
#   ./apply_to_tree.sh --device <name> <AOSP_ROOT>
#   ./apply_to_tree.sh --force --device <name> <AOSP_ROOT>
#   ./apply_to_tree.sh --disable-seedvault --device <name> <AOSP_ROOT>
#   ./apply_to_tree.sh --updater-url https://releases.graphene.voiceroy.dev/ --device <name> <AOSP_ROOT>
#   AOSP_TREE=/path/to/aosp DEVICE=akita ./apply_to_tree.sh
#
# --disable-seedvault (or DISABLE_SEEDVAULT=1) comments out
#   `PRODUCT_PACKAGES += Seedvault` in build/make/.../media_system.mk,
#   removing Seedvault from the build. Off by default.
#
# --updater-url <URL> (or UPDATER_URL=<URL>) points the Updater app at a custom
#   OTA server: rewrites the url string + pinned <domain> in packages/apps/Updater
#   (pin-set left untouched). Off by default.
#
# --device <name> additionally patches per-device files:
#   - injects `include vendor/extras/extras.mk` into vendor/google_devices/<name>/<name>.mk
#   - appends a trailing underscore to the RRO module name in
#     vendor/google_devices/<name>/overlays/framework-res__<name>__auto_generated_rro_product/Android.bp
# Both edits are idempotent.

set -euo pipefail

force=0
tree="${AOSP_TREE:-}"
device="${DEVICE:-}"
disable_seedvault="${DISABLE_SEEDVAULT:-0}"
updater_url="${UPDATER_URL:-}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --force) force=1; shift ;;
        --disable-seedvault) disable_seedvault=1; shift ;;
        --updater-url) updater_url="$2"; shift 2 ;;
        --updater-url=*) updater_url="${1#*=}"; shift ;;
        --device) device="$2"; shift 2 ;;
        --device=*) device="${1#*=}"; shift ;;
        -h|--help)
            sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        --) shift; tree="${1:-$tree}"; shift || true ;;
        -*) echo "unknown flag: $1" >&2; exit 2 ;;
        *) tree="$1"; shift ;;
    esac
done

if [[ -z "$tree" ]]; then
    echo "usage: $0 [--force] <AOSP_ROOT>" >&2
    exit 2
fi
if [[ ! -d "$tree" ]]; then
    echo "error: '$tree' is not a directory" >&2
    exit 2
fi

here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$here"

if ! command -v uv >/dev/null 2>&1; then
    echo "==> uv not found; installing via official installer"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    command -v uv >/dev/null 2>&1 || { echo "error: uv install failed" >&2; exit 1; }
fi

echo "==> building vendor/extras tarball"
build_args=()
[[ "$force" -eq 1 ]] && build_args+=(--force)
python3 ./build_inter_vendor.py "${build_args[@]}"

tarball="$(ls -1t vendor_extras_inter-*.tar.gz 2>/dev/null | head -n1 || true)"
if [[ -z "$tarball" ]]; then
    echo "error: no vendor_extras_inter-*.tar.gz produced" >&2
    exit 1
fi

aosp_abs="$(cd "$tree" && pwd)"
echo "==> extracting $tarball into $aosp_abs"
tar -xzf "$tarball" -C "$aosp_abs"

if [[ -f "$aosp_abs/vendor/extras/extras.mk" ]]; then
    echo "✓ vendor/extras patched at $aosp_abs"
else
    echo "error: vendor/extras/extras.mk missing after extract" >&2
    exit 1
fi

if [[ "$disable_seedvault" -eq 1 ]]; then
    echo "==> disabling Seedvault"
    python3 ./patch_seedvault.py --tree "$aosp_abs"
else
    echo "note: --disable-seedvault not set; leaving Seedvault in the build"
fi

if [[ -n "$updater_url" ]]; then
    echo "==> pointing Updater at $updater_url"
    python3 ./patch_updater.py --tree "$aosp_abs" --url "$updater_url"
else
    echo "note: --updater-url not set; leaving Updater pointed at the default server"
fi

if [[ -n "$device" ]]; then
    echo "==> patching device tree for '$device'"
    python3 ./patch_device_tree.py --tree "$aosp_abs" --device "$device"
else
    echo "note: --device not set; skipping device.mk include and RRO rename"
    echo "      (rerun with --device <name> after the AOSP tree finishes syncing)"
fi
