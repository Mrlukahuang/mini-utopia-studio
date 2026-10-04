# Mini Utopia offline asset pipeline

This tool converts approved third-party CC0 source packs into a portable
Mini Utopia reusable GLB pack.

It is intentionally **not** part of the Streamlit runtime dependency set.
Large mesh/texture conversion happens offline; the main app only validates and
imports the resulting normalized ZIP.

## Install

```bash
python -m venv .venv-assets
source .venv-assets/bin/activate
pip install -r tools/asset_pipeline/requirements.txt
```

## Build Core Asset Pack v1

```bash
python tools/asset_pipeline/build_core_asset_pack.py \
  --source kaykit_forest=/path/KayKit_Forest_Nature_Pack_1.0_FREE.zip \
  --source kenney_town=/path/kenney_fantasy-town-kit_2.0.zip \
  --source quaternius_nature="/path/Stylized Nature MegaKit[Standard].zip" \
  --source quaternius_props="/path/Fantasy Props MegaKit[Standard].zip" \
  --output /tmp/Mini_Utopia_Core_Asset_Pack_v1.zip
```

The builder:

- verifies the expected license file exists in each source ZIP
- uses the curated catalog in `assets/catalogs/core_cc0_seed_v1.json`
- downsizes selected Quaternius/KayKit source textures to a web-friendly ceiling
- converts glTF/GLB to self-contained GLB
- centers X/Z and aligns the model base to Y=0
- records bounds, triangle/vertex counts, source/license, SHA-256 and byte size
- writes a portable `manifest.json + glb/ + licenses/` ZIP

The app-side `ReusableAssetPackService` validates this portable pack and
imports each GLB into content-addressed ObjectStorage.
