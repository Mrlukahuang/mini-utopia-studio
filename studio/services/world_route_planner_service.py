from __future__ import annotations

from studio.models.world import WorldScenePlan


class WorldRoutePlannerService:
    """Validate and normalize the semantic exploration/photo route.

    GPT may propose a route order, but this service guarantees that references
    are valid, important creator objects are not silently skipped, and the
    executable Portal remains the final reveal.
    """

    def normalize(self, plan: WorldScenePlan) -> WorldScenePlan:
        by_id = {item.scene_id: item for item in plan.elements}
        ordered: list[str] = []

        def add(scene_id: str) -> None:
            if scene_id in by_id and scene_id not in ordered:
                ordered.append(scene_id)

        for scene_id in plan.exploration_order:
            add(scene_id)

        # Make sure required, visit-worthy creator content is represented even if
        # the model omitted it from the suggested route.
        for item in plan.elements:
            if (
                item.required
                and item.kind in {"landmark", "structure", "bridge", "water"}
            ):
                add(item.scene_id)

        portal_ids = [
            item.scene_id for item in plan.elements if item.kind == "portal"
        ]
        for portal_id in portal_ids:
            if portal_id in ordered:
                ordered.remove(portal_id)
        for portal_id in portal_ids:
            ordered.append(portal_id)

        valid_photo_spots: list[str] = []
        for scene_id in plan.photo_spot_ids:
            if scene_id in by_id and scene_id not in valid_photo_spots:
                valid_photo_spots.append(scene_id)

        # Preserve model intent but ensure there are enough useful camera moments.
        for scene_id in ordered:
            item = by_id[scene_id]
            if (
                item.photo_opportunity
                and scene_id not in valid_photo_spots
                and len(valid_photo_spots) < 6
            ):
                valid_photo_spots.append(scene_id)

        if not valid_photo_spots:
            for scene_id in ordered:
                item = by_id[scene_id]
                if item.kind in {"landmark", "structure", "water", "portal"}:
                    valid_photo_spots.append(scene_id)
                if len(valid_photo_spots) >= 4:
                    break

        route_intent = plan.route_intent.strip() or (
            "Create a natural, walkable discovery route from Spawn through major "
            "landmarks, with scenic/photo pauses and useful video reveal beats, "
            "ending with a memorable Portal reveal."
        )

        return plan.model_copy(
            update={
                "exploration_order": ordered,
                "photo_spot_ids": valid_photo_spots[:8],
                "route_intent": route_intent,
            }
        )
