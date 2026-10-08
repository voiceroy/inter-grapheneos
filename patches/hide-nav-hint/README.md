# Hide navigation handle

Git-apply patchset for the open GrapheneOS hide-nav-hint feature: hide the
gesture navigation hint pill without reclaiming reserved space.

Captured 2026-09-15 from:

| Project | PR | Head |
|---|---|---|
| `frameworks/base` | [platform_frameworks_base#440](https://github.com/GrapheneOS/platform_frameworks_base/pull/440) | `ffdacc31fdc860fc2aa6138c4e5f7972d77b606e` |
| `packages/apps/Settings` | [platform_packages_apps_Settings#448](https://github.com/GrapheneOS/platform_packages_apps_Settings/pull/448) | `265ba8bb7f36338f2f914dd9acc9b3deff5d658d` |
| `packages/apps/Launcher3` | [platform_packages_apps_Launcher3#83](https://github.com/GrapheneOS/platform_packages_apps_Launcher3/pull/83) | `225fc12747a0d17e6b31db7d959ac1fdfd44ef92` |

`#440` is the setting key. Settings and Launcher3 are required for a working
toggle; the three numbered patches are the squashed net diffs. `upstream/`
keeps the original GitHub `git format-patch` series (pre-squash commits).

Rebased onto GrapheneOS release `2026100600` (2026-10-08). On that tag
`ExtSettings` has the secure-paste clipboard settings, so `0001` adds
`HIDE_NAVIGATION_HANDLE` after `ALLOW_CLIPBOARD_READ_BY_DEFAULT`, and `0002`
appends its strings after the clipboard strings in `strings_ext.xml`. All
three patches `git apply` cleanly on `2026100600`, so no fuzz is needed.

Settings#448 was `mergeable_state: dirty` against GrapheneOS `17` at capture.
`--check` before applying on a tree that has moved. `apply.sh` skips a
patch that is already applied.

## Apply

From this directory:

```bash
./apply.sh --check /path/to/grapheneos
./apply.sh /path/to/grapheneos
./apply.sh --reverse /path/to/grapheneos
```

Or via the overlay driver:

```bash
./apply_to_tree.sh --hide-nav-hint --device tokay /path/to/grapheneos
```

Each patch is applied with `git apply` inside its project directory. Not
idempotent.

## Series

```
frameworks/base          0001-frameworks-base-add-HIDE_NAVIGATION_HANDLE.patch
packages/apps/Settings   0002-Settings-add-hide-navigation-hint-toggle.patch
packages/apps/Launcher3  0003-Launcher3-honor-HIDE_NAVIGATION_HANDLE.patch
```
