from __future__ import annotations

import json
from pathlib import Path


def test_core_cc0_seed_catalog_is_stable_and_cc0():
    root = Path(__file__).resolve().parents[1]
    catalog = json.loads(
        (root / "assets" / "catalogs" / "core_cc0_seed_v1.json").read_text(
            encoding="utf-8"
        )
    )

    assert catalog["schema_version"] == "1.0"
    assert len(catalog["assets"]) == 69
    assert set(catalog["packs"]) == {
        "kaykit_forest",
        "kenney_town",
        "quaternius_nature",
        "quaternius_props",
    }
    assert all(
        pack["license_id"] == "CC0-1.0"
        for pack in catalog["packs"].values()
    )

    selected = {(item["pack"], item["file"]) for item in catalog["assets"]}
    assert len(selected) == len(catalog["assets"])
    assert ("kenney_town", "wall.glb") in selected
    assert ("kaykit_forest", "Tree_1_A_Color1.gltf") in selected
    assert ("quaternius_nature", "TwistedTree_2.gltf") in selected
    assert ("quaternius_props", "Potion_1.gltf") in selected
