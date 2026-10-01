from __future__ import annotations
from studio.core.ids import new_id
from studio.models.universe import Universe
from studio.repositories.base import StudioRepository


MINI_UTOPIA_NAME = "Mini Utopia"


class UniverseService:
    def __init__(self, repository: StudioRepository):
        self.repository = repository

    def ensure_mini_utopia(self) -> Universe:
        for universe in self.repository.list_universes():
            if universe.name == MINI_UTOPIA_NAME:
                return universe
        universe = Universe(
            universe_id=new_id("UNIV"),
            name=MINI_UTOPIA_NAME,
            tagline="Small Worlds. Big Imagination.",
            description=(
                "A universe of miniature worlds connected by mysterious portals. "
                "Travel around every world: real, imaginary, historical, future, or completely invented."
            ),
            canon_rules=[
                "Keep an original miniature voxel/block visual DNA in Canon Mode.",
                "The Traveler is the audience anchor; new companions may recur.",
                "Every episode should contain discovery or a problem, not only sightseeing.",
                "Playground experiments never change Canon unless explicitly promoted.",
            ],
            story_formula=["Arrive", "Discover", "Problem", "Adventure", "Surprise", "Portal"],
            portal_rule="A portal can connect any world and may become the ending hook for the next episode.",
        )
        self.repository.save_universe(universe)
        return universe
