#!/usr/bin/env bash
# Apply the hide-navigation-handle patchset to a GrapheneOS/AOSP tree.
#
# Usage:
#   ./apply.sh <AOSP_ROOT>
#   ./apply.sh --check <AOSP_ROOT>
#   ./apply.sh --reverse <AOSP_ROOT>
#   AOSP_TREE=/path/to/grapheneos ./apply.sh
#
# Each patch is git-applied inside its project (repo-of-repos). Re-running
# on an already-patched tree fails unless --reverse is used.

set -euo pipefail

mode=apply
tree="${AOSP_TREE:-}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --check) mode=check; shift ;;
        --reverse) mode=reverse; shift ;;
        -h|--help)
            sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        --) shift; tree="${1:-$tree}"; shift || true ;;
        -*) echo "unknown flag: $1" >&2; exit 2 ;;
        *) tree="$1"; shift ;;
    esac
done

if [[ -z "$tree" ]]; then
    echo "usage: $0 [--check|--reverse] <AOSP_ROOT>" >&2
    exit 2
fi
if [[ ! -d "$tree" ]]; then
    echo "error: '$tree' is not a directory" >&2
    exit 2
fi

here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
tree="$(cd -- "$tree" && pwd)"
series="$here/series"

if [[ ! -f "$series" ]]; then
    echo "error: missing $series" >&2
    exit 1
fi

apply_flags=(--whitespace=nowarn)
case "$mode" in
    check) apply_flags+=(--check) ;;
    reverse) apply_flags+=(-R) ;;
esac

failures=0
while read -r project patch; do
    [[ -z "${project:-}" || "$project" == \#* ]] && continue
    patch_path="$here/$patch"
    project_path="$tree/$project"
    if [[ ! -f "$patch_path" ]]; then
        echo "error: missing patch $patch_path" >&2
        failures=1
        continue
    fi
    if [[ ! -d "$project_path" ]]; then
        echo "error: missing project $project_path" >&2
        failures=1
        continue
    fi
    echo "==> $mode $patch in $project"
    if [[ "$mode" == apply ]] && git -C "$project_path" apply --check -R --whitespace=nowarn "$patch_path" >/dev/null 2>&1; then
        echo "    already applied, skip"
        continue
    fi
    if git -C "$project_path" apply "${apply_flags[@]}" "$patch_path"; then
        echo "    ok"
    elif [[ "$mode" == apply ]]; then
        diff_only="$(mktemp)"
        sed -n '/^diff --git/,$p' "$patch_path" >"$diff_only"
        if patch -d "$project_path" -p1 --forward --fuzz=3 --batch <"$diff_only" >/dev/null; then
            echo "    ok (fuzz)"
            rm -f "$diff_only"
        else
            rm -f "$diff_only"
            echo "    FAILED" >&2
            failures=1
        fi
    else
        echo "    FAILED" >&2
        failures=1
    fi
done < <(grep -vE '^\s*(#|$)' "$series")

if [[ "$failures" -ne 0 ]]; then
    echo "error: one or more patches failed ($mode)" >&2
    exit 1
fi

echo "✓ hide-nav-hint $mode complete"
