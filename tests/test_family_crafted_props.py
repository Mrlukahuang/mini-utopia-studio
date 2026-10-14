import hashlib
import json

from studio.family_api import FamilyApplication
from studio.repositories.sqlite import SQLiteStudioRepository


def make_app(path):
    return FamilyApplication(
        SQLiteStudioRepository(path),
        token_hashes={
            "child_a": hashlib.sha256(b"test-owner-a").hexdigest(),
            "child_b": hashlib.sha256(b"test-owner-b").hexdigest(),
        },
        allowed_origins=("https://family.example",),
    )


def request(app, method, path, *, child="child_a", payload=None):
    token = "test-owner-a" if child == "child_a" else "test-owner-b"
    return app.handle(
        method=method, path=path,
        authorization="Bearer " + token,
        origin="https://family.example",
        body=json.dumps(payload).encode() if payload is not None else b"",
    )


def recipe(**changes):
    return dict({
        "schema_version": "1.0",
        "display_name": "My Star Wand",
        "shape": "star",
        "slot": "weapon_main",
        "color_hex": "#B9E7D0",
        "accent_color_hex": "#F2C75C",
    }, **changes)


def test_saved_crafted_prop_same_runtime_after_restart_and_sibling_isolation(tmp_path):
    db = tmp_path / "private-family.db"
    app = make_app(db)
    a = request(app, "POST", "/characters", payload={"display_name": "Sheep"})
    b = request(app, "POST", "/characters", child="child_b",
                payload={"display_name": "Cat"})
    aid, bid = a.payload["character_id"], b.payload["character_id"]
    uri = f"/characters/{aid}/crafted-props"

    assert request(app, "POST", uri, child="child_b", payload=recipe()).status == 404
    assert request(app, "GET", uri).status == 405
    made = request(app, "POST", uri, payload=recipe())
    assert made.status == 201
    item = made.payload["crafted"]["item_instance_id"]
    asset = made.payload["crafted"]["prop_asset_id"]
    assert item.startswith("ITEM_") and asset.startswith("EQ_")
    assert made.payload["crafted"]["visual_recipe"]["shape"] == "star"

    wardrobe = made.payload["equipment"]
    record = next(x for x in wardrobe["items"] if x["item_instance_id"] == item)
    assert record["visual_recipe"]["color_hex"] == "#B9E7D0"
    assert record["slot"] == "weapon_main"
    assert request(app, "PUT", f"/characters/{bid}/equipment/weapon_main",
                   child="child_b", payload={"item_instance_id": item}).status == 400

    equipped = request(app, "PUT", f"/characters/{aid}/equipment/weapon_main",
                       payload={"item_instance_id": item})
    assert equipped.status == 200
    spec = equipped.payload["runtime"]["equipped"]["weapon_main"]
    assert spec["item_instance_id"] == item
    assert spec["visual_recipe"]["shape"] == "star"
    assert spec["rolled_stats"] == {"hp": 0, "atk": 0, "defense": 0}

    reopened = make_app(db)
    stored = request(reopened, "GET", f"/characters/{aid}/equipment")
    again = stored.payload["runtime"]["equipped"]["weapon_main"]
    assert again["item_instance_id"] == item
    assert again["visual_recipe"]["color_hex"] == "#B9E7D0"
    assert request(reopened, "GET", f"/characters/{aid}/equipment",
                   child="child_b").status == 404
    other = request(reopened, "GET", f"/characters/{bid}/equipment",
                    child="child_b")
    assert item not in [x["item_instance_id"] for x in other.payload["items"]]
    assert reopened.repository.get_asset(asset).metadata["family_owner"] == "child_a"


def test_craft_accepts_safe_shapes_and_rejects_untrusted_fields(tmp_path):
    app = make_app(tmp_path / "strict.db")
    a = request(app, "POST", "/characters", payload={"display_name": "Sheep"})
    uri = f"/characters/{a.payload['character_id']}/crafted-props"
    for bad in [
        recipe(shape="unknown"), recipe(slot="wings"),
        recipe(color_hex="#NOTHEX"), recipe(display_name=""),
        recipe(display_name="a" * 33),
        recipe(extra_field=True), recipe(schema_version="2.0"),
        recipe(rolled_stats={"atk": 999}),
    ]:
        assert request(app, "POST", uri, payload=bad).status == 400
    for shape, slot in [
        ("heart", "headwear"), ("box", "backpack"),
        ("sphere", "accessory"),
    ]:
        assert request(app, "POST", uri, payload=recipe(
            shape=shape, slot=slot,
        )).status == 201
