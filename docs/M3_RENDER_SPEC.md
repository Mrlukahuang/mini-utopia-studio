# Mini Utopia M3 RenderSpec Contract

## North Star

Blueprint controls world truth. AppearancePlan controls visual intent.
Geometry Compiler controls construction. Three.js is the final unified stage.

GPT generates structured data, never world-specific Three.js JavaScript.

## Ownership

### Blueprint — authoritative game/world logic

Blueprint owns object identity, kind, semantic role, world x/y/z, world
width/depth/height, support relationships, walkability, paths, Portal location,
and camera beats.

Appearance/Vision is not allowed to change these facts.

### ObjectAppearanceSpec — visual intent

GPT and Vision may define silhouette family, main body primitive, attached local
parts, local proportions, geometry-strategy intent, palette/material roles,
edge language, detail density, sockets, and Preview evidence.

### WorldRenderSpec — Three.js-facing compiled contract

The Geometry Compiler combines Blueprint truth + AppearancePlan intent and emits
stable render data. Three.js does not interpret creator prose.

## Three.js field mapping

Three.js Object3D maps to ThreeObjectSpec:

| Three.js concern | Mini Utopia field |
| --- | --- |
| position | transform.position |
| quaternion | transform.quaternion |
| scale | transform.scale |
| visible | visible |
| castShadow | cast_shadow |
| receiveShadow | receive_shadow |
| renderOrder | render_order |
| frustumCulled | frustum_culled |
| layers | layer |

Reference: https://threejs.org/docs/pages/Object3D.html

Three.js BufferGeometry consumes vertex attributes and optional indices.
ThreeBufferGeometrySpec maps positions, indices, normals, UVs, and vertex colors
to those buffers.

References:
- https://threejs.org/docs/pages/BufferGeometry.html
- https://threejs.org/docs/pages/BufferAttribute.html

Large geometry must not be stored as giant JSON arrays. ThreeGeometrySpec
supports external asset_path, asset_mime_type, and asset_sha256. Inline buffers
are only for small generated meshes and tests.

Three.js Mesh combines geometry with material. Mini Utopia uses
ThreeMeshNodeSpec.geometry + material_id.

Reference: https://threejs.org/docs/pages/Mesh.html

## Material

The default Mini Utopia runtime material is physically based
MeshStandardMaterial.

ThreeMaterialSpec supports color, roughness, metalness, emissive, opacity,
alpha-test, side, vertex colors, and texture slots for color/normal/roughness/
metalness/emissive/alpha.

Reference: https://threejs.org/docs/pages/MeshStandardMaterial.html

GPT normally assigns semantic palette roles rather than arbitrary HEX colors.
The Geometry Compiler resolves primary, secondary, accent, cream, sky, water,
foliage, glow, and dark_accent from the World theme and Style Constitution.

## Texture

ThreeTextureSpec stores texture ID/usage, external asset path, MIME type, color
space, wrapping, and repeat. Texture binaries belong in Object Storage, not
metadata JSON.

## Camera

Blueprint camera points own where cameras are and what they look at.

RenderCameraSpec owns projection characteristics: FOV, near/far clipping, zoom,
and film gauge. Canvas aspect ratio is runtime-derived.

Reference: https://threejs.org/docs/pages/PerspectiveCamera.html

## Lighting / environment

RenderEnvironmentSpec owns background, fog, environment intensity, and lights.
RenderLightSpec supports ambient, hemisphere, directional, and point lights.
Directional lights use a position + target.

Reference: https://threejs.org/docs/pages/DirectionalLight.html

## Repeated blocks / foliage

Future repeated voxel blocks, flowers, lamps and props should use InstancedMesh
when they share geometry/material. Per-instance transform and optional color
reduce draw calls.

Reference: https://threejs.org/docs/pages/InstancedMesh.html

## Geometry source strategies

ObjectAppearanceSpec.geometry_strategy is planning intent:
- procedural
- voxel
- glb
- hybrid

Compiled ThreeGeometrySpec.source_type must remain truthful:
- primitive — runtime can build it immediately
- buffer — actual BufferGeometry data/binary exists
- glb — an actual GLB asset exists

The compiler must never label a planned GLB as runtime GLB before the artifact
exists.

## Shape grammar

GPT describes an object with one main_body, local parts, and optional attachment
or walkable sockets.

Each part defines primitive, parent part, normalized local position, local
rotation, relative scale, palette role, material role, and a surface-detail note.

The deterministic compiler clamps local offsets/scales so GPT cannot override
Blueprint world dimensions.

## Style Constitution

Every object, regardless of generation method, must obey the same style system:
- original soft voxel / rounded block geometry
- readable toy-scale silhouette
- gentle bevel/rounding
- high-lightness macaron harmony
- matte / soft toy PBR response
- very low metalness unless Canon requires otherwise
- no photoreal skin/fur/material drift
- no unrelated branded-game visual language

This applies equally to procedural geometry, voxel geometry, future AI GLB, and
textures. A GLB is not accepted merely because its shape is correct; it must be
style-normalized before joining the World.

## Current M3 pipeline

Creator Prompt
→ Scene Plan
→ Blueprint
→ GPT source AppearancePlan
→ Blueprint + AppearancePlan World Preview
→ Vision Preview refinement
→ final AppearancePlan
→ Geometry Compiler
→ WorldRenderSpec
→ Three.js

Preview/Vision may refine silhouette, parts, material roles, local shape, and
visual evidence. It may never rewrite Blueprint world logic.

## Future insertion points

### Voxel Compiler

Voxel Compiler may take ObjectAppearanceSpec and emit chunked voxel
occupancy/palette data, greedy-meshed BufferGeometry, or instanced blocks. The
result still enters Three.js through ThreeGeometrySpec.

### Open-source Hero GLB Worker

M3.3 adds an optional GPU Worker for major organic Hero objects.

Current adapters:

- Pixal3D — quality benchmark
- TripoSR — lightweight baseline

The Worker receives a Preview crop + ObjectAppearanceSpec and returns GLB. The
main Studio stores the GLB in ObjectStorage and appends a real
ThreeGeometrySpec(source_type="glb") node while retaining procedural nodes as
fallback.

Three.js loads the GLB asynchronously, measures its bounding box, uniformly fits
it inside the authoritative Blueprint width/height/depth envelope, centers x/z,
and aligns the model bottom to Blueprint base y. Procedural fallback is hidden
only after GLB load succeeds.

For the first spike, private GLB bytes are embedded into Explore as data URIs.
Production transport should move to short-lived signed URLs; RenderSpec does not
need to change.

The GPU runtime remains isolated from Streamlit so CUDA/PyTorch versions for
Pixal3D, TripoSR, TRELLIS or future generators can change independently.

### AI / procedural GLB

Additional Hero generators may emit GLB through the same provider/Worker
contract. The result is stored in Object Storage, style-normalized, then
referenced by ThreeGeometrySpec.asset_path. No Blueprint changes are required.

### Appearance correction loop

A future quality loop may compare a Three.js screenshot with the approved World
Preview and update AppearancePlan only. Blueprint remains unchanged.

## Benchmark

The first M3 benchmark is Cloud Whale Station.

Passing condition: without debug labels, the Three.js scene must read as a large
aerial whale carrying a garden/Portal while preserving Blueprint path and
elevation.

The benchmark is recognizable 3D identity, not photorealism.
