# Note: Always --disable-seedvault first

# Google Sans Flex for GrapheneOS

Builds a `vendor/extras/` overlay that installs Google Sans Flex as GrapheneOS's default `sans-serif`, and patches the device tree to wire it in.

Default target device: **tokay** (Pixel 9).

## What it does

1. Downloads `GoogleSansFlex-Regular.ttf` from Android's official source.
2. Maps the framework's clock, body, light, regular, and headline families to Google Sans Flex.
3. Maps the system `sans-serif` and Material variable typography families to the downloaded font.
4. Packages the font and hand-tuned XML templates as `vendor_extras_google_sans_flex.tar.gz`.
5. Extracts that into the AOSP tree and patches the device `.mk` + auto-generated RRO module name.

## Run it (fresh build server)

```bash
git clone https://github.com/voiceroy/inter-grapheneos GoogleSansFlex
cd GoogleSansFlex
./apply_to_tree.sh --device tokay /path/to/grapheneos-source
```

`apply_to_tree.sh` will:

- Run `build_google_sans_flex_vendor.py` to download the font and package the overlay.
- Extract the tarball into the AOSP root.
- Run `patch_device_tree.py` against the named device.

The device patch needs adevtool to have already unpacked vendor files for the device — i.e. run **after** the AOSP tree finishes syncing.

## Individual steps

Build the tarball only:

```bash
./build_google_sans_flex_vendor.py          # build the overlay tarball
./build_google_sans_flex_vendor.py --check  # validate templates + download, no build
```

Patch a device tree against an already-extracted tarball:

```bash
./patch_device_tree.py --tree /path/to/grapheneos-source --device tokay
```

Both device-tree edits are idempotent — safe to rerun.

Point the Updater at a custom OTA server (standalone):

```bash
./patch_updater.py --tree /path/to/grapheneos-source --url https://releases.graphene.voiceroy.dev/
```

## Layout

```
apply_to_tree.sh         # end-to-end driver (build + extract + patch)
build_google_sans_flex_vendor.py # download the font and package the overlay
patch_device_tree.py     # device.mk include + RRO module rename
patch_seedvault.py       # comment out PRODUCT_PACKAGES += Seedvault (tree-wide)
patch_updater.py         # point Updater app at a custom OTA server (url + pinned domain)
frozen_fonts/            # hand-tuned XML + Android.bp templates (do not regen)
  ├── Android.bp
  ├── config.xml
  ├── extras.mk
  └── fonts_customization.xml
```

## Notes

- `frozen_fonts/fonts_customization.xml` and `config.xml` are hand-tuned. Don't regenerate them.
- The builder downloads `GoogleSansFlex-Regular.ttf` from Android's official source and installs it into the product fonts.
- The device-mk patch anchors on the adevtool `inherit-product` line; modern adevtool emits `.../google_devices/<device>/device.mk`. If the anchor isn't found, the AOSP tree probably hasn't synced yet.
- The RRO rename works around a module-name collision between the auto-generated overlay and ours by appending a trailing `_`.
- `patch_seedvault.py` comments out the single `PRODUCT_PACKAGES += Seedvault` line in `build/make/target/product/media_system.mk`, removing Seedvault from every product image. It is **opt-in**: pass `--disable-seedvault` to `apply_to_tree.sh` (or set `DISABLE_SEEDVAULT=1`); off by default. Device-independent and idempotent. This leaves the build with no backup transport — that's intended. Run standalone with `./patch_seedvault.py --tree /path/to/grapheneos-source`.
- `patch_updater.py` rewrites the update server in `packages/apps/Updater`: the `url` string in `res/values/config.xml` and the pinned `<domain>` in `res/xml/network_security_config.xml`. The certificate `<pin-set>` is **left untouched** — a Let's Encrypt cert (e.g. via Fly.io) still chains to the pinned ISRG roots, so pinning keeps working; edit the pin-set yourself if you ever leave a Let's Encrypt issuer. It is **opt-in**: pass `--updater-url <URL>` to `apply_to_tree.sh` (or set `UPDATER_URL=<URL>`); off by default. Device-independent and idempotent.
