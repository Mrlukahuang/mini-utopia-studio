from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


HeroCompositionMode = Literal["monolithic", "composite", "modular"]
HeroCompositionRole = Literal["root", "intrinsic", "attachment", "standalone"]


class HeroCompositionMember(BaseModel):
    element_id: str
    role: HeroCompositionRole
    relation_to_root: str = ""
    reason: str = ""


class HeroCompositionCluster(BaseModel):
    cluster_id: str
    root_element_id: str
    mode: HeroCompositionMode = "monolithic"
    concept_summary: str = ""
    members: list[HeroCompositionMember] = Field(default_factory=list, max_length=16)


class WorldHeroCompositionPlan(BaseModel):
    schema_version: str = "0.1"
    source: Literal["gpt", "deterministic_fallback"] = "deterministic_fallback"
    clusters: list[HeroCompositionCluster] = Field(default_factory=list, max_length=4)
    standalone_element_ids: list[str] = Field(default_factory=list, max_length=32)
    planning_note: str = ""
