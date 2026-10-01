from studio.repositories.sqlite import SQLiteStudioRepository
from studio.services.universe_service import UniverseService


def test_bootstrap_mini_utopia_is_idempotent(tmp_path):
    repo = SQLiteStudioRepository(tmp_path / "studio.db")
    service = UniverseService(repo)
    one = service.ensure_mini_utopia()
    two = service.ensure_mini_utopia()
    assert one.universe_id == two.universe_id
    assert one.story_formula[-1] == "Portal"
