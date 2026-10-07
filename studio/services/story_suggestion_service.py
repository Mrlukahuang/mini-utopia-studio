from __future__ import annotations

import json

from studio.models.story_suggestion import StoryBeatSuggestions
from studio.providers.base import StructuredTextProvider


class StorySuggestionService:
    """Provider-neutral, human-approved Story beat suggestions."""

    def __init__(self, structured_provider: StructuredTextProvider | None = None):
        self.structured_provider = structured_provider

    @property
    def available(self) -> bool:
        return self.structured_provider is not None

    def suggest(
        self,
        *,
        title: str,
        premise: str,
        story_mode: str,
        character_names: list[str],
        world_name: str,
        world_context: dict,
        prop_names: list[str],
        continuity_context: dict | None = None,
    ) -> StoryBeatSuggestions:
        if self.structured_provider is None:
            raise RuntimeError("AI Story suggestions are not configured.")
        if not premise.strip():
            raise ValueError("Story premise is required for suggestions.")
        if not character_names:
            raise ValueError("Choose at least one Character first.")
        if not world_name.strip():
            raise ValueError("Choose a World first.")

        system = """You are the Mini Utopia Story Companion.

Suggest exactly six concise, editable Story beats for a child-friendly creative
adventure. The creator remains the author: you provide options, never final canon.

Follow this rhythm:
ARRIVE → DISCOVER → PROBLEM → ADVENTURE → SURPRISE → PORTAL.

Rules:
- Respect the supplied premise, selected Characters, World, Props and mode.
- Use approved World landmarks/context when useful; do not invent a competing World.
- Keep every beat concrete enough to later become gameplay or a filmed scene.
- Make PROBLEM age-appropriate and solvable; no graphic harm or frightening detail.
- ADVENTURE should involve exploration, cooperation, puzzle-solving or light game action.
- SURPRISE should reframe the situation without invalidating earlier beats.
- PORTAL should resolve or point naturally toward a next World/story.
- Canon mode should respect supplied continuity: current equipment, Baby, World state and prior Canon events.
- Never rewrite or contradict prior Canon events merely to make the new Story more dramatic.
- Playground may be sillier or stranger and should not inherit Canon continuity unless explicitly supplied.
- Each beat should be 1-3 short sentences, not a screenplay.
- Do not mention AI, prompts, models, JSON or production tooling."""

        context = {
            "title": title.strip(),
            "premise": premise.strip(),
            "mode": story_mode,
            "characters": character_names,
            "world": world_name,
            "world_context": world_context,
            "props": prop_names,
            "continuity": continuity_context or {},
        }
        user = (
            "CREATOR STORY CONTEXT\n"
            + json.dumps(context, ensure_ascii=False)
            + "\n\nSuggest the six editable Story beats now."
        )
        result = self.structured_provider.generate_structured(
            system=system,
            user=user,
            schema=StoryBeatSuggestions,
        )
        return StoryBeatSuggestions.model_validate(result)
