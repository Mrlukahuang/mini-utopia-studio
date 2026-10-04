from __future__ import annotations

import math

from studio.models.render import (
    ObjectAppearanceSpec,
    RenderEnvironmentSpec,
    RenderLightSpec,
    RenderQuaternion,
    RenderVec3,
    ThreeGeometrySpec,
    ThreeMaterialSpec,
    ThreeMeshNodeSpec,
    ThreeObjectSpec,
    ThreeObjectTransformSpec,
    WorldAppearancePlan,
    WorldRenderSpec,
)
from studio.models.world import WorldBlueprint, WorldLayoutElement, WorldProfile


_DEFAULT_PALETTE = [
    "#F7B7D2",  # strawberry pink
    "#B9E7D0",  # mint
    "#D7C2F3",  # lavender
    "#BDE3F7",  # sky/water
    "#FFF4D7",  # cream
]

_ROLE_FALLBACKS = {
    "primary": "#F7B7D2",
    "secondary": "#B9E7D0",
    "accent": "#D7C2F3",
    "cream": "#FFF4D7",
    "sky": "#BDE3F7",
    "water": "#BDE3F7",
    "foliage": "#B9E7D0",
    "glow": "#D7C2F3",
    "dark_accent": "#7A6E86",
}


class WorldGeometryCompilerService:
    """Compile Appearance DATA into a stable Three.js-facing RenderSpec."""

    def compile(
        self,
        *,
        profile: WorldProfile,
        blueprint: WorldBlueprint,
        appearance: WorldAppearancePlan,
        style_profile: dict,
    ) -> WorldRenderSpec:
        palette = self._palette_roles(profile)
        appearance_by_id = {item.element_id: item for item in appearance.objects}
        materials: dict[str, ThreeMaterialSpec] = {}
        objects: list[ThreeObjectSpec] = []

        for element in blueprint.layout_elements:
            item = appearance_by_id.get(element.element_id)
            if item is None:
                continue
            objects.append(
                self._compile_object(
                    element=element,
                    appearance=item,
                    palette=palette,
                    materials=materials,
                )
            )

        return WorldRenderSpec(
            location_asset_id=blueprint.location_asset_id,
            blueprint_schema_version=blueprint.schema_version,
            materials=list(materials.values()),
            objects=objects,
            environment=self._environment(profile, palette, style_profile),
        )

    def _compile_object(
        self,
        *,
        element: WorldLayoutElement,
        appearance: ObjectAppearanceSpec,
        palette: dict[str, str],
        materials: dict[str, ThreeMaterialSpec],
    ) -> ThreeObjectSpec:
        parts = [appearance.main_body, *appearance.parts]
        nodes: list[ThreeMeshNodeSpec] = []
        seen_part_ids: set[str] = set()

        for index, part in enumerate(parts):
            raw_part_id = part.part_id.strip() or f"part_{index:02d}"
            part_id = raw_part_id
            if part_id in seen_part_ids:
                part_id = f"{raw_part_id}_{index:02d}"
            parent_part_id = (
                part.parent_part_id
                if part.parent_part_id in seen_part_ids
                else ""
            )
            seen_part_ids.add(part_id)

            material_id = self._material_id(
                palette_role=part.palette_role,
                material_role=part.material_role,
            )
            if material_id not in materials:
                materials[material_id] = self._material(
                    material_id=material_id,
                    palette_role=part.palette_role,
                    material_role=part.material_role,
                    palette=palette,
                )

            nodes.append(
                ThreeMeshNodeSpec(
                    node_id=f"{element.element_id}:{part_id}",
                    parent_node_id=(
                        f"{element.element_id}:{parent_part_id}"
                        if parent_part_id
                        else ""
                    ),
                    geometry=ThreeGeometrySpec(
                        # Strategy is planning intent. Until an actual GLB/buffer
                        # artifact exists, the compiled runtime source stays primitive.
                        source_type="primitive",
                        primitive=part.primitive,
                        primitive_size=RenderVec3(
                            x=max(
                                .08,
                                element.width
                                * self._clamp(abs(part.relative_scale.x), .05, 2.5),
                            ),
                            y=max(
                                .08,
                                element.height
                                * self._clamp(abs(part.relative_scale.y), .05, 2.5),
                            ),
                            z=max(
                                .08,
                                element.depth
                                * self._clamp(abs(part.relative_scale.z), .05, 2.5),
                            ),
                        ),
                    ),
                    material_id=material_id,
                    # Blueprint y is the object's base/support elevation.
                    # Shape grammar local positions are center-relative, while
                    # Three.js primitives are centered on their local origin.
                    # Lift every compiled part by half the authoritative object
                    # height so geometry occupies y .. y+height instead of
                    # straddling the Blueprint base plane.
                    local_position=RenderVec3(
                        x=self._clamp(part.local_position.x, -1.5, 1.5)
                        * element.width,
                        y=(
                            element.height * .5
                            + self._clamp(part.local_position.y, -1.5, 1.5)
                            * element.height
                        ),
                        z=self._clamp(part.local_position.z, -1.5, 1.5)
                        * element.depth,
                    ),
                    local_quaternion=self._quaternion_from_euler_degrees(
                        part.rotation_degrees.x,
                        part.rotation_degrees.y,
                        part.rotation_degrees.z,
                    ),
                )
            )

        return ThreeObjectSpec(
            element_id=element.element_id,
            name=element.name,
            kind=element.kind,
            semantic_key=element.semantic_key,
            spatial_mode=element.spatial_mode,
            traversability=element.traversability,
            transform=ThreeObjectTransformSpec(
                position=element.position.model_copy(deep=True),
                quaternion=self._orientation_quaternion(element.orientation),
            ),
            nodes=nodes,
            source="appearance_spec",
        )

    @staticmethod
    def _palette_roles(profile: WorldProfile) -> dict[str, str]:
        source = list(profile.theme_color_hexes) or list(_DEFAULT_PALETTE)
        while len(source) < 5:
            source.append(_DEFAULT_PALETTE[len(source) % len(_DEFAULT_PALETTE)])
        return {
            "primary": source[0],
            "secondary": source[1],
            "accent": source[2],
            "cream": source[4],
            "sky": source[3],
            "water": source[3],
            "foliage": source[1],
            "glow": source[2],
            "dark_accent": _ROLE_FALLBACKS["dark_accent"],
        }

    @staticmethod
    def _material_id(*, palette_role: str, material_role: str) -> str:
        return f"MAT_{palette_role.upper()}_{material_role.upper()}"

    @staticmethod
    def _material(
        *,
        material_id: str,
        palette_role: str,
        material_role: str,
        palette: dict[str, str],
    ) -> ThreeMaterialSpec:
        color = palette.get(palette_role, _ROLE_FALLBACKS["primary"])
        kwargs = {
            "roughness": .76,
            "metalness": 0.0,
            "emissive_hex": "#000000",
            "emissive_intensity": 0.0,
            "opacity": 1.0,
            "transparent": False,
            "side": "front",
        }
        if material_role == "toy_soft":
            kwargs["roughness"] = .68
        elif material_role == "translucent":
            kwargs.update(
                roughness=.48,
                opacity=.66,
                transparent=True,
                side="double",
            )
        elif material_role == "emissive":
            kwargs.update(
                roughness=.5,
                emissive_hex=color,
                emissive_intensity=1.25,
            )
        elif material_role == "water":
            kwargs.update(
                roughness=.28,
                opacity=.72,
                transparent=True,
                emissive_hex=color,
                emissive_intensity=.12,
                side="double",
            )
        elif material_role == "foliage":
            kwargs["roughness"] = .82
        elif material_role == "glass_soft":
            kwargs.update(
                roughness=.22,
                opacity=.42,
                transparent=True,
                side="double",
            )

        return ThreeMaterialSpec(
            material_id=material_id,
            palette_role=palette_role,
            color_hex=color,
            **kwargs,
        )

    @staticmethod
    def _environment(
        profile: WorldProfile,
        palette: dict[str, str],
        style_profile: dict,
    ) -> RenderEnvironmentSpec:
        return RenderEnvironmentSpec(
            background_hex=palette["sky"],
            fog_hex=palette["sky"],
            fog_near=55.0,
            fog_far=160.0,
            environment_intensity=.8,
            lights=[
                RenderLightSpec(
                    light_id="LIGHT_HEMISPHERE",
                    kind="hemisphere",
                    color_hex="#FFF8F1",
                    intensity=1.05,
                    position=RenderVec3(x=0, y=30, z=0),
                ),
                RenderLightSpec(
                    light_id="LIGHT_KEY",
                    kind="directional",
                    color_hex="#FFF4E8",
                    intensity=1.65,
                    position=RenderVec3(x=35, y=55, z=25),
                    target=RenderVec3(x=25, y=8, z=25),
                    cast_shadow=True,
                ),
                RenderLightSpec(
                    light_id="LIGHT_FILL",
                    kind="directional",
                    color_hex=palette["accent"],
                    intensity=.35,
                    position=RenderVec3(x=-20, y=25, z=-10),
                    target=RenderVec3(x=25, y=6, z=25),
                ),
            ],
        )

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    @classmethod
    def _orientation_quaternion(cls, orientation: str) -> RenderQuaternion:
        if orientation == "inverted":
            return cls._quaternion_from_euler_degrees(0, 0, 180)
        if orientation == "vertical":
            return cls._quaternion_from_euler_degrees(90, 0, 0)
        if orientation == "tilted":
            return cls._quaternion_from_euler_degrees(0, 0, 25)
        return RenderQuaternion()

    @staticmethod
    def _quaternion_from_euler_degrees(
        x_degrees: float,
        y_degrees: float,
        z_degrees: float,
    ) -> RenderQuaternion:
        x = math.radians(x_degrees) * .5
        y = math.radians(y_degrees) * .5
        z = math.radians(z_degrees) * .5
        cx, sx = math.cos(x), math.sin(x)
        cy, sy = math.cos(y), math.sin(y)
        cz, sz = math.cos(z), math.sin(z)

        # XYZ Euler order, matching the runtime contract.
        return RenderQuaternion(
            x=sx * cy * cz + cx * sy * sz,
            y=cx * sy * cz - sx * cy * sz,
            z=cx * cy * sz + sx * sy * cz,
            w=cx * cy * cz - sx * sy * sz,
        )
