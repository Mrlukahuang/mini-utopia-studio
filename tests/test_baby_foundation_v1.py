from pathlib import Path

from studio.models.baby import BabyGrowthStage
from studio.repositories.sqlite import SQLiteStudioRepository
from studio.repositories.supabase import SupabaseStudioRepository
from studio.services.baby_service import BABY_ARCHETYPES, BabyService


ROOT = Path(__file__).resolve().parents[1]


def test_initial_baby_identity_growth_and_sqlite_persistence(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    service = BabyService(repo)

    roster = service.create_initial_baby(
        display_name="Nova",
        species_id="star_baby",
    )
    baby = roster.active_baby()
    assert baby is not None
    baby_id = baby.baby_id
    seed = baby.appearance_seed

    service.add_xp(baby_id=baby_id, amount=125)
    service.add_bond(baby_id=baby_id, amount=15)
    service.rename(baby_id=baby_id, display_name="Nova Star")

    reloaded = BabyService(
        SQLiteStudioRepository(tmp_path / "studio.db")
    ).get_roster()
    restored = reloaded.active_baby()

    assert restored is not None
    assert restored.baby_id == baby_id
    assert restored.appearance_seed == seed
    assert restored.display_name == "Nova Star"
    assert restored.growth_stage == BabyGrowthStage.BABY
    assert restored.level == 2
    assert restored.xp == 125
    assert restored.bond == 15
    assert restored.active is True
    assert reloaded.active_baby_id == baby_id


def test_baby_is_independent_from_equipment_collection(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    service = BabyService(repo)
    roster = service.create_initial_baby(
        display_name="Cloudy",
        species_id="cloud_baby",
    )

    assert roster.roster_id == "BABIES_DEFAULT"
    assert repo.get_collection("COLL_DEFAULT") is None
    assert repo.get_baby_roster("BABIES_DEFAULT") is not None


def test_runtime_spec_reserves_godot_follow_hook(tmp_path):
    service = BabyService(SQLiteStudioRepository(tmp_path / "studio.db"))
    service.create_initial_baby(
        display_name="Sprout",
        species_id="forest_baby",
    )

    spec = service.runtime_spec()

    assert spec is not None
    assert spec.display_name == "Sprout"
    assert spec.species_id == "forest_baby"
    assert spec.follow_enabled is True
    assert spec.active is True


def test_supabase_baby_roster_uses_its_own_record_kind(monkeypatch):
    repo = SupabaseStudioRepository(
        url="https://example.supabase.co",
        service_role_key="test-key",
    )
    service = BabyService(repo)
    stored = {}

    def fake_get_one(*, kind, record_id):
        assert kind == "baby_roster"
        assert record_id == "BABIES_DEFAULT"
        return stored.get(record_id)

    def fake_upsert(*, record_id, kind, name, data, updated_at):
        assert kind == "baby_roster"
        stored[record_id] = data

    monkeypatch.setattr(repo, "_get_one", fake_get_one)
    monkeypatch.setattr(repo, "_upsert", fake_upsert)

    created = service.create_initial_baby(
        display_name="Bolt",
        species_id="robot_baby",
    )
    restored = service.get_roster()

    assert restored.active_baby_id == created.active_baby_id
    assert restored.active_baby().display_name == "Bolt"


def test_creator_ui_exposes_my_baby_and_context():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    my_baby = (
        ROOT / "studio" / "ui" / "creator" / "my_baby.py"
    ).read_text(encoding="utf-8")
    my_stuff = (
        ROOT / "studio" / "ui" / "creator" / "my_stuff.py"
    ).read_text(encoding="utf-8")

    assert "🐣 My Baby" in app
    assert "render_my_baby(ctx)" in app
    assert "Meet My Baby / 领取宝宝" in my_baby
    assert "Rename Baby / 改名字" in my_baby
    assert "How Baby Grows / 怎么长大" in my_baby
    assert "Quest Growth" in my_baby
    assert "+25 XP" not in my_baby
    assert "+5 Bond" not in my_baby
    assert "Active Baby" in my_stuff
    assert "Baby Growth / 宝宝成长" in my_stuff


def test_baby_v1_archetypes_are_child_visible():
    assert set(BABY_ARCHETYPES) == {
        "cloud_baby",
        "sheep_baby",
        "star_baby",
        "robot_baby",
        "forest_baby",
    }


def test_creator_baby_ui_uses_repository_boundary_for_hot_reload_safety():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    my_baby = (
        ROOT / "studio" / "ui" / "creator" / "my_baby.py"
    ).read_text(encoding="utf-8")
    my_stuff = (
        ROOT / "studio" / "ui" / "creator" / "my_stuff.py"
    ).read_text(encoding="utf-8")

    assert "baby_service = BabyService(ctx.repository)" in app
    assert "BabyService(ctx.repository)" in my_baby
    assert "BabyService(ctx.repository)" in my_stuff
    assert "ctx.babies" not in app
    assert "ctx.babies" not in my_baby
    assert "ctx.babies" not in my_stuff
