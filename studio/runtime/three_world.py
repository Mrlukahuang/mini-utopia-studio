from __future__ import annotations

import json
from html import escape

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
) -> str:
    """Build a self-contained Three.js playground for a saved WorldBlueprint.

    The runtime is intentionally a renderer of saved data. It does not mutate
    Canon world state or invent new Blueprint structure.
    """

    runtime_data = {
        "worldName": world_name,
        "profile": profile.model_dump(mode="json"),
        "blueprint": blueprint.model_dump(mode="json"),
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
</head>
<body>
<div id="wrap">
  <div id="canvas"></div>
  <div class="hud">
    <h2>🌍 {escape(world_name)}</h2>
    <p><b>Explore Mode</b> · WASD / Arrow Keys</p>
    <p>Blueprint v{escape(blueprint.schema_version)} · {blueprint.grid.width}×{blueprint.grid.depth} · {len(blueprint.chunks)} chunks</p>
    <span class="pill">🧸 Mini Avatar</span>
    <span class="pill">🌀 Portal</span>
    <span class="pill">🎬 Director Camera</span>
  </div>
  <div class="controls">
    <button id="reset">↺ Reset</button>
    <button id="tour" class="primary">🎬 Start Director Tour</button>
  </div>
  <div class="tip">Click inside the world, then use WASD to explore · 方向键也可以</div>
</div>

<script type="module">
import * as THREE from 'https://cdn.jsdelivr.net/npm/three@{THREE_VERSION}/build/three.module.js';

const DATA = {data_json};
const profile = DATA.profile;
const bp = DATA.blueprint;
const host = document.getElementById('canvas');

const renderer = new THREE.WebGLRenderer({{ antialias:true, alpha:false }});
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
host.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const palette = (profile.theme_color_hexes && profile.theme_color_hexes.length)
  ? profile.theme_color_hexes
  : ['#F7B7D2','#B9E7D0','#D7C2F3','#BDE3F7','#FFF4D7'];
scene.background = new THREE.Color(palette[3] || '#BDE3F7');
scene.fog = new THREE.Fog(scene.background, 55, 95);

const camera = new THREE.PerspectiveCamera(48, 1, 0.1, 180);

const hemi = new THREE.HemisphereLight(0xffffff, 0xcfc7e8, 2.3);
scene.add(hemi);
const sun = new THREE.DirectionalLight(0xfff4df, 3.2);
sun.position.set(24, 34, 18);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.camera.left = -55; sun.shadow.camera.right = 55;
sun.shadow.camera.top = 55; sun.shadow.camera.bottom = -55;
scene.add(sun);

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

(bp.chunks || []).forEach((chunk, i) => {{
  const color = palette[i % palette.length];
  const geo = new THREE.BoxGeometry(cw - .18, .8, cd - .18);
  const mesh = new THREE.Mesh(geo, mat(color));
  mesh.position.set(chunk.chunk_x * cw + cw/2, -.4, chunk.chunk_z * cd + cd/2);
  mesh.receiveShadow = true;
  world.add(mesh);

  // Soft block-built scenery clusters: decorative only, not Canon geometry.
  if ((i % 3) === 0) {{
    const h = 1.1 + (i % 4) * .35;
    const deco = new THREE.Mesh(
      new THREE.BoxGeometry(2.2, h, 2.2),
      mat(palette[(i+2) % palette.length])
    );
    deco.position.set(mesh.position.x - 2.3, h/2, mesh.position.z + 2.0);
    deco.castShadow = true; deco.receiveShadow = true;
    world.add(deco);
  }}
}});

function addLandmark(spec, index) {{
  const g = new THREE.Group();
  const c1 = palette[(index + 1) % palette.length];
  const c2 = palette[(index + 3) % palette.length];
  const base = new THREE.Mesh(new THREE.BoxGeometry(4.4, 1.2, 4.4), mat(c1));
  base.position.y = .6; base.castShadow = true; base.receiveShadow = true;
  g.add(base);
  const tower = new THREE.Mesh(new THREE.BoxGeometry(2.6, 5.2, 2.6), mat(c2));
  tower.position.y = 3.2; tower.castShadow = true; g.add(tower);
  const cap = new THREE.Mesh(new THREE.SphereGeometry(1.8, 16, 10), mat(c1));
  cap.scale.y = .7; cap.position.y = 6.0; cap.castShadow = true; g.add(cap);
  g.position.set(spec.position.x, spec.position.y || 0, spec.position.z);
  g.userData.label = spec.name;
  world.add(g);
}}
(bp.landmarks || []).forEach(addLandmark);

if (bp.portal) {{
  const portal = new THREE.Group();
  const ring = new THREE.Mesh(
    new THREE.TorusGeometry(2.3, .42, 14, 36),
    new THREE.MeshStandardMaterial({{
      color:new THREE.Color(palette[2] || '#D7C2F3'),
      emissive:new THREE.Color(palette[2] || '#D7C2F3'),
      emissiveIntensity:1.4,
      roughness:.35
    }})
  );
  ring.rotation.y = Math.PI / 2;
  ring.position.y = 3.0;
  ring.castShadow = true;
  portal.add(ring);
  const glow = new THREE.PointLight(palette[2] || '#D7C2F3', 12, 12);
  glow.position.y = 3.0; portal.add(glow);
  portal.position.set(bp.portal.position.x, bp.portal.position.y || 0, bp.portal.position.z);
  world.add(portal);
}}

function makeAvatar() {{
  const g = new THREE.Group();
  const body = new THREE.Mesh(new THREE.BoxGeometry(1.05, 1.45, .78), mat('#FFF4D7'));
  body.position.y = 1.25; body.castShadow = true; g.add(body);
  const head = new THREE.Mesh(new THREE.BoxGeometry(1.65, 1.55, 1.45), mat(palette[0] || '#F7B7D2'));
  head.position.y = 2.65; head.castShadow = true; g.add(head);
  const footGeo = new THREE.BoxGeometry(.55, .38, .9);
  const footMat = mat('#F6F7FB');
  const lf = new THREE.Mesh(footGeo, footMat); lf.position.set(-.35,.25,.08); lf.castShadow=true; g.add(lf);
  const rf = new THREE.Mesh(footGeo, footMat); rf.position.set(.35,.25,.08); rf.castShadow=true; g.add(rf);
  return g;
}}

const player = makeAvatar();
scene.add(player);

const spawn = bp.spawn || {{x:6,y:0,z:25,facing_degrees:90}};
function resetPlayer() {{
  player.position.set(spawn.x, .02, spawn.z);
  player.rotation.y = THREE.MathUtils.degToRad(-(spawn.facing_degrees || 0));
}}
resetPlayer();

const keys = new Set();
let manualMode = true;
let tourState = null;

window.addEventListener('keydown', e => {{
  if (['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','KeyW','KeyA','KeyS','KeyD'].includes(e.code)) {{
    e.preventDefault(); keys.add(e.code);
  }}
}});
window.addEventListener('keyup', e => keys.delete(e.code));

const velocity = new THREE.Vector3();
const cameraTarget = new THREE.Vector3();
const clock = new THREE.Clock();

function updatePlayer(dt) {{
  if (!manualMode) return;
  let dx = 0, dz = 0;
  if (keys.has('KeyW') || keys.has('ArrowUp')) dz -= 1;
  if (keys.has('KeyS') || keys.has('ArrowDown')) dz += 1;
  if (keys.has('KeyA') || keys.has('ArrowLeft')) dx -= 1;
  if (keys.has('KeyD') || keys.has('ArrowRight')) dx += 1;
  const len = Math.hypot(dx, dz);
  if (len > 0) {{
    dx /= len; dz /= len;
    const speed = 7.0;
    player.position.x += dx * speed * dt;
    player.position.z += dz * speed * dt;
    player.rotation.y = Math.atan2(dx, dz);
  }}
  const margin = 1.5;
  player.position.x = THREE.MathUtils.clamp(player.position.x, margin, bp.grid.width*cell-margin);
  player.position.z = THREE.MathUtils.clamp(player.position.z, margin, bp.grid.depth*cell-margin);
}}

const followOffset = new THREE.Vector3(-7, 7, 9);
function updateFollowCamera(dt) {{
  if (!manualMode) return;
  const desired = player.position.clone().add(followOffset);
  const blend = 1 - Math.pow(.001, dt);
  camera.position.lerp(desired, blend);
  cameraTarget.lerp(player.position.clone().add(new THREE.Vector3(0,1.8,0)), blend);
  camera.lookAt(cameraTarget);
}}

function cameraPointById(id) {{
  return (bp.camera_points || []).find(p => p.camera_id === id);
}}

function startTour() {{
  const tour = (bp.director_tours || [])[0];
  if (!tour || !(tour.steps || []).length) return;
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
document.getElementById('reset').addEventListener('click', () => {{
  stopTour(); resetPlayer();
}});

function resize() {{
  const w = host.clientWidth || 900;
  const h = Math.max(620, host.clientHeight || 700);
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}}
window.addEventListener('resize', resize);
resize();
camera.position.set(spawn.x-7, 7, spawn.z+9);
cameraTarget.copy(player.position).add(new THREE.Vector3(0,1.8,0));
camera.lookAt(cameraTarget);

function animate() {{
  requestAnimationFrame(animate);
  const dt = Math.min(clock.getDelta(), .05);
  updatePlayer(dt);
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
) -> dict[str, object]:
    """Small inspectable summary used by UI/tests without running a browser."""

    return {
        "grid": f"{blueprint.grid.width}x{blueprint.grid.depth}",
        "chunks": len(blueprint.chunks),
        "landmarks": len(blueprint.landmarks),
        "camera_points": len(blueprint.camera_points),
        "director_tours": len(blueprint.director_tours),
        "theme_colors": list(profile.theme_color_hexes),
    }
