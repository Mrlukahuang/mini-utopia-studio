from __future__ import annotations

import re
from dataclasses import dataclass

from studio.models.world import (
    GridSpec,
    WorldLayoutElement,
    WorldPoint,
    WorldProfile,
    WorldScenePlan,
    WorldVisualAnchor,
)


_KIND_KEYWORDS = {
    "portal": ("portal", "gate", "arch", "传送门", "星门", "拱门"),
    "water": ("lake", "pond", "river", "water", "waterfall", "lagoon", "湖", "池", "河", "瀑布", "水"),
    "bridge": ("bridge", "桥"),
    "structure": (
        "castle", "tower", "house", "building", "palace", "temple", "plaza",
        "城堡", "塔", "房", "屋", "宫", "殿", "广场",
    ),
    "terrain": (
        "island", "mountain", "hill", "forest", "garden", "meadow", "cliff",
        "岛", "山", "森林", "花园", "草地", "悬崖",
    ),
}

_STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "at", "to", "and", "with",
    "main", "central", "visible", "large", "small", "pastel",
}


@dataclass(frozen=True)
class WorldLayoutPlan:
    elements: list[WorldLayoutElement]

    def first(self, kind: str) -> WorldLayoutElement | None:
        return next((element for element in self.elements if element.kind == kind), None)


