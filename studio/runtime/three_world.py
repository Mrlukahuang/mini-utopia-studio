from __future__ import annotations

import json
from html import escape

from studio.models.character import CharacterProfile
from studio.models.runtime_character import CharacterRuntimeSpec
from studio.models.render import WorldRenderSpec
from studio.models.world import WorldBlueprint, WorldProfile


THREE_VERSION = "0.181.0"


def _safe_json(value: object) -> str:
    """Serialize data for an inline module script without allowing </script> breaks."""
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


def build_world_runtime_html(
    *,
    world_name: str,
    profile: WorldProfile,
    blueprint: WorldBlueprint,
    character_name: str = "Mini Traveler",
    character_profile: CharacterProfile | None = None,
    character_runtime: CharacterRuntimeSpec | None = None,
    render_spec: WorldRenderSpec | None = None,
    render_asset_payloads: dict[str, str] | None = None,
) -> str:
    """Build a self-contained Three.js playground for a saved WorldBlueprint.

    The runtime is intentionally a renderer of saved data. It does not mutate
    Canon world state or invent new Blueprint structure.
    """

    runtime_data = {
        "worldName": world_name,
        "profile": profile.model_dump(mode="json"),
        "blueprint": blueprint.model_dump(mode="json"),
        "renderSpec": (
            render_spec.model_dump(mode="json")
            if render_spec is not None
            else None
        ),
        "renderAssets": render_asset_payloads or {},
        "characterName": character_name,
        "character": (
            character_profile.model_dump(mode="json")
            if character_profile is not None
            else None
        ),
        "characterRuntime": (
            character_runtime.model_dump(mode="json")
            if character_runtime is not None
            else CharacterRuntimeSpec().model_dump(mode="json")
        ),
    }
    data_json = _safe_json(runtime_data)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
  html, body {{ margin:0; height:100%; overflow:hidden; background:#f8f5ff; }}
  body {{ font-family: ui-rounded, "Nunito", "Noto Sans SC", system-ui, sans-serif; }}
  #wrap {{ position:relative; width:100%; height:100vh; min-height:660px; overflow:hidden; border-radius:24px; }}
  #canvas {{ position:absolute; inset:0; }}
  #canvas canvas {{ touch-action:none; cursor:grab; }}
  .hud {{
    position:absolute; left:18px; top:18px; z-index:5; max-width:340px;
    background:rgba(255,255,255,.84); backdrop-filter:blur(14px);
    border:1px solid rgba(120,104,170,.14); box-shadow:0 12px 32px rgba(53,49,90,.12);
    border-radius:20px; padding:14px 16px; color:#34334c;
  }}
  .hud h2 {{ margin:0 0 4px; font-size:18px; }}
  .hud p {{ margin:3px 0; font-size:12px; line-height:1.4; color:#66617d; }}
  .pill {{
    display:inline-block; margin:7px 5px 0 0; padding:5px 9px; border-radius:999px;
    background:rgba(237,231,255,.9); font-size:11px; font-weight:800;
  }}
  .controls {{
    position:absolute; right:18px; top:18px; z-index:5; display:flex; gap:8px; flex-wrap:wrap;
  }}
  button {{
    border:0; border-radius:999px; padding:10px 14px; cursor:pointer; font:inherit; font-weight:800;
    color:#3a3551; background:rgba(255,255,255,.9); box-shadow:0 8px 24px rgba(58,53,81,.12);
  }}
  button.primary {{ background:#fff0f8; }}
  .tip {{
    position:absolute; left:50%; bottom:18px; transform:translateX(-50%); z-index:5;
    background:rgba(45,49,80,.82); color:white; padding:9px 14px; border-radius:999px;
    font-size:12px; white-space:nowrap;
  }}
  .dot {{ width:9px; height:9px; border-radius:50%; display:inline-block; margin-right:6px; }}
</style>
<script type="importmap">
{{
  "imports": {{
    "three": "https://cdn.jsdelivr.net/npm/three@{THREE_VERSION}/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@{THREE_VERSION}/examples/jsm/"
  }}
}}
</script>
</head>
<body>
<div id="wrap">
  <div id="canvas"></div>
  <div class="hud">
    <h2>🌍 {escape(world_name)}</h2>
    <p><b>Third-person Explore</b> · WASD / Arrow Keys · Drag to Look</p>
    <p>Blueprint v{escape(blueprint.schema_version)} · {blueprint.grid.width}×{blueprint.grid.depth} · {len(blueprint.chunks)} chunks</p>
    <span class="pill">🧸 {escape(character_name)}</span>
    <span class="pill" id="animState">Idle</span>
    <span class="pill">🌀 Portal</span>
    <span class="pill">🎬 Director Camera</span>
    <span class="pill" id="zoomState">🔎 100%</span>
  </div>
  <div class="controls">
    <button id="zoomOut" title="Zoom out / 拉远">−</button>
    <button id="zoomIn" title="Zoom in / 拉近">＋</button>
    <button id="overview" title="Show the whole World / 查看全景">🌐 Overview</button>
    <button id="recenter" title="Put camera behind character / 镜头回到角色背后">🎯 Behind</button>
    <button id="reset">↺ Reset</button>
    <button id="tour" class="primary">🎬 Start Director Tour</button>
  </div>
  <div class="tip">WASD / 方向键跟随镜头移动 · Shift 奔跑 · Mouse Drag / 拖动环绕视角 · Wheel / 滚轮缩放 · 🎯 Behind 回正</div>
  <div id="runtimeError" style="
    display:none; position:absolute; inset:120px 24px auto 24px; z-index:20;
    padding:16px 18px; border-radius:18px; background:rgba(255,235,238,.96);
    color:#8b2e3a; border:1px solid rgba(180,60,80,.2); font-size:13px;
    box-shadow:0 12px 30px rgba(100,40,55,.14);">
  </div>
</div>

<script>
window.addEventListener('error', event => {{
  const box = document.getElementById('runtimeError');
  if (!box) return;
  box.style.display = 'block';
  box.textContent = '3D Runtime error: ' + (event.message || 'Unknown browser error');
}});
window.addEventListener('unhandledrejection', event => {{
  const box = document.getElementById('runtimeError');
  if (!box) return;
  box.style.display = 'block';
  box.textContent = '3D Runtime error: ' + String(event.reason || 'Module failed to load');
}});
</script>

<script type="module">
import * as THREE from 'three';
import {{ GLTFLoader }} from 'three/addons/loaders/GLTFLoader.js';
import {{ RoundedBoxGeometry }} from 'three/addons/geometries/RoundedBoxGeometry.js';

const DATA = {data_json};
const profile = DATA.profile;
const bp = DATA.blueprint;
const renderSpec = DATA.renderSpec || null;
const renderAssets = DATA.renderAssets || {{}};
const layoutById = new Map(
  (bp.layout_elements || []).map(element => [element.element_id, element])
);
const gltfLoader = new GLTFLoader();
const character = DATA.character || {{}};
const characterRuntime = DATA.characterRuntime || {{}};
const visualAnchor = bp.visual_anchor || {{}};
const anchorText = [
  ...(visualAnchor.must_preserve || []),
  visualAnchor.concept_summary || ''
].join(' ').toLowerCase();
const host = document.getElementById('canvas');
const renderSettings = renderSpec?.renderer || {{}};
const cameraSettings = renderSpec?.camera || {{}};

const renderer = new THREE.WebGLRenderer({{
  antialias: renderSettings.antialias !== false,
  alpha:false
}});
renderer.setPixelRatio(
  Math.min(window.devicePixelRatio || 1, renderSettings.pixel_ratio_cap || 2)
);
renderer.shadowMap.enabled = renderSettings.shadows_enabled !== false;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
if (renderSettings.tone_mapping === 'linear') {{
  renderer.toneMapping = THREE.LinearToneMapping;
}} else if (renderSettings.tone_mapping === 'none') {{
  renderer.toneMapping = THREE.NoToneMapping;
}} else {{
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
}}
renderer.toneMappingExposure = renderSettings.exposure || 1;
host.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const palette = (visualAnchor.palette_hexes && visualAnchor.palette_hexes.length)
  ? visualAnchor.palette_hexes
  : (profile.theme_color_hexes && profile.theme_color_hexes.length)
    ? profile.theme_color_hexes
    : ['#F7B7D2','#B9E7D0','#D7C2F3','#BDE3F7','#FFF4D7'];
const renderEnv = renderSpec?.environment || {{}};
scene.background = new THREE.Color(renderEnv.background_hex || palette[3] || '#BDE3F7');
scene.fog = new THREE.Fog(
  new THREE.Color(renderEnv.fog_hex || renderEnv.background_hex || palette[3] || '#BDE3F7'),
  renderEnv.fog_near || 55,
  renderEnv.fog_far || 95
);

const camera = new THREE.PerspectiveCamera(
  cameraSettings.fov_degrees || 48,
  1,
  cameraSettings.near || .1,
  cameraSettings.far || 180
);
camera.zoom = cameraSettings.zoom || 1;
camera.filmGauge = cameraSettings.film_gauge_mm || 35;
camera.updateProjectionMatrix();

function addRenderLight(spec) {{
  const intensityScale = renderEnv.environment_intensity ?? 1;
  let light = null;
  if (spec.kind === 'ambient') {{
    light = new THREE.AmbientLight(spec.color_hex || '#FFFFFF', (spec.intensity || 1) * intensityScale);
  }} else if (spec.kind === 'point') {{
    light = new THREE.PointLight(spec.color_hex || '#FFFFFF', (spec.intensity || 1) * intensityScale, 0);
  }} else if (spec.kind === 'directional') {{
    light = new THREE.DirectionalLight(spec.color_hex || '#FFFFFF', (spec.intensity || 1) * intensityScale);
    const target = new THREE.Object3D();
    target.position.set(spec.target?.x || 0, spec.target?.y || 0, spec.target?.z || 0);
    scene.add(target);
    light.target = target;
  }} else {{
    light = new THREE.HemisphereLight(
      spec.color_hex || '#FFFFFF',
      '#CFC7E8',
      (spec.intensity || 1) * intensityScale
    );
  }}
  light.position.set(spec.position?.x || 0, spec.position?.y || 20, spec.position?.z || 0);
  light.castShadow = Boolean(spec.cast_shadow);
  if (light.shadow) {{
    const shadowSize = renderSettings.shadow_map_size || 2048;
    light.shadow.mapSize.set(shadowSize,shadowSize);
    if (light.shadow.camera) {{
      light.shadow.camera.left = -55; light.shadow.camera.right = 55;
      light.shadow.camera.top = 55; light.shadow.camera.bottom = -55;
    }}
  }}
  scene.add(light);
}}

if (renderSpec?.environment?.lights?.length) {{
  renderSpec.environment.lights.forEach(addRenderLight);
}} else {{
  const hemi = new THREE.HemisphereLight(0xffffff, 0xcfc7e8, 2.3);
  scene.add(hemi);
  const sun = new THREE.DirectionalLight(0xfff4df, 3.2);
  sun.position.set(24, 34, 18);
  sun.castShadow = true;
  const shadowSize = renderSettings.shadow_map_size || 2048;
  sun.shadow.mapSize.set(shadowSize, shadowSize);
  sun.shadow.camera.left = -55; sun.shadow.camera.right = 55;
  sun.shadow.camera.top = 55; sun.shadow.camera.bottom = -55;
  scene.add(sun);
}}

const world = new THREE.Group();
scene.add(world);

function mat(color, rough=.82) {{
  return new THREE.MeshStandardMaterial({{
    color:new THREE.Color(color),
    roughness:rough,
    metalness:0.02
  }});
}}

const cell = bp.grid.cell_size || 1;
const cw = bp.grid.chunk_width * cell;
const cd = bp.grid.chunk_depth * cell;

function addToyTree(x, z, index=0) {{
  const g = new THREE.Group();
  const trunk = new THREE.Mesh(new THREE.BoxGeometry(.7, 2.2, .7), mat('#E8C9A8'));
  trunk.position.y = 1.1; trunk.castShadow = true; g.add(trunk);
  const crown = new THREE.Mesh(
    new THREE.BoxGeometry(2.5, 2.2, 2.5),
    mat(palette[(index+1) % palette.length])
  );
  crown.position.y = 3.0; crown.castShadow = true; g.add(crown);
  g.position.set(x, 0, z); world.add(g);
}}

function addToyHouse(x, z, index=0) {{
  const g = new THREE.Group();
  const base = new THREE.Mesh(
    new THREE.BoxGeometry(3.6, 2.8, 3.4),
    mat(palette[(index+2) % palette.length])
  );
  base.position.y = 1.4; base.castShadow = true; base.receiveShadow = true; g.add(base);
  const roof = new THREE.Mesh(
    new THREE.ConeGeometry(3.1, 1.8, 4),
    mat(palette[(index+4) % palette.length])
  );
  roof.position.y = 3.7; roof.rotation.y = Math.PI/4; roof.castShadow = true; g.add(roof);
  const door = new THREE.Mesh(new THREE.BoxGeometry(.9, 1.45, .18), mat('#FFF4D7'));
  door.position.set(0,.75,1.79); g.add(door);
  g.position.set(x,0,z); world.add(g);
}}

function addToyRock(x, z, index=0) {{
  const rock = new THREE.Mesh(
    new THREE.DodecahedronGeometry(1.15 + (index%3)*.18, 0),
    mat(palette[(index+3) % palette.length])
  );
  rock.scale.y = .7; rock.position.set(x,.7,z); rock.castShadow = true; rock.receiveShadow = true;
  world.add(rock);
}}

function addFlowerPatch(x, z, index=0) {{
  const g = new THREE.Group();
  for (let i=0; i<5; i++) {{
    const a = (i / 5) * Math.PI * 2;
    const stem = new THREE.Mesh(new THREE.BoxGeometry(.08,.55,.08), mat('#9FD5A8'));
    stem.position.set(Math.cos(a)*.55,.28,Math.sin(a)*.55);
    g.add(stem);
    const bloom = new THREE.Mesh(
      new THREE.BoxGeometry(.34,.22,.34),
      mat(palette[(index+i) % palette.length])
    );
    bloom.position.set(Math.cos(a)*.55,.62,Math.sin(a)*.55);
    bloom.rotation.y = a;
    bloom.castShadow = true;
    g.add(bloom);
  }}
  const center = new THREE.Mesh(new THREE.BoxGeometry(.28,.2,.28), mat('#FFF4A8'));
  center.position.y=.62; g.add(center);
  g.position.set(x,0,z); world.add(g);
}}

function addCloud(x, y, z, scale=1) {{
  const g = new THREE.Group();
  [[0,0,0,1.4],[1.0,.15,.1,1.0],[-1.0,.1,.05,.9],[.35,.5,0,.85]].forEach(p => {{
    const puff = new THREE.Mesh(
      new THREE.SphereGeometry(p[3], 12, 8),
      new THREE.MeshStandardMaterial({{color:0xffffff, roughness:.95, transparent:true, opacity:.92}})
    );
    puff.position.set(p[0],p[1],p[2]); g.add(puff);
  }});
  g.position.set(x,y,z); g.scale.setScalar(scale); world.add(g);
}}

function addStarLamp(x, z, index=0) {{
  const g = new THREE.Group();
  const pole = new THREE.Mesh(new THREE.BoxGeometry(.2,1.8,.2), mat('#FFF4D7'));
  pole.position.y=.9; g.add(pole);
  const orb = new THREE.Mesh(
    new THREE.OctahedronGeometry(.45,0),
    new THREE.MeshStandardMaterial({{
      color:new THREE.Color(palette[index % palette.length]),
      emissive:new THREE.Color(palette[index % palette.length]),
      emissiveIntensity:1.1,
      roughness:.4
    }})
  );
  orb.position.y=2.05; g.add(orb);
  g.position.set(x,0,z); world.add(g);
}}

function decorateChunk(chunk, i, centerX, centerZ) {{
  const biome = (chunk.biome || '').toLowerCase();
  const worldType = (profile.world_type || '').toLowerCase();
  const worldName = (profile.world_name || DATA.worldName || '').toLowerCase();
  const gardenLike = biome.includes('forest') || worldType.includes('forest') || worldType.includes('garden') || worldName.includes('garden') || anchorText.includes('garden') || anchorText.includes('forest');
  if (gardenLike) {{
    addToyTree(centerX-2.6, centerZ+2.2, i);
    addToyTree(centerX+2.3, centerZ-1.8, i+1);
    addFlowerPatch(centerX+2.4, centerZ+2.4, i);
    if ((i % 3) === 0) addToyHouse(centerX-.3, centerZ-.2, i);
  }} else if (worldType.includes('village') || worldType.includes('city') || worldType.includes('harbor')) {{
    addToyHouse(centerX, centerZ, i);
    addStarLamp(centerX-3.2, centerZ+2.6, i);
  }} else {{
    addToyRock(centerX-2.2, centerZ+1.8, i);
    if ((i % 2) === 0) addStarLamp(centerX+2.2, centerZ-2.0, i);
  }}
}}

const semanticElevatedTerrain = (bp.layout_elements || []).some(element =>
  element.kind === 'terrain' &&
  ['floating','aerial','suspended'].includes(element.spatial_mode || '')
);
const floatingWorld =
  semanticElevatedTerrain ||
  (profile.world_type || '').toLowerCase().includes('floating') ||
  anchorText.includes('floating');

// Grounded worlds keep the classic chunk quilt. Semantic floating/aerial worlds
// are built from Scene elements instead, so a 25-tile ground plane does not
// overwrite the creator's vertical composition.
if (!semanticElevatedTerrain) {{
  (bp.chunks || []).forEach((chunk, i) => {{
    const color = palette[i % palette.length];
    const geo = new THREE.BoxGeometry(cw - .18, .8, cd - .18);
    const mesh = new THREE.Mesh(geo, mat(color));
    mesh.position.set(chunk.chunk_x * cw + cw/2, -.4, chunk.chunk_z * cd + cd/2);
    mesh.receiveShadow = true;
    world.add(mesh);
    decorateChunk(chunk, i, mesh.position.x, mesh.position.z);
  }});
}}

if (floatingWorld) {{
  addCloud(7, 11, 9, 1.1);
  addCloud(39, 15, 14, .8);
  addCloud(31, 12, 43, 1.0);
  addCloud(14, 16, 36, .7);
}}

function applySemanticOrientation(object, orientation) {{
  if (orientation === 'inverted') object.rotation.z = Math.PI;
  else if (orientation === 'vertical') object.rotation.x = Math.PI / 2;
  else if (orientation === 'tilted') object.rotation.z = Math.PI / 7;
}}

function semanticMaterial(index, transparent=false) {{
  const color = palette[(index+3) % palette.length] || '#BDE3F7';
  return new THREE.MeshStandardMaterial({{
    color:new THREE.Color(color),
    transparent,
    opacity: transparent ? .72 : 1,
    roughness:.3,
    metalness:.03,
    emissive:new THREE.Color(color),
    emissiveIntensity: transparent ? .13 : .04
  }});
}}

function addSemanticLabel(text, x, y, z) {{
  if (!text) return;
  const canvas = document.createElement('canvas');
  canvas.width = 512; canvas.height = 96;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0,0,canvas.width,canvas.height);
  ctx.fillStyle = 'rgba(255,255,255,.92)';
  ctx.strokeStyle = 'rgba(75,67,105,.18)';
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.roundRect(8,10,496,76,22);
  ctx.fill(); ctx.stroke();
  ctx.fillStyle = '#34334c';
  ctx.font = '700 28px sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  const clean = String(text).slice(0,30);
  ctx.fillText(clean, 256, 49);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const sprite = new THREE.Sprite(
    new THREE.SpriteMaterial({{map:texture, transparent:true, depthTest:false}})
  );
  sprite.scale.set(7.2,1.35,1);
  sprite.position.set(x,y,z);
  sprite.renderOrder = 30;
  world.add(sprite);
}}

const compiledMaterialCache = new Map();

function renderSide(name) {{
  if (name === 'double') return THREE.DoubleSide;
  if (name === 'back') return THREE.BackSide;
  return THREE.FrontSide;
}}

function compiledMaterial(spec) {{
  if (!spec) return mat('#FFF4D7');
  if (compiledMaterialCache.has(spec.material_id)) {{
    return compiledMaterialCache.get(spec.material_id);
  }}
  const params = {{
    color: new THREE.Color(spec.color_hex || '#FFF4D7'),
    roughness: spec.roughness ?? .72,
    metalness: spec.metalness ?? 0,
    emissive: new THREE.Color(spec.emissive_hex || '#000000'),
    emissiveIntensity: spec.emissive_intensity ?? 0,
    opacity: spec.opacity ?? 1,
    transparent: Boolean(spec.transparent),
    alphaTest: spec.alpha_test ?? 0,
    side: renderSide(spec.side),
    vertexColors: Boolean(spec.vertex_colors),
  }};
  const material = spec.model === 'toon'
    ? new THREE.MeshToonMaterial({{
        color: params.color,
        opacity: params.opacity,
        transparent: params.transparent,
        alphaTest: params.alphaTest,
        side: params.side,
        vertexColors: params.vertexColors,
      }})
    : new THREE.MeshStandardMaterial(params);
  compiledMaterialCache.set(spec.material_id, material);
  return material;
}}

function bufferGeometryFromSpec(buffer) {{
  const geometry = new THREE.BufferGeometry();
  if (buffer?.positions?.length) {{
    geometry.setAttribute(
      'position',
      new THREE.Float32BufferAttribute(buffer.positions, 3)
    );
  }}
  if (buffer?.indices?.length) geometry.setIndex(buffer.indices);
  if (buffer?.normals?.length) {{
    geometry.setAttribute(
      'normal',
      new THREE.Float32BufferAttribute(buffer.normals, 3)
    );
  }} else if (buffer?.positions?.length) {{
    geometry.computeVertexNormals();
  }}
  if (buffer?.uvs?.length) {{
    geometry.setAttribute('uv', new THREE.Float32BufferAttribute(buffer.uvs, 2));
  }}
  if (buffer?.colors?.length) {{
    geometry.setAttribute(
      'color',
      new THREE.Float32BufferAttribute(buffer.colors, 3)
    );
  }}
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();
  return geometry;
}}

function wedgeGeometry() {{
  const geometry = new THREE.BufferGeometry();
  const positions = new Float32Array([
    -.5,-.5,-.5,  .5,-.5,-.5,  -.5,.5,-.5,
    -.5,-.5,.5,   .5,-.5,.5,   -.5,.5,.5
  ]);
  const indices = [
    0,1,2,
    3,5,4,
    0,3,4, 0,4,1,
    0,2,5, 0,5,3,
    1,4,5, 1,5,2,
    2,1,4, 2,4,5
  ];
  geometry.setAttribute('position', new THREE.BufferAttribute(positions,3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}}

function primitiveGeometry(spec) {{
  const size = spec.primitive_size || {{x:1,y:1,z:1}};
  const primitive = spec.primitive || 'box';
  let geometry;
  const baseScale = new THREE.Vector3(1,1,1);

  if (spec.source_type === 'buffer' && spec.buffer?.positions?.length) {{
    return {{geometry: bufferGeometryFromSpec(spec.buffer), baseScale}};
  }}

  if (primitive === 'sphere' || primitive === 'ellipsoid') {{
    geometry = new THREE.SphereGeometry(.5, 28, 20);
    baseScale.set(size.x || 1, size.y || 1, size.z || 1);
  }} else if (primitive === 'capsule') {{
    geometry = new THREE.CapsuleGeometry(.35,.30,8,18);
    baseScale.set(
      (size.x || 1) / .70,
      size.y || 1,
      (size.z || 1) / .70
    );
  }} else if (primitive === 'hemisphere' || primitive === 'dome') {{
    geometry = new THREE.SphereGeometry(.5,28,14,0,Math.PI*2,0,Math.PI/2);
    geometry.translate(0,-.22,0);
    baseScale.set(size.x || 1, size.y || 1, size.z || 1);
  }} else if (primitive === 'cylinder') {{
    geometry = new THREE.CylinderGeometry(.5,.5,1,24);
    baseScale.set(size.x || 1, size.y || 1, size.z || 1);
  }} else if (primitive === 'cone') {{
    geometry = new THREE.ConeGeometry(.5,1,24);
    baseScale.set(size.x || 1, size.y || 1, size.z || 1);
  }} else if (primitive === 'tapered_box') {{
    geometry = new THREE.CylinderGeometry(.34,.5,1,4,1,false);
    geometry.rotateY(Math.PI/4);
    baseScale.set(size.x || 1, size.y || 1, size.z || 1);
  }} else if (primitive === 'wedge') {{
    geometry = wedgeGeometry();
    baseScale.set(size.x || 1, size.y || 1, size.z || 1);
  }} else if (primitive === 'disc') {{
    geometry = new THREE.CylinderGeometry(.5,.5,.12,28);
    baseScale.set(size.x || 1, (size.y || 1) / .12, size.z || 1);
  }} else if (primitive === 'torus' || primitive === 'ring') {{
    geometry = new THREE.TorusGeometry(
      primitive === 'ring' ? .40 : .34,
      primitive === 'ring' ? .07 : .12,
      14,
      36
    );
    baseScale.set(size.x || 1, size.y || 1, size.z || 1);
  }} else if (primitive === 'plane') {{
    geometry = new THREE.PlaneGeometry(1,1);
    geometry.rotateX(-Math.PI/2);
    baseScale.set(size.x || 1, size.z || 1, Math.max(.04,size.y || .08));
  }} else if (primitive === 'arch') {{
    geometry = new THREE.TorusGeometry(.36,.11,14,36,Math.PI);
    geometry.rotateZ(Math.PI);
    baseScale.set(size.x || 1, size.y || 1, size.z || 1);
  }} else if (primitive === 'rounded_box' || primitive === 'voxel_cluster') {{
    geometry = new RoundedBoxGeometry(1,1,1,4,primitive === 'voxel_cluster' ? .06 : .12);
    baseScale.set(size.x || 1, size.y || 1, size.z || 1);
  }} else {{
    geometry = new THREE.BoxGeometry(1,1,1);
    baseScale.set(size.x || 1, size.y || 1, size.z || 1);
  }}
  return {{geometry, baseScale}};
}}

function applyNodeTransform(group, node) {{
  const p = node.local_position || {{}};
  const q = node.local_quaternion || {{}};
  const s = node.local_scale || {{}};
  group.position.set(p.x || 0, p.y || 0, p.z || 0);
  group.quaternion.set(q.x || 0, q.y || 0, q.z || 0, q.w ?? 1);
  group.scale.set(s.x ?? 1, s.y ?? 1, s.z ?? 1);
}}

function dominantHorizontalAxis(size) {{
  const x = Math.max(.001, size.x || 0);
  const z = Math.max(.001, size.z || 0);
  const ratio = Math.min(x, z) / Math.max(x, z);
  if (ratio > .88) return 'balanced';
  return x >= z ? 'x' : 'z';
}}

function fitHeroGLBToEnvelope(model, element) {{
  if (!model || !element) return null;

  // Provider GLBs can arrive with arbitrary world units, pivots and with the
  // long horizontal axis on either X or Z. Normalize those before fitting the
  // authoritative Blueprint envelope.
  model.updateMatrixWorld(true);
  let bounds = new THREE.Box3().setFromObject(model);
  const nativeSize = bounds.getSize(new THREE.Vector3());
  const target = new THREE.Vector3(
    Math.max(.1, element.width || 1),
    Math.max(.1, element.height || 1),
    Math.max(.1, element.depth || 1)
  );

  const nativeAxis = dominantHorizontalAxis(nativeSize);
  const targetAxis = dominantHorizontalAxis(
    new THREE.Vector3(target.x, 0, target.z)
  );
  let axisRotationDegrees = 0;

  if (
    nativeAxis !== 'balanced'
    && targetAxis !== 'balanced'
    && nativeAxis !== targetAxis
  ) {{
    model.rotation.y += Math.PI / 2;
    axisRotationDegrees = 90;
    model.updateMatrixWorld(true);
    bounds = new THREE.Box3().setFromObject(model);
  }}

  const orientedSize = bounds.getSize(new THREE.Vector3());
  const sx = target.x / Math.max(.001, orientedSize.x);
  const sy = target.y / Math.max(.001, orientedSize.y);
  const sz = target.z / Math.max(.001, orientedSize.z);
  const fitScale = Math.min(sx, sy, sz) * .96;
  model.scale.multiplyScalar(fitScale);
  model.updateMatrixWorld(true);

  // Canonical Hero pivot = horizontal center + bottom anchor. This makes the
  // Blueprint element position a stable support/base elevation regardless of
  // where Pixal3D placed its native origin.
  bounds = new THREE.Box3().setFromObject(model);
  const center = bounds.getCenter(new THREE.Vector3());
  model.position.x -= center.x;
  model.position.z -= center.z;
  model.position.y -= bounds.min.y;
  model.updateMatrixWorld(true);

  const finalBounds = new THREE.Box3().setFromObject(model);
  const finalSize = finalBounds.getSize(new THREE.Vector3());
  return {{
    native_axis: nativeAxis,
    target_axis: targetAxis,
    axis_rotation_degrees: axisRotationDegrees,
    uniform_scale: fitScale,
    native_size: {{x:nativeSize.x, y:nativeSize.y, z:nativeSize.z}},
    oriented_size: {{x:orientedSize.x, y:orientedSize.y, z:orientedSize.z}},
    target_size: {{x:target.x, y:target.y, z:target.z}},
    final_size: {{x:finalSize.x, y:finalSize.y, z:finalSize.z}},
    pivot: 'bottom_center',
  }};
}}

function loadHeroGLBNode({{node, spec, objectGroup, fallbackGroups}}) {{
  const geometry = node.geometry || {{}};
  const assetPath = geometry.asset_path || '';
  const assetUrl = renderAssets[assetPath];
  if (!assetPath || !assetUrl) return false;

  const holder = new THREE.Group();
  applyNodeTransform(holder, node);
  holder.visible = node.visible !== false;
  objectGroup.add(holder);

  gltfLoader.load(
    assetUrl,
    gltf => {{
      const model = gltf.scene;
      model.traverse(child => {{
        if (!child.isMesh) return;
        child.castShadow = node.cast_shadow !== false;
        child.receiveShadow = node.receive_shadow !== false;
        child.frustumCulled = spec.frustum_culled !== false;
      }});
      const normalization = fitHeroGLBToEnvelope(
        model,
        layoutById.get(spec.element_id)
      );
      holder.add(model);
      fallbackGroups.forEach(group => {{ group.visible = false; }});
      objectGroup.userData.heroAssetLoaded = true;
      objectGroup.userData.heroAssetPath = assetPath;
      objectGroup.userData.heroSpatialNormalization = normalization;
    }},
    undefined,
    error => {{
      console.warn(
        'Hero GLB failed; keeping procedural fallback',
        spec.element_id,
        assetPath,
        error
      );
      holder.removeFromParent();
      objectGroup.userData.heroAssetLoaded = false;
    }}
  );
  return true;
}}

function addCompiledRenderObject(spec) {{
  if (!spec || spec.kind === 'portal') return false;
  const objectGroup = new THREE.Group();
  const nodeGroups = new Map();
  const fallbackGroups = [];
  const glbNodes = [];
  const materialById = new Map(
    (renderSpec?.materials || []).map(item => [item.material_id, item])
  );

  (spec.nodes || []).forEach(node => {{
    if (node.geometry?.source_type === 'glb') {{
      glbNodes.push(node);
      return;
    }}

    const built = primitiveGeometry(node.geometry || {{}});
    const material = compiledMaterial(materialById.get(node.material_id));
    const mesh = new THREE.Mesh(built.geometry, material);
    mesh.scale.copy(built.baseScale);
    mesh.castShadow = node.cast_shadow !== false;
    mesh.receiveShadow = node.receive_shadow !== false;
    mesh.visible = node.visible !== false;
    mesh.renderOrder = node.render_order || 0;
    mesh.frustumCulled = spec.frustum_culled !== false;

    const group = new THREE.Group();
    applyNodeTransform(group, node);
    group.add(mesh);
    fallbackGroups.push(group);
    nodeGroups.set(node.node_id, {{group, parent: node.parent_node_id || ''}});
  }});

  // RenderSpec v0.2 mesh-node transforms are all object-local.
  nodeGroups.forEach(entry => objectGroup.add(entry.group));

  const transform = spec.transform || {{}};
  const p = transform.position || {{}};
  const q = transform.quaternion || {{}};
  const s = transform.scale || {{}};
  objectGroup.position.set(p.x || 0, p.y || 0, p.z || 0);
  objectGroup.quaternion.set(q.x || 0, q.y || 0, q.z || 0, q.w ?? 1);
  objectGroup.scale.set(s.x ?? 1, s.y ?? 1, s.z ?? 1);
  objectGroup.visible = spec.visible !== false;
  objectGroup.renderOrder = spec.render_order || 0;
  objectGroup.layers.set(spec.layer || 0);
  objectGroup.userData.elementId = spec.element_id;
  objectGroup.userData.semanticKey = spec.semantic_key || '';
  objectGroup.userData.traversability = spec.traversability || 'scenic';
  world.add(objectGroup);

  glbNodes.forEach(node => loadHeroGLBNode({{
    node,
    spec,
    objectGroup,
    fallbackGroups,
  }}));

  return true;
}}

function addSemanticElement(element, index) {{
  if (!element || element.kind === 'portal') return;

  const role = element.geometry_role || 'volume';
  const spatialMode = element.spatial_mode || 'grounded';
  const y = element.position?.y || 0;
  const width = Math.max(1.2, element.width || 5);
  const depth = Math.max(1.2, element.depth || 5);
  const height = Math.max(.6, element.height || 4);
  const g = new THREE.Group();
  let labelHeight = height + 2.0;

  if (element.kind === 'water') {{
    if (role === 'vertical_flow') {{
      const flow = new THREE.Mesh(
        new THREE.BoxGeometry(width, Math.max(4,height), Math.max(1.2,depth)),
        semanticMaterial(index,true)
      );
      flow.position.y = Math.max(4,height) / 2;
      flow.castShadow = true;
      g.add(flow);
      labelHeight = Math.max(4,height) + 2;
    }} else {{
      const water = new THREE.Mesh(
        new THREE.CylinderGeometry(
          Math.max(width,depth) * .5,
          Math.max(width,depth) * .5,
          .16,
          36
        ),
        semanticMaterial(index,true)
      );
      water.scale.z = Math.max(.35, depth / Math.max(width,depth));
      water.position.y = .05;
      water.receiveShadow = true;
      g.add(water);
      labelHeight = 1.6;
    }}
  }} else if (role === 'terrain_mass' || element.kind === 'terrain') {{
    const mass = new THREE.Mesh(
      new THREE.BoxGeometry(width, height, depth),
      semanticMaterial(index,false)
    );
    mass.position.y = height / 2;
    mass.castShadow = true; mass.receiveShadow = true; g.add(mass);
    if (['floating','aerial','suspended'].includes(spatialMode)) {{
      const underside = new THREE.Mesh(
        new THREE.CylinderGeometry(
          Math.max(1.1,width*.31),
          Math.max(.5,width*.10),
          Math.max(2.4,height*.75),
          6
        ),
        mat('#D9CBE8')
      );
      underside.position.y = -Math.max(1.3,height*.34);
      underside.castShadow = true; g.add(underside);
    }}
  }} else if (
    role === 'organic' ||
    (
      role === 'volume' &&
      element.kind === 'landmark' &&
      ['floating','aerial','suspended'].includes(spatialMode)
    )
  ) {{
    // Generic soft-body proxy for organic subjects and legacy aerial volume
    // landmarks. This is semantic fallback, not an object-name special case.
    const body = new THREE.Mesh(
      new THREE.SphereGeometry(1,24,16),
      semanticMaterial(index,false)
    );
    body.scale.set(width*.52, height*.42, depth*.52);
    body.position.y = height*.5;
    body.castShadow = true; body.receiveShadow = true; g.add(body);

    const secondary = new THREE.Mesh(
      new THREE.SphereGeometry(1,18,12),
      semanticMaterial(index+1,false)
    );
    secondary.scale.set(width*.22,height*.22,depth*.30);
    secondary.position.set(width*.42,height*.55,0);
    secondary.castShadow = true; g.add(secondary);

    const appendage = new THREE.Mesh(
      new THREE.ConeGeometry(Math.max(.6,depth*.20), Math.max(1.5,width*.34), 5),
      semanticMaterial(index+2,false)
    );
    appendage.rotation.z = Math.PI/2;
    appendage.position.set(-width*.48,height*.48,0);
    appendage.castShadow = true; g.add(appendage);
  }} else if (role === 'platform') {{
    const deck = new THREE.Mesh(
      new THREE.BoxGeometry(width, Math.max(.5,height*.18), depth),
      semanticMaterial(index,false)
    );
    deck.position.y = Math.max(.25,height*.09);
    deck.castShadow=true; deck.receiveShadow=true; g.add(deck);
    const rail = new THREE.Mesh(
      new THREE.BoxGeometry(Math.max(1,width*.88),.3,.3),
      semanticMaterial(index+1,false)
    );
    rail.position.set(0,1.05,-depth*.42);
    rail.castShadow=true; g.add(rail);
    labelHeight = 2.6;
  }} else if (role === 'bridge' || element.kind === 'bridge') {{
    const deck = new THREE.Mesh(
      new THREE.BoxGeometry(width, Math.max(.35,height*.25), depth),
      semanticMaterial(index,false)
    );
    deck.position.y = Math.max(.3,height*.14);
    deck.castShadow=true; deck.receiveShadow=true; g.add(deck);
    [-.42,.42].forEach(k => {{
      const rail = new THREE.Mesh(
        new THREE.BoxGeometry(width,.35,.24),
        semanticMaterial(index+1,false)
      );
      rail.position.set(0,1.0,depth*k);
      rail.castShadow=true; g.add(rail);
    }});
    labelHeight = 2.5;
  }} else if (role === 'path') {{
    const path = new THREE.Mesh(
      new THREE.BoxGeometry(width,.22,depth),
      semanticMaterial(index,false)
    );
    path.position.y=.11; path.receiveShadow=true; g.add(path);
    labelHeight = 1.4;
  }} else if (role === 'decorative' || element.kind === 'decoration') {{
    const deco = new THREE.Mesh(
      new THREE.OctahedronGeometry(Math.max(.65,width*.28),0),
      semanticMaterial(index,false)
    );
    deco.position.y = Math.max(.8,height*.5);
    deco.castShadow=true; g.add(deco);
    labelHeight = Math.max(1.8,height+1);
  }} else {{
    // Generic built/artificial volume uses its actual Blueprint dimensions.
    const base = new THREE.Mesh(
      new THREE.BoxGeometry(width,height,depth),
      semanticMaterial(index,false)
    );
    base.position.y = height/2;
    base.castShadow=true; base.receiveShadow=true; g.add(base);
  }}

  applySemanticOrientation(g, element.orientation || 'normal');
  g.position.set(element.position.x,y,element.position.z);
  g.userData.label = element.name;
  world.add(g);

  if (
    element.kind !== 'decoration' &&
    role !== 'decorative' &&
    role !== 'path'
  ) {{
    addSemanticLabel(
      element.name,
      element.position.x,
      y + labelHeight,
      element.position.z
    );
  }}
}}

const compiledElementIds = new Set();
if (renderSpec?.objects?.length) {{
  (renderSpec.objects || []).forEach(spec => {{
    if (addCompiledRenderObject(spec)) compiledElementIds.add(spec.element_id);
  }});
}}
(bp.layout_elements || []).forEach((element,index) => {{
  if (!compiledElementIds.has(element.element_id)) addSemanticElement(element,index);
}});

(bp.paths || []).forEach((path, pathIndex) => {{
  const points = path.points || [];
  for (let i=0; i<points.length-1; i++) {{
    const a = points[i], b = points[i+1];
    const dx = b.x-a.x, dy=(b.y||0)-(a.y||0), dz = b.z-a.z;
    const horizontal = Math.hypot(dx,dz);
    const length = Math.hypot(dx,dy,dz);
    if (length < .01) continue;
    const walkway = new THREE.Mesh(
      new THREE.BoxGeometry(path.width_cells || 2.0, .14, length),
      mat(pathIndex % 2 ? '#FFF4D7' : '#FFE5EF')
    );
    walkway.position.set(
      (a.x+b.x)/2,
      ((a.y||0)+(b.y||0))/2 + .08,
      (a.z+b.z)/2
    );
    walkway.rotation.y = Math.atan2(dx,dz);
    walkway.rotation.x = -Math.atan2(dy, Math.max(.001, horizontal));
    walkway.receiveShadow = true;
    world.add(walkway);
  }}
}});

function addLandmark(spec, index) {{
  const g = new THREE.Group();
  const c1 = palette[(index + 1) % palette.length];
  const c2 = palette[(index + 3) % palette.length];
  const role = spec.geometry_role || ((spec.kind || '').toLowerCase() === 'bridge' ? 'bridge' : 'volume');

  if (role === 'bridge' || (spec.kind || '').toLowerCase() === 'bridge') {{
    const deck = new THREE.Mesh(new THREE.BoxGeometry(8.5,.55,2.4), mat(c1));
    deck.position.y=.85; deck.castShadow=true; deck.receiveShadow=true; g.add(deck);
    [-3.5,3.5].forEach(x => {{
      const post = new THREE.Mesh(new THREE.BoxGeometry(.35,1.7,.35), mat(c2));
      post.position.set(x,1.55,0); post.castShadow=true; g.add(post);
    }});
  }} else if (role === 'organic') {{
    const body = new THREE.Mesh(new THREE.SphereGeometry(3.4, 24, 16), mat(c1));
    body.scale.set(1.55,.72,.88);
    body.position.y=2.8; body.castShadow=true; body.receiveShadow=true; g.add(body);
    const top = new THREE.Mesh(new THREE.BoxGeometry(5.2,.7,3.8), mat(c2));
    top.position.y=5.1; top.castShadow=true; top.receiveShadow=true; g.add(top);
  }} else if (role === 'platform') {{
    const deck = new THREE.Mesh(new THREE.BoxGeometry(6.8,.8,6.0), mat(c1));
    deck.position.y=.4; deck.castShadow=true; deck.receiveShadow=true; g.add(deck);
    const rail = new THREE.Mesh(new THREE.BoxGeometry(6.3,.35,.35), mat(c2));
    rail.position.set(0,1.1,-2.7); rail.castShadow=true; g.add(rail);
  }} else {{
    const base = new THREE.Mesh(new THREE.BoxGeometry(4.4, 1.2, 4.4), mat(c1));
    base.position.y = .6; base.castShadow = true; base.receiveShadow = true;
    g.add(base);
    const tower = new THREE.Mesh(new THREE.BoxGeometry(2.6, 5.2, 2.6), mat(c2));
    tower.position.y = 3.2; tower.castShadow = true; g.add(tower);
    const cap = new THREE.Mesh(new THREE.SphereGeometry(1.8, 16, 10), mat(c1));
    cap.scale.y = .7; cap.position.y = 6.0; cap.castShadow = true; g.add(cap);
  }}

  applySemanticOrientation(g, spec.orientation || 'normal');
  g.position.set(spec.position.x, spec.position.y || 0, spec.position.z);
  g.userData.label = spec.name;
  world.add(g);
}}
// Legacy Blueprints without layout_elements still use LandmarkSpec proxies.
if (!(bp.layout_elements || []).length) {{
  (bp.landmarks || []).forEach(addLandmark);
}}

if (bp.portal) {{
  const portal = new THREE.Group();
  const portalColor = palette[2] || '#D7C2F3';
  const portalMat = new THREE.MeshStandardMaterial({{
    color:new THREE.Color(portalColor),
    emissive:new THREE.Color(portalColor),
    emissiveIntensity:1.4,
    roughness:.35
  }});
  const portalForm = (
    bp.portal.form || profile.portal_form || visualAnchor.must_preserve?.join(' ') || ''
  ).toLowerCase();

  if (portalForm.includes('star')) {{
    const shape = new THREE.Shape();
    const outer=2.75, inner=1.28, points=5;
    for (let i=0;i<points*2;i++) {{
      const r = i%2===0 ? outer : inner;
      const angle = -Math.PI/2 + i*Math.PI/points;
      const x = Math.cos(angle)*r, y = Math.sin(angle)*r;
      if (i===0) shape.moveTo(x,y); else shape.lineTo(x,y);
    }}
    shape.closePath();
    const hole = new THREE.Path();
    hole.absellipse(0,0,1.05,1.05,0,Math.PI*2,false,0);
    shape.holes.push(hole);
    const star = new THREE.Mesh(new THREE.ExtrudeGeometry(shape, {{depth:.38, bevelEnabled:true, bevelSize:.12, bevelThickness:.10, bevelSegments:2}}), portalMat);
    star.position.set(0,3.0,-.18);
    star.castShadow = true;
    portal.add(star);
  }} else {{
    const ring = new THREE.Mesh(new THREE.TorusGeometry(2.3,.42,14,36), portalMat);
    ring.rotation.y = Math.PI/2;
    ring.position.y = 3.0;
    ring.castShadow = true;
    portal.add(ring);
  }}
  const glow = new THREE.PointLight(palette[2] || '#D7C2F3', 12, 12);
  glow.position.y = 3.0; portal.add(glow);
  portal.position.set(bp.portal.position.x, bp.portal.position.y || 0, bp.portal.position.z);
  world.add(portal);
  addSemanticLabel(
    bp.portal.form || profile.portal_form || 'Portal',
    bp.portal.position.x,
    (bp.portal.position.y || 0) + 7.2,
    bp.portal.position.z
  );
}}

function makeAvatar() {{
  const g = new THREE.Group();
  const bodyColor = characterRuntime.body_color_hex || '#FFF4D7';
  const accentColor = characterRuntime.accent_color_hex || '#B9E7D0';
  const hairColor = characterRuntime.hair_color_hex || '#5B4036';
  const eyeColor = characterRuntime.eye_color_hex || '#7A5238';

  const body = new THREE.Mesh(new THREE.BoxGeometry(1.1, 1.35, .82), mat(bodyColor));
  body.position.y = 1.18; body.castShadow = true; g.add(body);

  const head = new THREE.Mesh(new THREE.BoxGeometry(1.78, 1.62, 1.52), mat('#F7E7D9'));
  head.position.y = 2.58; head.castShadow = true; g.add(head);

  const hair = new THREE.Mesh(new THREE.BoxGeometry(1.88, .72, 1.58), mat(hairColor));
  hair.position.set(0,3.13,-.02); hair.castShadow = true; g.add(hair);

  const eyeGeo = new THREE.BoxGeometry(.22,.27,.12);
  const eyeMat = mat(eyeColor,.55);
  const le = new THREE.Mesh(eyeGeo, eyeMat); le.position.set(-.38,2.64,.79); g.add(le);
  const re = new THREE.Mesh(eyeGeo, eyeMat); re.position.set(.38,2.64,.79); g.add(re);

  const armGeo = new THREE.BoxGeometry(.34,1.05,.34);
  const armMat = mat(accentColor);
  const la = new THREE.Mesh(armGeo, armMat); la.position.set(-.75,1.25,0); la.castShadow=true; g.add(la);
  const ra = new THREE.Mesh(armGeo, armMat); ra.position.set(.75,1.25,0); ra.castShadow=true; g.add(ra);

  const footGeo = new THREE.BoxGeometry(.58, .4, .92);
  const footMat = mat('#F6F7FB');
  const lf = new THREE.Mesh(footGeo, footMat); lf.position.set(-.36,.25,.08); lf.castShadow=true; g.add(lf);
  const rf = new THREE.Mesh(footGeo, footMat); rf.position.set(.36,.25,.08); rf.castShadow=true; g.add(rf);

  g.userData.characterName = DATA.characterName || 'Mini Traveler';
  g.userData.parts = {{ body, head, la, ra, lf, rf }};
  return g;
}}

const player = new THREE.Group();
const proceduralAvatar = makeAvatar();
player.add(proceduralAvatar);
scene.add(player);

let gltfMixer = null;
let gltfActions = {{}};
let activeGltfAction = null;

function findClip(clips, preferredName) {{
  const target = (preferredName || '').toLowerCase();
  return clips.find(clip => clip.name.toLowerCase() === target)
    || clips.find(clip => clip.name.toLowerCase().includes(target));
}}

function playGltfState(state) {{
  if (!gltfMixer) return;
  const clipName = (characterRuntime.animation_clips || {{}})[state.toLowerCase()] || state;
  const next = gltfActions[clipName] || gltfActions[state];
  if (!next || next === activeGltfAction) return;
  if (activeGltfAction) activeGltfAction.fadeOut(.18);
  next.reset().fadeIn(.18).play();
  activeGltfAction = next;
}}

if (characterRuntime.mode === 'glb' && characterRuntime.model_data_uri) {{
  const loader = new GLTFLoader();
  loader.load(characterRuntime.model_data_uri, gltf => {{
    proceduralAvatar.visible = false;
    const model = gltf.scene;
    model.scale.setScalar(characterRuntime.scale || 1);
    model.traverse(obj => {{
      if (obj.isMesh) {{
        obj.castShadow = true;
        obj.receiveShadow = true;
      }}
    }});
    player.add(model);
    gltfMixer = new THREE.AnimationMixer(model);
    const names = characterRuntime.animation_clips || {{}};
    ['Idle','Walk','Run'].forEach(state => {{
      const wanted = names[state.toLowerCase()] || state;
      const clip = findClip(gltf.animations || [], wanted);
      if (clip) {{
        const action = gltfMixer.clipAction(clip);
        gltfActions[wanted] = action;
        gltfActions[state] = action;
      }}
    }});
    playGltfState('Idle');
  }}, undefined, () => {{
    proceduralAvatar.visible = true;
  }});
}}

const spawn = bp.spawn || {{x:6,y:0,z:25,facing_degrees:90}};
function resetPlayer() {{
  player.position.set(spawn.x, (spawn.y || 0) + .02, spawn.z);
  player.rotation.y = THREE.MathUtils.degToRad(-(spawn.facing_degrees || 0));
}}
resetPlayer();

const keys = new Set();
let manualMode = true;
let tourState = null;
let animationState = 'Idle';
let animationTime = 0;

window.addEventListener('keydown', e => {{
  if ([
    'ArrowUp','ArrowDown','ArrowLeft','ArrowRight',
    'KeyW','KeyA','KeyS','KeyD','ShiftLeft','ShiftRight'
  ].includes(e.code)) {{
    if (e.code.startsWith('Arrow')) e.preventDefault();
    if (
      overviewMode &&
      ['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','KeyW','KeyA','KeyS','KeyD'].includes(e.code)
    ) {{
      overviewMode = false;
      updateZoomLabel();
    }}
    keys.add(e.code);
  }}
}});
window.addEventListener('keyup', e => keys.delete(e.code));

const velocity = new THREE.Vector3();
const cameraTarget = new THREE.Vector3();
const clock = new THREE.Clock();

const FOLLOW_TARGET_HEIGHT = 1.8;
const baseFollowDistance = 12.0;
const ZOOM_MIN = .60;
const ZOOM_MAX = 3.80;
const ORBIT_PITCH_MIN = THREE.MathUtils.degToRad(-10);
const ORBIT_PITCH_MAX = THREE.MathUtils.degToRad(72);
const ORBIT_SENSITIVITY = .0052;
const ORBIT_DAMPING = 14.0;
const PLAYER_TURN_DAMPING = 16.0;
const INITIAL_PLAYER_YAW = THREE.MathUtils.degToRad(-(spawn.facing_degrees || 0));
const DEFAULT_ORBIT_YAW = INITIAL_PLAYER_YAW + Math.PI;
const DEFAULT_ORBIT_PITCH = THREE.MathUtils.degToRad(24);
const baseFollowOffset = new THREE.Vector3(
  Math.sin(DEFAULT_ORBIT_YAW) * Math.cos(DEFAULT_ORBIT_PITCH) * baseFollowDistance,
  Math.sin(DEFAULT_ORBIT_PITCH) * baseFollowDistance,
  Math.cos(DEFAULT_ORBIT_YAW) * Math.cos(DEFAULT_ORBIT_PITCH) * baseFollowDistance,
);
const scaledFollowOffset = new THREE.Vector3();
const moveForward = new THREE.Vector3();
const moveRight = new THREE.Vector3();
const moveVector = new THREE.Vector3();
let followZoom = 1.0;
let overviewMode = false;
let overviewDistance = 1;
let orbitYaw = DEFAULT_ORBIT_YAW;
let orbitPitch = DEFAULT_ORBIT_PITCH;
let targetOrbitYaw = DEFAULT_ORBIT_YAW;
let targetOrbitPitch = DEFAULT_ORBIT_PITCH;
let orbitDragging = false;
let orbitPointerId = null;
let orbitPointerX = 0;
let orbitPointerY = 0;

const layoutTopY = Math.max(
  0,
  ...(bp.layout_elements || []).map(element =>
    (element.position?.y || 0) + (element.height || 0)
  ),
);
const cameraTopY = Math.max(
  0,
  ...(bp.camera_points || []).flatMap(point => [
    point.position?.y || 0,
    point.look_at?.y || 0,
  ]),
);
const worldTopY = Math.max(8, layoutTopY, cameraTopY);
const worldSpan = Math.max(
  bp.grid.width * cell,
  bp.grid.depth * cell,
  worldTopY * 1.6,
);
camera.far = Math.max(camera.far, worldSpan * 4);
camera.updateProjectionMatrix();
if (scene.fog) {{
  scene.fog.near = Math.max(55, worldSpan * .9);
  scene.fog.far = Math.max(95, worldSpan * 2.8);
}}
const overviewTarget = new THREE.Vector3(
  bp.grid.width * cell * .5,
  Math.max(2, worldTopY * .34),
  bp.grid.depth * cell * .5,
);

function dampAngle(current, target, damping, dt) {{
  const delta = Math.atan2(Math.sin(target-current), Math.cos(target-current));
  return current + delta * (1 - Math.exp(-damping * dt));
}}

function resetOrbitAngle() {{
  orbitYaw = DEFAULT_ORBIT_YAW;
  orbitPitch = DEFAULT_ORBIT_PITCH;
  targetOrbitYaw = DEFAULT_ORBIT_YAW;
  targetOrbitPitch = DEFAULT_ORBIT_PITCH;
}}

function recenterBehindPlayer(immediate=false) {{
  targetOrbitYaw = player.rotation.y + Math.PI;
  targetOrbitPitch = DEFAULT_ORBIT_PITCH;
  if (immediate) {{
    orbitYaw = targetOrbitYaw;
    orbitPitch = targetOrbitPitch;
  }}
}}

function setOrbitFromOffset(offset) {{
  const distance = Math.max(.001, offset.length());
  orbitYaw = Math.atan2(offset.x, offset.z);
  orbitPitch = THREE.MathUtils.clamp(
    Math.asin(THREE.MathUtils.clamp(offset.y / distance, -1, 1)),
    ORBIT_PITCH_MIN,
    ORBIT_PITCH_MAX,
  );
  targetOrbitYaw = orbitYaw;
  targetOrbitPitch = orbitPitch;
  return distance;
}}

function updateOrbitDamping(dt) {{
  orbitYaw = dampAngle(orbitYaw, targetOrbitYaw, ORBIT_DAMPING, dt);
  orbitPitch += (targetOrbitPitch - orbitPitch) * (1 - Math.exp(-ORBIT_DAMPING * dt));
  orbitPitch = THREE.MathUtils.clamp(orbitPitch, ORBIT_PITCH_MIN, ORBIT_PITCH_MAX);
  if (manualMode && overviewMode) {{
    positionCameraOnOrbit(cameraTarget, overviewDistance);
  }}
}}

function positionCameraOnOrbit(target, distance) {{
  const cosPitch = Math.cos(orbitPitch);
  camera.position.set(
    target.x + Math.sin(orbitYaw) * cosPitch * distance,
    target.y + Math.sin(orbitPitch) * distance,
    target.z + Math.cos(orbitYaw) * cosPitch * distance,
  );
  camera.lookAt(target);
}}

function updateZoomLabel() {{
  const label = document.getElementById('zoomState');
  if (!label) return;
  if (overviewMode) {{
    label.textContent = '🌐 Overview';
    return;
  }}
  label.textContent = '🔎 ' + Math.round(100 / followZoom) + '%';
}}

function setFollowZoom(value) {{
  followZoom = THREE.MathUtils.clamp(value, ZOOM_MIN, ZOOM_MAX);
  overviewMode = false;
  updateZoomLabel();
}}

function zoomCamera(direction) {{
  if (overviewMode) {{
    const delta = camera.position.clone().sub(cameraTarget);
    const currentDistance = Math.max(.001, delta.length());
    const factor = direction > 0 ? 1.16 : .86;
    const nextDistance = THREE.MathUtils.clamp(
      currentDistance * factor,
      worldSpan * .35,
      worldSpan * 2.2,
    );
    overviewDistance = nextDistance;
    delta.setLength(nextDistance);
    camera.position.copy(cameraTarget).add(delta);
    camera.lookAt(cameraTarget);
    return;
  }}
  setFollowZoom(followZoom * (direction > 0 ? 1.16 : .86));
}}

function showOverview() {{
  stopTour();
  overviewMode = true;
  keys.clear();
  const horizontal = Math.max(bp.grid.width * cell, bp.grid.depth * cell);
  cameraTarget.copy(overviewTarget);
  camera.position.set(
    overviewTarget.x - horizontal * .78,
    Math.max(worldTopY + horizontal * .58, 30),
    overviewTarget.z + horizontal * .88,
  );
  overviewDistance = setOrbitFromOffset(camera.position.clone().sub(cameraTarget));
  camera.lookAt(cameraTarget);
  updateZoomLabel();
}}

function setAnimationState(next) {{
  if (animationState === next) return;
  animationState = next;
  const label = document.getElementById('animState');
  if (label) label.textContent = next;
  playGltfState(next);
}}

function updateProceduralAnimation(dt) {{
  if (!proceduralAvatar.visible) return;
  animationTime += dt;
  const p = proceduralAvatar.userData.parts || {{}};
  const moving = animationState !== 'Idle';
  const run = animationState === 'Run';
  const speed = run ? 11.0 : moving ? 7.0 : 2.2;
  const amplitude = run ? .8 : moving ? .52 : .06;
  const swing = Math.sin(animationTime * speed) * amplitude;

  if (p.la) p.la.rotation.x = moving ? swing : Math.sin(animationTime*2.2)*.04;
  if (p.ra) p.ra.rotation.x = moving ? -swing : -Math.sin(animationTime*2.2)*.04;
  if (p.lf) p.lf.rotation.x = moving ? -swing*.48 : 0;
  if (p.rf) p.rf.rotation.x = moving ? swing*.48 : 0;
  if (p.body) p.body.position.y = 1.18 + Math.abs(Math.sin(animationTime*speed)) * (run ? .11 : moving ? .06 : .025);
  if (p.head) p.head.rotation.z = moving ? Math.sin(animationTime*speed*.5)*.025 : Math.sin(animationTime*1.7)*.018;
}}

function pathHeightAt(x, z) {{
  let best = null;
  (bp.paths || []).forEach(path => {{
    const points = path.points || [];
    const halfWidth = Math.max(1.5, (path.width_cells || 2) * .8);
    for (let i=0; i<points.length-1; i++) {{
      const a=points[i], b=points[i+1];
      const vx=b.x-a.x, vz=b.z-a.z;
      const len2=vx*vx+vz*vz;
      if (len2 < .0001) continue;
      const t=THREE.MathUtils.clamp(((x-a.x)*vx+(z-a.z)*vz)/len2,0,1);
      const px=a.x+vx*t, pz=a.z+vz*t;
      const dist=Math.hypot(x-px,z-pz);
      if (dist <= halfWidth && (!best || dist < best.dist)) {{
        best={{
          dist,
          y:(a.y||0)+((b.y||0)-(a.y||0))*t
        }};
      }}
    }}
  }});
  return best ? best.y : 0;
}}

function updatePlayer(dt) {{
  if (!manualMode) {{
    setAnimationState('Idle');
    return;
  }}

  let forwardInput = 0;
  let sideInput = 0;
  if (keys.has('KeyW') || keys.has('ArrowUp')) forwardInput += 1;
  if (keys.has('KeyS') || keys.has('ArrowDown')) forwardInput -= 1;
  if (keys.has('KeyA') || keys.has('ArrowLeft')) sideInput -= 1;
  if (keys.has('KeyD') || keys.has('ArrowRight')) sideInput += 1;

  const inputLength = Math.hypot(forwardInput, sideInput);
  const running = keys.has('ShiftLeft') || keys.has('ShiftRight');

  if (inputLength > 0) {{
    // Camera-relative ground-plane movement: W always moves into the view,
    // while A/D remain screen-relative left/right after any orbit.
    moveForward.set(-Math.sin(orbitYaw), 0, -Math.cos(orbitYaw)).normalize();
    moveRight.set(-moveForward.z, 0, moveForward.x).normalize();
    moveVector
      .copy(moveForward).multiplyScalar(forwardInput)
      .addScaledVector(moveRight, sideInput)
      .normalize();

    const speed = running ? 10.5 : 6.2;
    setAnimationState(running ? 'Run' : 'Walk');
    player.position.addScaledVector(moveVector, speed * dt);

    const desiredPlayerYaw = Math.atan2(moveVector.x, moveVector.z);
    player.rotation.y = dampAngle(
      player.rotation.y,
      desiredPlayerYaw,
      PLAYER_TURN_DAMPING,
      dt,
    );
  }} else {{
    setAnimationState('Idle');
  }}

  const margin = 1.5;
  player.position.x = THREE.MathUtils.clamp(player.position.x, margin, bp.grid.width*cell-margin);
  player.position.z = THREE.MathUtils.clamp(player.position.z, margin, bp.grid.depth*cell-margin);
  const routeY = pathHeightAt(player.position.x, player.position.z);
  player.position.y += ((routeY + .02) - player.position.y) * Math.min(1, dt * 9);
}}

function updateFollowCamera(dt) {{
  if (!manualMode || overviewMode) return;
  const target = player.position.clone().add(
    new THREE.Vector3(0, FOLLOW_TARGET_HEIGHT, 0)
  );
  const distance = baseFollowDistance * followZoom;
  const cosPitch = Math.cos(orbitPitch);
  scaledFollowOffset.set(
    Math.sin(orbitYaw) * cosPitch * distance,
    Math.sin(orbitPitch) * distance,
    Math.cos(orbitYaw) * cosPitch * distance,
  );
  const desired = target.clone().add(scaledFollowOffset);
  const blend = 1 - Math.pow(.001, dt);
  camera.position.lerp(desired, blend);
  cameraTarget.lerp(target, blend);
  camera.lookAt(cameraTarget);
}}

function cameraPointById(id) {{
  return (bp.camera_points || []).find(p => p.camera_id === id);
}}

function startTour() {{
  const tour = (bp.director_tours || [])[0];
  if (!tour || !(tour.steps || []).length) return;
  overviewMode = false;
  updateZoomLabel();
  manualMode = false;
  keys.clear();
  tourState = {{ tour, index:0, elapsed:0, fromPos:camera.position.clone(), fromLook:cameraTarget.clone() }};
  document.getElementById('tour').textContent = '🧭 Return to Explore';
}}

function stopTour() {{
  manualMode = true;
  tourState = null;
  document.getElementById('tour').textContent = '🎬 Start Director Tour';
}}

function updateTour(dt) {{
  if (!tourState) return;
  const step = tourState.tour.steps[tourState.index];
  const point = cameraPointById(step.camera_id);
  if (!point) {{
    tourState.index += 1; tourState.elapsed = 0;
    if (tourState.index >= tourState.tour.steps.length) stopTour();
    return;
  }}
  tourState.elapsed += dt;
  const duration = Math.max(.5, step.duration_seconds || 4);
  const t = Math.min(1, tourState.elapsed / duration);
  const smooth = t*t*(3-2*t);
  const toPos = new THREE.Vector3(point.position.x, point.position.y, point.position.z);
  const toLook = new THREE.Vector3(point.look_at.x, point.look_at.y, point.look_at.z);
  camera.position.lerpVectors(tourState.fromPos, toPos, smooth);
  cameraTarget.lerpVectors(tourState.fromLook, toLook, smooth);
  camera.lookAt(cameraTarget);
  if (t >= 1) {{
    tourState.index += 1; tourState.elapsed = 0;
    tourState.fromPos.copy(toPos); tourState.fromLook.copy(toLook);
    if (tourState.index >= tourState.tour.steps.length) stopTour();
  }}
}}

document.getElementById('tour').addEventListener('click', () => {{
  if (manualMode) startTour(); else stopTour();
}});
document.getElementById('zoomOut').addEventListener('click', () => zoomCamera(1));
document.getElementById('zoomIn').addEventListener('click', () => zoomCamera(-1));
document.getElementById('overview').addEventListener('click', showOverview);
document.getElementById('recenter').addEventListener('click', () => {{
  stopTour();
  overviewMode = false;
  recenterBehindPlayer();
  updateZoomLabel();
}});
document.getElementById('reset').addEventListener('click', () => {{
  stopTour();
  overviewMode = false;
  followZoom = 1.0;
  resetOrbitAngle();
  resetPlayer();
  updateZoomLabel();
}});

renderer.domElement.addEventListener('pointerdown', event => {{
  if (!manualMode || event.button !== 0) return;
  orbitDragging = true;
  orbitPointerId = event.pointerId;
  orbitPointerX = event.clientX;
  orbitPointerY = event.clientY;
  renderer.domElement.setPointerCapture?.(event.pointerId);
  renderer.domElement.style.cursor = 'grabbing';
}});

renderer.domElement.addEventListener('pointermove', event => {{
  if (!orbitDragging || event.pointerId !== orbitPointerId || !manualMode) return;
  const dx = event.clientX - orbitPointerX;
  const dy = event.clientY - orbitPointerY;
  orbitPointerX = event.clientX;
  orbitPointerY = event.clientY;

  targetOrbitYaw -= dx * ORBIT_SENSITIVITY;
  targetOrbitPitch = THREE.MathUtils.clamp(
    targetOrbitPitch - dy * ORBIT_SENSITIVITY,
    ORBIT_PITCH_MIN,
    ORBIT_PITCH_MAX,
  );
}});

function endOrbitDrag(event) {{
  if (!orbitDragging || event.pointerId !== orbitPointerId) return;
  orbitDragging = false;
  orbitPointerId = null;
  renderer.domElement.releasePointerCapture?.(event.pointerId);
  renderer.domElement.style.cursor = 'grab';
}}

renderer.domElement.addEventListener('pointerup', endOrbitDrag);
renderer.domElement.addEventListener('pointercancel', endOrbitDrag);

renderer.domElement.addEventListener('wheel', event => {{
  event.preventDefault();
  if (!manualMode) return;
  zoomCamera(Math.sign(event.deltaY || 1));
}}, {{ passive:false }});

function resize() {{
  const w = host.clientWidth || 900;
  const h = Math.max(620, host.clientHeight || 700);
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}}
window.addEventListener('resize', resize);
resize();
cameraTarget.copy(player.position).add(new THREE.Vector3(0,FOLLOW_TARGET_HEIGHT,0));
camera.position.copy(cameraTarget).add(baseFollowOffset);
camera.lookAt(cameraTarget);
updateZoomLabel();

function animate() {{
  requestAnimationFrame(animate);
  const dt = Math.min(clock.getDelta(), .05);
  updateOrbitDamping(dt);
  updatePlayer(dt);
  updateProceduralAnimation(dt);
  if (gltfMixer) gltfMixer.update(dt);
  updateFollowCamera(dt);
  updateTour(dt);
  renderer.render(scene, camera);
}}
animate();
</script>
</body>
</html>"""


def runtime_summary(
    *,
    profile: WorldProfile,
    blueprint: WorldBlueprint,
    character_profile: CharacterProfile | None = None,
) -> dict[str, object]:
    """Small inspectable summary used by UI/tests without running a browser."""

    return {
        "grid": f"{blueprint.grid.width}x{blueprint.grid.depth}",
        "chunks": len(blueprint.chunks),
        "landmarks": len(blueprint.landmarks),
        "camera_points": len(blueprint.camera_points),
        "director_tours": len(blueprint.director_tours),
        "theme_colors": list(profile.theme_color_hexes),
        "character_colors": (
            list(character_profile.favorite_color_hexes)
            if character_profile is not None
            else []
        ),
    }
