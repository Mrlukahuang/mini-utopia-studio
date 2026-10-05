# Local Golden Style Anchors

This folder is for **local derived copies** of the curated Style Anchor assets.

The actual model/texture files and `installed_manifest.json` are intentionally ignored by git. The source ZIPs remain outside the repository and are never modified.

Install the first lineup from the repository root:

```bash
python3 tools/install_golden_anchors.py
```

The installer searches the repository plus common macOS folders such as `~/Downloads`, `~/Desktop` and `~/Documents`.

If your ZIPs live somewhere else:

```bash
python3 tools/install_golden_anchors.py --source-dir "/path/to/zips"
```

To rebuild the local lineup from scratch:

```bash
python3 tools/install_golden_anchors.py --clean
```

After installation, return to Godot and let it finish importing the GLTF/GLB files.
