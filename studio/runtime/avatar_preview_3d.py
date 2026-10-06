from __future__ import annotations

import json

from studio.models.avatar import AVATAR_RIG_FAMILY, AvatarAppearance
from studio.models.baby import BabyRuntimeSpec
from studio.models.equipment_runtime import EquipmentRuntimeSpec


THREE_VERSION = "0.181.0"

# Mirrors MiniUtopiaAvatarContract.body_width_scale() in Godot.
BODY_WIDTH_SCALE = {
    "slim": 0.84,
    "standard": 1.0,
    "chubby": 1.16,
}

# Head silhouette intentionally stays stable so body type reads from the body,
# not by turning the face into a vertical/horizontal egg.
HEAD_WIDTH_SCALE = {
    "slim": 1.0,
    "standard": 1.0,
    "chubby": 1.0,
}


def _safe_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


def build_avatar_preview_html(
    appearance: AvatarAppearance,
    *,
    equipment: EquipmentRuntimeSpec | None = None,
    baby: BabyRuntimeSpec | None = None,
) -> str:
    """Build the reusable Creator/Dressing-Room WebGL Avatar preview.

    Geometry and body-width rules intentionally mirror the Godot
    MiniUtopiaAvatarContract preview so the browser is a visual client of the
    same playable-avatar contract rather than a second character system.
    """

    payload = {
        "rigFamily": AVATAR_RIG_FAMILY,
        "appearance": appearance.model_dump(mode="json"),
        "bodyWidthScale": BODY_WIDTH_SCALE,
        "headWidthScale": HEAD_WIDTH_SCALE,
        "equipment": (
            equipment.model_dump(mode="json")
            if equipment is not None
            else None
        ),
        "baby": (
            baby.model_dump(mode="json")
            if baby is not None
            else None
        ),
    }
    data_json = _safe_json(payload)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
  html, body {{
    margin:0; height:100%; overflow:hidden;
    background:linear-gradient(145deg,#fff8e9 0%,#eeeaff 52%,#e5f8ff 100%);
    font-family:ui-rounded,"Nunito","Noto Sans SC",system-ui,sans-serif;
  }}
  #wrap {{
    position:relative; width:100%; height:100vh; min-height:600px;
    overflow:hidden; border-radius:28px;
  }}
  #canvas {{ position:absolute; inset:0; }}
  #canvas canvas {{ display:block; width:100%; height:100%; touch-action:none; cursor:grab; }}
  #canvas canvas:active {{ cursor:grabbing; }}
  .topbar {{
    position:absolute; left:18px; right:18px; top:16px; z-index:10;
    display:flex; justify-content:space-between; gap:12px; align-items:flex-start;
    pointer-events:none;
  }}
  .title, .contract {{
    background:rgba(255,255,255,.82); backdrop-filter:blur(14px);
    border:1px solid rgba(91,80,128,.12);
    box-shadow:0 10px 28px rgba(72,62,112,.10);
    border-radius:999px; padding:9px 13px; color:#37334f;
  }}
  .title {{ font-weight:900; font-size:14px; }}
  .contract {{ font-size:11px; color:#726b8e; }}
  .controls {{
    position:absolute; left:50%; bottom:18px; transform:translateX(-50%);
    z-index:10; display:flex; gap:8px; flex-wrap:wrap; justify-content:center;
  }}
  button {{
    border:1px solid rgba(91,80,128,.12); border-radius:999px;
    background:rgba(255,255,255,.9); color:#393451;
    box-shadow:0 8px 22px rgba(72,62,112,.10);
    padding:9px 13px; font:inherit; font-size:12px; font-weight:800; cursor:pointer;
  }}
  button.active {{ background:#ffeaf5; border-color:#f4accd; }}
  .hint {{
    position:absolute; right:18px; bottom:18px; z-index:9;
    color:#756d8e; font-size:11px; background:rgba(255,255,255,.74);
    border-radius:999px; padding:7px 10px;
  }}
  .error {{
    display:none; position:absolute; inset:82px 18px auto 18px; z-index:30;
    padding:14px 16px; border-radius:18px; color:#8b2e3a;
    background:rgba(255,235,238,.97); border:1px solid rgba(180,60,80,.2);
  }}
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
  <div class="topbar">
    <div class="title">🧸 Live 3D Avatar / 实时 3D 预览</div>
    <div class="contract">Rig · {AVATAR_RIG_FAMILY}</div>
  </div>
  <div class="controls">
    <button data-state="Idle" class="active">Idle</button>
    <button data-state="Walk">Walk</button>
    <button data-state="Run">Run</button>
    <button data-state="Jump">Jump</button>
    <button id="reset">↺ Reset View</button>
  </div>
  <div class="hint">Drag / 拖动旋转 · Wheel / 滚轮缩放</div>
  <div id="runtimeError" class="error"></div>
</div>

<script type="module">
import * as THREE from 'three';
import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';

const DATA = {data_json};
const A = DATA.appearance;
const E = DATA.equipment || {{equipped: {{}}, final_stats: {{}}}};
const B = DATA.baby || null;
const host = document.getElementById('canvas');
const errorBox = document.getElementById('runtimeError');

function fail(message) {{
  errorBox.style.display = 'block';
  errorBox.textContent = '3D Avatar Preview error: ' + message;
}}

window.addEventListener('error', e => fail(e.message || 'Unknown browser error'));
window.addEventListener('unhandledrejection', e => fail(String(e.reason || 'Module failed to load')));

const renderer = new THREE.WebGLRenderer({{antialias:true, alpha:true}});
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
host.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(34, 1, .1, 80);
camera.position.set(4.8, 3.2, 7.2);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.enablePan = false;
controls.minDistance = 4.4;
controls.maxDistance = 10.5;
controls.minPolarAngle = Math.PI * .18;
controls.maxPolarAngle = Math.PI * .72;
controls.target.set(0, 1.18, 0);

scene.add(new THREE.HemisphereLight(0xffffff, 0xc7bde9, 2.5));
const key = new THREE.DirectionalLight(0xfff3df, 3.5);
key.position.set(5, 7, 6);
key.castShadow = true;
key.shadow.mapSize.set(2048,2048);
scene.add(key);
const rim = new THREE.DirectionalLight(0xcfeeff, 2.2);
rim.position.set(-5,4,-5);
scene.add(rim);

const stage = new THREE.Group();
scene.add(stage);

const floorMat = new THREE.MeshStandardMaterial({{
  color:'#fff8ee', roughness:.94, metalness:0
}});
const floor = new THREE.Mesh(new THREE.CylinderGeometry(2.65,2.95,.30,48), floorMat);
floor.position.y = -.17;
floor.receiveShadow = true;
stage.add(floor);

const ring = new THREE.Mesh(
  new THREE.TorusGeometry(2.35,.035,10,64),
  new THREE.MeshStandardMaterial({{
    color:'#d9c9fb', emissive:'#d9c9fb', emissiveIntensity:.45, roughness:.5
  }})
);
ring.rotation.x = Math.PI/2;
ring.position.y = .005;
stage.add(ring);

function mat(color, rough=.82, metal=.02) {{
  return new THREE.MeshStandardMaterial({{
    color:new THREE.Color(color), roughness:rough, metalness:metal
  }});
}}

function roundedBox(w,h,d,r=.12) {{
  const shape = new THREE.Shape();
  const x=-w/2, y=-h/2;
  shape.moveTo(x+r,y);
  shape.lineTo(x+w-r,y);
  shape.quadraticCurveTo(x+w,y,x+w,y+r);
  shape.lineTo(x+w,y+h-r);
  shape.quadraticCurveTo(x+w,y+h,x+w-r,y+h);
  shape.lineTo(x+r,y+h);
  shape.quadraticCurveTo(x,y+h,x,y+h-r);
  shape.lineTo(x,y+r);
  shape.quadraticCurveTo(x,y,x+r,y);
  const geo = new THREE.ExtrudeGeometry(shape,{{
    depth:d, bevelEnabled:true, bevelSize:Math.min(r*.5,d*.18),
    bevelThickness:Math.min(r*.5,d*.18), bevelSegments:2
  }});
  geo.center();
  return geo;
}}

function addMesh(parent, geometry, material, position, name) {{
  const mesh = new THREE.Mesh(geometry, material);
  mesh.name = name;
  mesh.position.set(position[0],position[1],position[2]);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  parent.add(mesh);
  return mesh;
}}

function sphereGeo(rx,ry,rz) {{
  const g = new THREE.SphereGeometry(1,28,18);
  g.scale(rx,ry,rz);
  return g;
}}

function rarityColor(rarity) {{
  return {{
    green:'#78D66C', blue:'#65A9F5', purple:'#B879F4',
    gold:'#F4C95D', red:'#F06A6A', rainbow:'#F59BD8'
  }}[rarity] || '#B879F4';
}}

function equippedItem(slot) {{
  return (E.equipped || {{}})[slot] || null;
}}

function buildSword(width, item) {{
  const g = new THREE.Group();
  g.name = 'Equipment_Weapon_Main';
  const rarity = rarityColor(item.rarity);
  addMesh(g, roundedBox(.13,.92,.09,.035), mat('#E9EEF7',.26,.55), [0,.43,0], 'Blade');
  addMesh(g, roundedBox(.42,.09,.12,.035), mat(rarity,.48,.20), [0,-.05,0], 'Guard');
  addMesh(g, roundedBox(.10,.35,.10,.035), mat('#74513B',.76), [0,-.26,0], 'Handle');
  const gem = addMesh(g,new THREE.SphereGeometry(.10,16,10),mat(rarity,.34,.14),[0,-.48,0],'Pommel');
  gem.castShadow=true;
  g.position.set(.78*width,.98,.08);
  g.rotation.z=-.12;
  return g;
}}

function addEquipment(root) {{
  const width = root.userData.bodyWidth || 1;
  const parts = root.userData.parts || {{}};

  const outfit = equippedItem('outfit');
  if (outfit && parts.body) {{
    const color = rarityColor(outfit.rarity);
    parts.body.material = mat(color,.78,.02);
    addMesh(
      root,roundedBox(.62*width,.13,.49*width,.05),
      mat('#FFF4D7',.78),[0,1.18,.01],'OutfitCollar'
    );
  }}

  const weapon = equippedItem('weapon_main');
  if (weapon) root.add(buildSword(width, weapon));

  const backpack = equippedItem('backpack');
  if (backpack) {{
    const g=new THREE.Group(); g.name='Equipment_Backpack';
    addMesh(
      g,roundedBox(.58*width,.72,.28,.10),
      mat(rarityColor(backpack.rarity),.76),[0,0,0],'Pack'
    );
    addMesh(
      g,roundedBox(.36*width,.22,.08,.05),
      mat('#FFF4D7',.82),[0,.10,.18],'PackPocket'
    );
    g.position.set(0,1.10,-.47);
    root.add(g);
  }}

  const wings = equippedItem('wings');
  if (wings) {{
    const g=new THREE.Group(); g.name='Equipment_Wings';
    const wingMat=mat(rarityColor(wings.rarity),.56,.04);
    for(const side of [-1,1]) {{
      const wing=addMesh(
        g,new THREE.ConeGeometry(.34,.94,4),wingMat,
        [.48*side,0,0],'Wing'
      );
      wing.rotation.z=side*(Math.PI/2.8);
      wing.rotation.y=Math.PI/4;
    }}
    g.position.set(0,1.34,-.39);
    root.add(g);
  }}

  const accessory = equippedItem('accessory');
  if (accessory) {{
    const color=rarityColor(accessory.rarity);
    const charm=new THREE.Mesh(
      new THREE.TorusGeometry(.13,.04,10,20),
      mat(color,.35,.24)
    );
    charm.name='Equipment_Accessory';
    charm.position.set(.35*width,1.46,.48);
    charm.rotation.x=Math.PI/2;
    charm.castShadow=true;
    root.add(charm);
  }}
}}

function buildBabyCompanion() {{
  if (!B) return null;
  const g=new THREE.Group();
  g.name='ActiveBaby_' + B.baby_id;
  const species=B.species_id || 'star_baby';
  const palette={{
    star_baby:['#FFD968','#FFF4BF'],
    cloud_baby:['#F7FBFF','#DDEEFF'],
    sheep_baby:['#F6F1E8','#CFA77E'],
    robot_baby:['#B9DDF4','#8EA3B8'],
    forest_baby:['#B9E7D0','#7BAF7A'],
  }}[species] || ['#FFD968','#FFF4BF'];
  const bodyMat=mat(palette[0],.72,.03);
  const accentMat=mat(palette[1],.78,.02);

  addMesh(g,sphereGeo(.36,.31,.33),bodyMat,[0,.40,0],'BabyBody');
  addMesh(g,sphereGeo(.30,.29,.29),accentMat,[0,.78,.02],'BabyHead');

  for(const s of [-1,1]) {{
    addMesh(
      g,sphereGeo(.052,.07,.045),mat('#4C4058',.38),
      [.105*s,.80,.285],'BabyEye'
    );
  }}

  if(species==='star_baby') {{
    const star=new THREE.Mesh(
      new THREE.OctahedronGeometry(.17,0),
      mat('#FFD968',.35,.08)
    );
    star.position.set(-.36,.84,.02);
    star.rotation.z=Math.PI/4;
    g.add(star);
  }} else if(species==='cloud_baby') {{
    for(const x of [-.22,0,.22]) addMesh(
      g,sphereGeo(.18,.14,.16),accentMat,[x,.94,-.03],'CloudPuff'
    );
  }} else if(species==='sheep_baby') {{
    for(const s of [-1,1]) addMesh(
      g,sphereGeo(.14,.11,.12),bodyMat,[.28*s,.82,0],'BabySheepEar'
    );
  }} else if(species==='robot_baby') {{
    addMesh(g,new THREE.CylinderGeometry(.025,.025,.18,10),mat('#7D8C9B',.4,.4),[0,1.10,0],'BabyAntenna');
    addMesh(g,new THREE.SphereGeometry(.055,12,8),bodyMat,[0,1.20,0],'BabyAntennaTip');
  }} else if(species==='forest_baby') {{
    const leaf=addMesh(
      g,new THREE.ConeGeometry(.10,.28,5),mat('#7BAF7A',.72),
      [.10,1.08,0],'BabyLeaf'
    );
    leaf.rotation.z=-.45;
  }}

  g.position.set(-1.42,.02,.20);
  g.scale.setScalar(.88);
  return g;
}}

function buildHair(root, headWidth, hairColor) {{
  if (A.hair_style_id === 'hair_none') return null;

  const group = new THREE.Group();
  group.name = 'Hair';
  root.add(group);
  const hairMat = mat(hairColor,.72);

  // Shared visible cap: deliberately sits outside the head envelope instead
  // of being buried inside it.
  const cap = addMesh(
    group, sphereGeo(.74*headWidth,.27,.70), hairMat,
    [0,2.13,-.01], 'HairCap'
  );

  // Small front fringe makes every non-none hairstyle visible from the
  // default camera before the child rotates the Avatar.
  addMesh(
    group, roundedBox(.46*headWidth,.16,.14,.06), hairMat,
    [0,2.05,.61], 'HairFringe'
  );

  if (A.hair_style_id === 'hair_short_v1') {{
    addMesh(
      group, roundedBox(.30*headWidth,.20,.18,.06), hairMat,
      [-.28*headWidth,2.08,.52], 'ShortSweep'
    );
  }} else if (A.hair_style_id === 'hair_bob_v1') {{
    addMesh(
      group, roundedBox(.24*headWidth,.58,.34,.09), hairMat,
      [-.61*headWidth,1.77,.00], 'BobSideL'
    );
    addMesh(
      group, roundedBox(.24*headWidth,.58,.34,.09), hairMat,
      [.61*headWidth,1.77,.00], 'BobSideR'
    );
    addMesh(
      group, roundedBox(.56*headWidth,.20,.18,.07), hairMat,
      [0,1.98,.59], 'BobFringe'
    );
  }} else if (A.hair_style_id === 'hair_long_wavy_v1') {{
    addMesh(
      group, roundedBox(.27*headWidth,.86,.38,.10), hairMat,
      [-.62*headWidth,1.61,-.01], 'LongSideL'
    );
    addMesh(
      group, roundedBox(.27*headWidth,.86,.38,.10), hairMat,
      [.62*headWidth,1.61,-.01], 'LongSideR'
    );
    for (const x of [-.60,.60]) {{
      addMesh(
        group, sphereGeo(.18,.20,.18), hairMat,
        [x*headWidth,1.22,-.01], 'WaveTip'
      );
    }}
  }} else if (A.hair_style_id === 'hair_ponytail_v1') {{
    addMesh(
      group, sphereGeo(.24,.39,.25), hairMat,
      [.70*headWidth,1.82,-.38], 'Ponytail'
    );
    addMesh(
      group, roundedBox(.17,.34,.17,.06), hairMat,
      [.57*headWidth,1.93,-.25], 'PonyTie'
    );
  }} else if (A.hair_style_id === 'hair_fluffy_v1') {{
    for (const p of [
      [-.48,2.07,.00],[-.22,2.28,-.02],[.08,2.31,-.02],
      [.38,2.18,.00],[.58,1.98,.00],[-.60,1.96,.00]
    ]) {{
      addMesh(
        group, sphereGeo(.25,.22,.24), hairMat,
        [p[0]*headWidth,p[1],p[2]], 'Fluff'
      );
    }}
  }}
  return cap;
}}

function addSpeciesDetails(root, headWidth, surfaceMat) {{
  const id = A.species_head_id || '';
  if (id.includes('sheep')) {{
    for (const s of [-1,1]) {{
      const ear = addMesh(
        root,sphereGeo(.24,.18,.18),surfaceMat,
        [.66*headWidth*s,1.82,-.02],'SheepEar'
      );
      ear.rotation.z = -.28*s;
    }}
  }} else if (id.includes('cat')) {{
    for (const s of [-1,1]) {{
      const ear = addMesh(
        root,new THREE.ConeGeometry(.21,.42,4),surfaceMat,
        [.38*headWidth*s,2.25,-.02],'CatEar'
      );
      ear.rotation.y = Math.PI/4;
    }}
  }} else if (id.includes('robot')) {{
    addMesh(
      root,new THREE.CylinderGeometry(.035,.035,.28,12),
      mat('#8793A5',.48,.45),[0,2.31,0],'Antenna'
    );
    addMesh(
      root,new THREE.SphereGeometry(.075,16,10),
      mat(A.eye_color_hex,.4,.12),[0,2.48,0],'AntennaTip'
    );
  }} else if (id.includes('cloud')) {{
    for (const p of [[-.38,2.03,-.08],[0,2.16,-.07],[.38,2.03,-.08]]) {{
      addMesh(
        root,sphereGeo(.30,.25,.27),surfaceMat,
        [p[0]*headWidth,p[1],p[2]],'CloudPuff'
      );
    }}
  }}
}}

function buildAvatar() {{
  const root = new THREE.Group();
  root.name = 'Avatar_' + A.body_type;
  const width = DATA.bodyWidthScale[A.body_type] || 1;
  const headWidth = DATA.headWidthScale[A.body_type] || 1;
  const surfaceMat = mat(A.surface_color_hex || '#F2C7A5', A.surface_type === 'metal' ? .38 : .84, A.surface_type === 'metal' ? .38 : .01);
  const outfitMat = mat('#D7C2F3',.80);
  const shoeMat = mat('#EEF2FA',.72);
  const eyeMat = mat(A.eye_color_hex || '#7A5238',.42,.02);

  const body = addMesh(
    root,roundedBox(.78*width,.92,.44*width,.16),outfitMat,[0,.92,0],'Body'
  );
  const head = addMesh(
    root,sphereGeo(.70*headWidth,.69,.67),surfaceMat,[0,1.72,0],'SpeciesHead'
  );

  const limbs = {{arms:[],legs:[]}};
  for (const s of [-1,1]) {{
    const arm = addMesh(
      root,roundedBox(.22,.72,.22,.08),surfaceMat,[.52*width*s,1.05,0],'Arm'
    );
    limbs.arms.push(arm);
    const leg = addMesh(
      root,roundedBox(.27,.68,.30,.08),mat('#BFDFF5',.82),[.22*s,.34,0],'Leg'
    );
    limbs.legs.push(leg);
    addMesh(
      root,roundedBox(.33,.22,.46,.08),shoeMat,[.22*s,.085,.07],'Foot'
    );
  }}

  const eyeScale = A.eye_style_id === 'eyes_sparkle_v1' ? 1.22
    : A.eye_style_id === 'eyes_sleepy_v1' ? .72
    : A.eye_style_id === 'eyes_robot_v1' ? 1.12
    : A.eye_style_id === 'eyes_cat_v1' ? .86 : 1;
  for (const s of [-1,1]) {{
    const eye = addMesh(
      root,sphereGeo(.10*eyeScale,.12*eyeScale,.08),eyeMat,
      [.15*headWidth*s,1.76,.58],'Eye'
    );
    if (A.eye_style_id === 'eyes_cat_v1') eye.scale.y=.62;
  }}

  addSpeciesDetails(root,headWidth,surfaceMat);
  buildHair(root,headWidth,A.hair_color_hex || '#5B4036');

  // Canonical socket nodes are represented as Object3D anchors so later
  // equipment preview can attach to the exact same named contract.
  const sockets = new THREE.Group();
  sockets.name = 'Sockets';
  root.add(sockets);
  const socketPositions = {{
    'Socket_Weapon_R':[.67*width,.90,0],
    'Socket_Weapon_L':[-.67*width,.90,0],
    'Socket_Backpack':[0,1.12,-.32],
    'Socket_Wings':[0,1.34,-.33],
    'Socket_Accessory':[0,1.75,0],
  }};
  for (const [name,p] of Object.entries(socketPositions)) {{
    const node = new THREE.Object3D();
    node.name=name; node.position.set(...p); sockets.add(node);
  }}

  root.userData.parts={{body,head,...limbs}};
  root.userData.bodyWidth=width;
  root.userData.sockets=sockets;
  return root;
}}

const avatar = buildAvatar();
addEquipment(avatar);
stage.add(avatar);

const babyCompanion = buildBabyCompanion();
if (babyCompanion) stage.add(babyCompanion);

let state='Idle';
let elapsed=0;

function setState(next) {{
  state=next;
  elapsed=0;
  document.querySelectorAll('[data-state]').forEach(btn => {{
    btn.classList.toggle('active',btn.dataset.state===next);
  }});
}}
document.querySelectorAll('[data-state]').forEach(btn => {{
  btn.addEventListener('click',()=>setState(btn.dataset.state));
}});

document.getElementById('reset').addEventListener('click',()=>{{
  camera.position.set(4.8,3.2,7.2);
  controls.target.set(0,1.18,0);
  controls.update();
}});

function animateAvatar(t) {{
  const p=avatar.userData.parts;
  const arms=p.arms || [], legs=p.legs || [];
  arms.forEach(x=>{{x.rotation.x=0;x.rotation.z=0;}});
  legs.forEach(x=>{{x.rotation.x=0;}});
  avatar.position.y=0;
  avatar.rotation.z=0;

  if (state==='Walk' || state==='Run') {{
    const speed=state==='Run'?7.2:4.2;
    const swing=Math.sin(t*speed)*(state==='Run' ? .72 : .43);
    if (arms[0]) arms[0].rotation.x=swing;
    if (arms[1]) arms[1].rotation.x=-swing;
    if (legs[0]) legs[0].rotation.x=-swing*.70;
    if (legs[1]) legs[1].rotation.x=swing*.70;
    avatar.position.y=Math.abs(Math.sin(t*speed*2))*(state==='Run' ? .045 : .022);
  }} else if (state==='Jump') {{
    const phase=(elapsed%1.25)/1.25;
    avatar.position.y=Math.sin(Math.PI*phase)*.62;
    arms.forEach((x,i)=>{{x.rotation.z=(i===0?1:-1)*.62;}});
  }} else {{
    avatar.position.y=Math.sin(t*2.1)*.012;
    arms.forEach((x,i)=>{{x.rotation.z=(i===0?1:-1)*.035*Math.sin(t*1.7);}});
  }}
}}

function resize() {{
  const w=host.clientWidth || 640;
  const h=host.clientHeight || 600;
  renderer.setSize(w,h,false);
  camera.aspect=w/h;
  camera.updateProjectionMatrix();
}}
window.addEventListener('resize',resize);
resize();

const clock=new THREE.Clock();
function animate() {{
  requestAnimationFrame(animate);
  const dt=Math.min(clock.getDelta(),.05);
  elapsed+=dt;
  const t=clock.elapsedTime;
  animateAvatar(t);
  if (babyCompanion) {{
    babyCompanion.position.y=.02 + Math.sin(t*2.6)*.035;
    babyCompanion.rotation.y=Math.sin(t*.85)*.12;
  }}
  controls.update();
  renderer.render(scene,camera);
}}
animate();
</script>
</body>
</html>"""