class WorldLayoutService:
    """Compile visual-anchor evidence into stable 50x50 Blueprint coordinates.

    The compiler is deliberately deterministic and inspectable. Vision tells us
    what is visible; this service decides how those relations map into executable
    world coordinates without delegating runtime layout to a black-box model.
    """

    def compile_scene_plan(
        self,
        *,
        plan: WorldScenePlan,
        grid: GridSpec,
    ) -> WorldLayoutPlan:
        """Compile a semantic Scene Plan into deterministic runtime positions."""
        elements: list[WorldLayoutElement] = []
        for index, scene in enumerate(plan.elements):
            pos = self._default_position(kind=scene.kind, index=index, grid=grid)
            width, depth, height = self._default_footprint(scene.kind)
            element = WorldLayoutElement(
                element_id=scene.scene_id,
                name=scene.name,
                kind=scene.kind,
                position=pos,
                width=width,
                depth=depth,
                height=height,
                source_evidence=[
                    f"scene_plan:{scene.source}",
                    *scene.relation_hints,
                ],
            )
            if scene.placement_hint:
                self._apply_element_hint(element, scene.placement_hint, grid)
                element.source_evidence.append(scene.placement_hint)
            elements.append(element)

        # Resolve each element's own relative placement hint after every target
        # exists. This keeps hints like "湖的右侧" attached to the Castle, rather
        # than accidentally moving the Lake itself.
        by_scene_id = {scene.scene_id: scene for scene in plan.elements}
        by_element_id = {element.element_id: element for element in elements}
        for scene_id, scene in by_scene_id.items():
            element = by_element_id.get(scene_id)
            if element is None or not scene.placement_hint:
                continue
            self._apply_owned_hint_relation(
                elements,
                element,
                scene.placement_hint,
                grid,
            )

        for scene in plan.elements:
            for relation in scene.relation_hints:
                for clause in self._relation_clauses(relation):
                    self._apply_relation(elements, clause, grid)
        for relation in plan.spatial_relations:
            for clause in self._relation_clauses(relation):
                self._apply_relation(elements, clause, grid)

        for element in elements:
            element.position.x = self._clamp(element.position.x, 5.0, grid.width - 5.0)
            element.position.z = self._clamp(element.position.z, 5.0, grid.depth - 5.0)

        return WorldLayoutPlan(elements=elements)

    def compile(
        self,
        *,
        profile: WorldProfile,
        anchor: WorldVisualAnchor,
        grid: GridSpec,
    ) -> WorldLayoutPlan:
        names: list[str] = []

        def add_name(value: str) -> None:
            value = (value or "").strip()
            if value and not self._contains_equivalent(names, value):
                names.append(value)

        for item in anchor.must_preserve:
            add_name(item)
        for item in profile.landmark_ideas:
            add_name(item)
        for item in profile.water_features:
            add_name(item)
        if profile.portal_form and not any(self._kind(name) == "portal" for name in names):
            add_name(profile.portal_form)

        elements: list[WorldLayoutElement] = []
        for index, name in enumerate(names[:10]):
            kind = self._kind(name)
            pos = self._default_position(kind=kind, index=index, grid=grid)
            width, depth, height = self._default_footprint(kind)
            elements.append(
                WorldLayoutElement(
                    element_id=f"LAYOUT_{index+1:02d}",
                    name=name,
                    kind=kind,
                    position=pos,
                    width=width,
                    depth=depth,
                    height=height,
                    source_evidence=[name],
                )
            )

        if not any(element.kind == "portal" for element in elements):
            elements.append(
                WorldLayoutElement(
                    element_id=f"LAYOUT_{len(elements)+1:02d}",
                    name=profile.portal_form or "Portal",
                    kind="portal",
                    position=WorldPoint(x=grid.width * .78, y=0, z=grid.depth * .5),
                    width=5.5,
                    depth=3.0,
                    height=6.0,
                    source_evidence=["profile.portal_form"],
                )
            )

        for note in anchor.composition_notes:
            self._apply_composition_note(elements, note, grid)

        for relation in anchor.spatial_relations:
            self._apply_relation(elements, relation, grid)

        # Keep every executable point safely inside the current playable bounds.
        for element in elements:
            element.position.x = self._clamp(element.position.x, 5.0, grid.width - 5.0)
            element.position.z = self._clamp(element.position.z, 5.0, grid.depth - 5.0)

        return WorldLayoutPlan(elements=elements)

    def _apply_composition_note(
        self,
        elements: list[WorldLayoutElement],
        note: str,
        grid: GridSpec,
    ) -> None:
        element = self._resolve_element(elements, note)
        if element is None:
            return

        text = note.lower()
        if any(token in text for token in ("left", "left side", "左")):
            element.position.x = grid.width * .28
        elif any(token in text for token in ("right", "right side", "右")):
            element.position.x = grid.width * .72
        elif any(token in text for token in ("center", "centre", "central", "中央", "中心")):
            element.position.x = grid.width * .5
            element.position.z = grid.depth * .5

        if any(token in text for token in ("foreground", "front of frame", "前景")):
            element.position.z = grid.depth * .72
        elif any(token in text for token in ("background", "rear", "背景", "后景")):
            element.position.z = grid.depth * .28
        elif any(token in text for token in ("midground", "middle ground", "中景")):
            element.position.z = grid.depth * .5

        element.source_evidence.append(note)

    def _apply_relation(
        self,
        elements: list[WorldLayoutElement],
        relation: str,
        grid: GridSpec,
    ) -> None:
        text = relation.strip()
        lowered = text.lower()
        if self._apply_connection_relation(elements, text, lowered, grid):
            return
        if self._apply_chinese_relative_relation(elements, text, grid):
            return
        relation_defs = [
            ("in front of", "front"),
            ("behind", "behind"),
            ("left of", "left"),
            ("right of", "right"),
            ("next to", "near"),
            ("beside", "near"),
            ("near", "near"),
            ("前面", "front"),
            ("前方", "front"),
            ("后面", "behind"),
            ("后方", "behind"),
            ("左边", "left"),
            ("左侧", "left"),
            ("右边", "right"),
            ("右侧", "right"),
            ("旁边", "near"),
            ("附近", "near"),
        ]

        marker = None
        mode = None
        for phrase, relation_mode in relation_defs:
            if phrase in lowered:
                marker = phrase
                mode = relation_mode
                break
        if marker is None or mode is None:
            return

        before, after = lowered.split(marker, 1)
        subject = self._resolve_element(elements, before)
        target = self._resolve_element(elements, after)
        if subject is None or target is None or subject is target:
            # A full-relation resolver helps when the subject/object wording is
            # generic, e.g. "castle behind portal".
            candidates = sorted(
                (
                    (self._match_score(element, before), element)
                    for element in elements
                ),
                key=lambda item: item[0],
                reverse=True,
            )
            targets = sorted(
                (
                    (self._match_score(element, after), element)
                    for element in elements
                ),
                key=lambda item: item[0],
                reverse=True,
            )
            if subject is None and candidates and candidates[0][0] > 0:
                subject = candidates[0][1]
            if target is None and targets and targets[0][0] > 0:
                target = targets[0][1]
        if subject is None or target is None or subject is target:
            return

        step_x = grid.width * .20
        step_z = grid.depth * .20
        if mode == "front":
            subject.position.z = target.position.z + step_z
            subject.position.x = target.position.x
        elif mode == "behind":
            subject.position.z = target.position.z - step_z
            subject.position.x = target.position.x
        elif mode == "left":
            subject.position.x = target.position.x - step_x
            subject.position.z = target.position.z
        elif mode == "right":
            subject.position.x = target.position.x + step_x
            subject.position.z = target.position.z
        elif mode == "near":
            subject.position.x = target.position.x + grid.width * .09
            subject.position.z = target.position.z + grid.depth * .04

        subject.source_evidence.append(text)
        target.source_evidence.append(text)

    def _apply_element_hint(
        self,
        element: WorldLayoutElement,
        hint: str,
        grid: GridSpec,
    ) -> None:
        text = hint.lower()
        if any(token in text for token in ("left", "left side", "左")):
            element.position.x = grid.width * .28
        elif any(token in text for token in ("right", "right side", "右")):
            element.position.x = grid.width * .72
        elif any(token in text for token in ("center", "centre", "central", "中央", "中心")):
            element.position.x = grid.width * .5

        if any(token in text for token in ("front", "foreground", "入口", "前景")):
            element.position.z = grid.depth * .72
        elif any(token in text for token in ("behind", "rear", "background", "后面", "后方", "背景")):
            element.position.z = grid.depth * .28
        elif any(token in text for token in ("middle", "midground", "中部", "中景")):
            element.position.z = grid.depth * .5

    def _apply_owned_hint_relation(
        self,
        elements: list[WorldLayoutElement],
        subject: WorldLayoutElement,
        hint: str,
        grid: GridSpec,
    ) -> bool:
        """Resolve a placement hint relative to another named Scene element."""
        text = hint.strip()
        lowered = text.lower()

        if subject.kind == "bridge":
            synthetic = f"{subject.name} {text}"
            if self._apply_connection_relation(
                elements,
                synthetic,
                synthetic.lower(),
                grid,
            ):
                return True

        direction_defs = (
            ("right of", "right"),
            ("left of", "left"),
            ("behind", "behind"),
            ("in front of", "front"),
            ("next to", "near"),
            ("beside", "near"),
            ("右侧", "right"),
            ("右边", "right"),
            ("左侧", "left"),
            ("左边", "left"),
            ("后方", "behind"),
            ("后面", "behind"),
            ("前方", "front"),
            ("前面", "front"),
            ("旁边", "near"),
            ("附近", "near"),
        )
        marker = None
        mode = None
        target_phrase = ""
        for phrase, relation_mode in direction_defs:
            if phrase not in lowered:
                continue
            marker = phrase
            mode = relation_mode
            if phrase in {"右侧", "右边", "左侧", "左边", "后方", "后面", "前方", "前面", "旁边", "附近"}:
                target_phrase = text.split(phrase, 1)[0]
                target_phrase = re.sub(r"[的\s]+$", "", target_phrase)
            else:
                target_phrase = text.split(phrase, 1)[1]
            break

        if marker is None or mode is None or not target_phrase.strip():
            return False
        target = self._resolve_element(elements, target_phrase)
        if target is None or target is subject:
            return False

        step_x = grid.width * .20
        step_z = grid.depth * .20
        if mode == "right":
            subject.position.x = target.position.x + step_x
            subject.position.z = target.position.z
        elif mode == "left":
            subject.position.x = target.position.x - step_x
            subject.position.z = target.position.z
        elif mode == "behind":
            subject.position.z = target.position.z - step_z
            subject.position.x = target.position.x
        elif mode == "front":
            subject.position.z = target.position.z + step_z
            subject.position.x = target.position.x
        else:
            subject.position.x = target.position.x + grid.width * .09
            subject.position.z = target.position.z + grid.depth * .04

        if "偏左" in text:
            subject.position.x -= step_x
        elif "偏右" in text:
            subject.position.x += step_x

        subject.source_evidence.append(text)
        target.source_evidence.append(text)
        return True

    def _apply_chinese_relative_relation(
        self,
        elements: list[WorldLayoutElement],
        text: str,
        grid: GridSpec,
    ) -> bool:
        """Handle common Chinese subject/target word orders without moving the target."""
        patterns = (
            re.compile(
                r"(?P<subject>.+?)(?:在|位于)(?P<target>.+?)的?"
                r"(?P<direction>右侧|左侧|后方|前方|右边|左边|后面|前面|旁边|附近)"
                r"(?P<offset>偏左|偏右)?"
            ),
            re.compile(
                r"(?P<target>.+?)的?"
                r"(?P<direction>右侧|左侧|后方|前方|右边|左边|后面|前面|旁边|附近)"
                r"(?:有|放着|放置|是)(?P<subject>.+)"
            ),
        )
        match = next((pattern.search(text) for pattern in patterns if pattern.search(text)), None)
        if match is None:
            return False

        subject = self._resolve_element(elements, match.group("subject"))
        target = self._resolve_element(elements, match.group("target"))
        if subject is None or target is None or subject is target:
            return False

        direction = match.group("direction")
        offset = match.groupdict().get("offset") or ""
        step_x = grid.width * .20
        step_z = grid.depth * .20
        if direction in {"右侧", "右边"}:
            subject.position.x = target.position.x + step_x
            subject.position.z = target.position.z
        elif direction in {"左侧", "左边"}:
            subject.position.x = target.position.x - step_x
            subject.position.z = target.position.z
        elif direction in {"后方", "后面"}:
            subject.position.z = target.position.z - step_z
            subject.position.x = target.position.x
        elif direction in {"前方", "前面"}:
            subject.position.z = target.position.z + step_z
            subject.position.x = target.position.x
        else:
            subject.position.x = target.position.x + grid.width * .09
            subject.position.z = target.position.z + grid.depth * .04

        if offset == "偏左":
            subject.position.x -= step_x
        elif offset == "偏右":
            subject.position.x += step_x

        subject.source_evidence.append(text)
        target.source_evidence.append(text)
        return True

    def _apply_connection_relation(
        self,
        elements: list[WorldLayoutElement],
        text: str,
        lowered: str,
        grid: GridSpec,
    ) -> bool:
        marker = None
        for candidate in (" connects ", " connecting ", " between ", "连接", "位于"):
            if candidate in lowered:
                marker = candidate
                break
        if marker is None:
            return False

        before, after = lowered.split(marker, 1)
        subject = self._resolve_element(elements, before)
        if subject is None or subject.kind != "bridge":
            return False

        parts = [
            part.strip()
            for part in re.split(r"\band\b|\bto\b|和|与|到", after)
            if part.strip()
        ]
        targets: list[WorldLayoutElement] = []
        for part in parts:
            target = self._resolve_element(elements, part)
            if target is not None and target is not subject and target not in targets:
                targets.append(target)
            if len(targets) == 2:
                break
        if len(targets) < 2:
            return False

        subject.position.x = (targets[0].position.x + targets[1].position.x) / 2
        subject.position.z = (targets[0].position.z + targets[1].position.z) / 2
        subject.source_evidence.append(text)
        targets[0].source_evidence.append(text)
        targets[1].source_evidence.append(text)
        return True

    def _resolve_element(
        self,
        elements: list[WorldLayoutElement],
        phrase: str,
    ) -> WorldLayoutElement | None:
        if not phrase.strip():
            return None
        ranked = sorted(
            ((self._match_score(element, phrase), element) for element in elements),
            key=lambda item: item[0],
            reverse=True,
        )
        if ranked and ranked[0][0] > 0:
            return ranked[0][1]
        return None

    def _match_score(self, element: WorldLayoutElement, phrase: str) -> int:
        phrase_norm = self._normalize(phrase)
        aliases = self._aliases(element.name)
        score = 0
        for alias in aliases:
            alias_norm = self._normalize(alias)
            if alias_norm and alias_norm in phrase_norm:
                score += 8
            alias_tokens = self._tokens(alias_norm)
            phrase_tokens = self._tokens(phrase_norm)
            score += len(alias_tokens & phrase_tokens) * 3

        # Generic role words allow vision phrases such as "star portal" to map
        # back to a profile item such as "Star Arch / 星星拱门".
        for keyword in _KIND_KEYWORDS.get(element.kind, ()):
            if keyword.lower() in phrase_norm:
                score += 2
        return score

    def _kind(self, name: str) -> str:
        lowered = name.lower()
        # A place named after the Portal is not necessarily the Portal itself.
        # e.g. "Portal Plaza / 传送门广场" is a landmark/structure around the
        # actual Star Arch, and must not create a second executable Portal.
        if any(token in lowered for token in ("plaza", "square", "广场")):
            return "structure"
        for kind in ("portal", "water", "bridge", "structure", "terrain"):
            if any(keyword.lower() in lowered for keyword in _KIND_KEYWORDS[kind]):
                return kind
        return "landmark"

    @staticmethod
    def _relation_clauses(value: str) -> list[str]:
        return [
            part.strip()
            for part in re.split(r"[.;,，。；]+", value or "")
            if part.strip()
        ]

    @staticmethod
    def _default_position(*, kind: str, index: int, grid: GridSpec) -> WorldPoint:
        if kind == "portal":
            return WorldPoint(x=grid.width * .72, y=0, z=grid.depth * .5)
        if kind == "water":
            return WorldPoint(x=grid.width * .5, y=0, z=grid.depth * .5)
        slots = (
            (.50, .50),
            (.72, .30),
            (.70, .72),
            (.36, .76),
            (.30, .30),
            (.50, .22),
        )
        x, z = slots[index % len(slots)]
        return WorldPoint(x=grid.width * x, y=0, z=grid.depth * z)

    @staticmethod
    def _default_footprint(kind: str) -> tuple[float, float, float]:
        if kind == "water":
            return 12.0, 10.0, .3
        if kind == "terrain":
            return 11.0, 11.0, 3.0
        if kind == "bridge":
            return 10.0, 3.0, 1.0
        if kind == "portal":
            return 5.5, 3.0, 6.0
        if kind == "structure":
            return 7.0, 7.0, 8.0
        return 6.0, 6.0, 5.0

    @classmethod
    def _contains_equivalent(cls, existing: list[str], candidate: str) -> bool:
        candidate_tokens = cls._tokens(cls._normalize(candidate))
        if not candidate_tokens:
            return False
        for item in existing:
            tokens = cls._tokens(cls._normalize(item))
            if candidate_tokens == tokens or (
                candidate_tokens & tokens
                and min(len(candidate_tokens), len(tokens)) <= len(candidate_tokens & tokens)
            ):
                return True
        return False

    @staticmethod
    def _aliases(name: str) -> list[str]:
        aliases = [name]
        aliases.extend(part.strip() for part in re.split(r"[/|·]", name) if part.strip())
        return aliases

    @staticmethod
    def _normalize(value: str) -> str:
        return re.sub(r"[^a-z0-9\u4e00-\u9fff ]+", " ", value.lower()).strip()

    @staticmethod
    def _tokens(value: str) -> set[str]:
        return {
            token for token in value.split()
            if token and token not in _STOPWORDS
        }

    @staticmethod
    def _clamp(value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))
