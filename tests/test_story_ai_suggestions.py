from pathlib import Path

import pytest

from studio.models.story_suggestion import StoryBeatSuggestions
from studio.providers.base import StructuredTextProvider
from studio.services.story_suggestion_service import StorySuggestionService


ROOT = Path(__file__).resolve().parents[1]


class FakeStoryProvider(StructuredTextProvider):
    def __init__(self):
        self.calls = []

    def generate_structured(self, *, system: str, user: str, schema):
        self.calls.append(
            {
                "system": system,
                "user": user,
                "schema": schema,
            }
        )
        return StoryBeatSuggestions(
            arrive="Nancy arrives at the village gate with Nova.",
            discover="They discover a glowing clue beside the Portal path.",
            problem="A playful Skeleton blocks the safe route forward.",
            adventure="Nancy explores the square and solves the clue before a light battle.",
            surprise="The Skeleton was protecting the clue from a gusty magic wind.",
            portal="The Portal lights up and reveals the next friendly world.",
        )


def test_story_suggestions_are_optional_and_manual_builder_can_exist_without_provider():
    service = StorySuggestionService()
    assert service.available is False

    with pytest.raises(RuntimeError, match="not configured"):
        service.suggest(
            title="",
            premise="A small adventure",
            story_mode="canon",
            character_names=["Nancy"],
            world_name="Newbie Village",
            world_context={},
            prop_names=[],
        )


def test_story_suggestion_provider_returns_six_structured_editable_beats():
    provider = FakeStoryProvider()
    service = StorySuggestionService(provider)

    result = service.suggest(
        title="The Glowing Portal",
        premise="Nancy and Nova discover why the Portal is flickering.",
        story_mode="canon",
        character_names=["Nancy", "Nova"],
        world_name="Newbie Village",
        world_context={
            "mood": ["warm", "curious"],
            "landmarks": ["Village Square", "Portal"],
        },
        prop_names=["Tiny Key"],
    )

    assert service.available is True
    assert result.arrive.startswith("Nancy arrives")
    assert result.portal.startswith("The Portal")
    assert provider.calls
    call = provider.calls[0]
    assert call["schema"] is StoryBeatSuggestions
    assert "ARRIVE → DISCOVER → PROBLEM" in call["system"]
    assert "Newbie Village" in call["user"]
    assert "Nancy" in call["user"]
    assert "Tiny Key" in call["user"]


def test_story_builder_keeps_human_approval_gate_and_editable_fields():
    builder = (
        ROOT / "studio" / "ui" / "creator" / "story_builder.py"
    ).read_text(encoding="utf-8")
    bootstrap = (
        ROOT / "studio" / "services" / "bootstrap.py"
    ).read_text(encoding="utf-8")

    assert "Suggest Story Beats / AI 提案" in builder
    assert "story_ai_suggestion_pending" in builder
    assert "只有点击 Save 才会保存" in builder
    assert 'key="story_hook"' in builder
    assert 'key="story_discovery"' in builder
    assert 'key="story_conflict"' in builder
    assert 'key="story_adventure"' in builder
    assert 'key="story_twist"' in builder
    assert 'key="story_ending"' in builder
    assert "ctx.stories.create_story(" in builder
    assert "StorySuggestionService" in bootstrap
    assert "structured_provider=text_provider" in bootstrap
