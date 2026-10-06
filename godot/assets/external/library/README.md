# Local 3D Asset Vault

This folder is the one-time imported asset library for Mini Utopia.

Install/update it with:

```bash
python3 tools/install_full_asset_vault.py
```

The installer scans common local folders for KayKit / Kenney / Quaternius / MegaKit ZIPs that actually contain `.gltf` or `.glb` assets.

It:

- never modifies the source ZIPs
- extracts every supported 3D asset plus direct glTF buffers/textures
- preserves each pack in its own subfolder
- writes `asset_vault_manifest.json`
- reuses unchanged packs on later runs
- lets Godot import the library once, then future scenes can reuse it without repeatedly extracting small subsets

All extracted third-party files are gitignored.

Godot runtime helper:

`res://scripts/asset_vault_runtime.gd`
