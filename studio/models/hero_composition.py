from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HeroCompositionMember(BaseModel):
    element_id: str
    role: Literal["root", "baked"]
    relation_to_root: str = ""
    reason: str = ""


class HeroCompositionCluster(BaseModel):
    cluster_id: str
    root_element_id: str
    render_strategy: Literal["unified_glb"] = "unified_glb"
    concept_summary: str = ""
    members: list[HeroCompositionMember] = Field(default_factory=list, max_length=24)


class WorldHeroCompositionPlan(BaseModel):
    schema_version: str = "0.2"
    source: Literal["gpt", "deterministic_fallback"] = "deterministic_fallback"
    clusters: list[HeroCompositionCluster] = Field(default_factory=list, max_length=4)
    standalone_element_ids: list[str] = Field(default_factory=list, max_length=48)
    planning_note: str = ""
