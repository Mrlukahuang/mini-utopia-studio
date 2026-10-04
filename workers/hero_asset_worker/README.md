# Mini Utopia Hero Asset Worker

This Worker keeps CUDA-heavy open-source 3D models outside the Streamlit app.

The main Studio sends one Hero image crop and an AppearanceSpec to:

`POST /generate`

The Worker returns a raw `.glb`. Mini Utopia stores it, references it from
RenderSpec, and Three.js loads it into the authoritative Blueprint envelope.

## Supported engines

### Pixal3D — recommended quality benchmark

Official project:
https://github.com/TencentARC/Pixal3D

Pixal3D is MIT licensed and its official inference command can generate GLB
directly from one image. Install it in its own CUDA environment following the
official README.

Example:

```bash
git clone https://github.com/TencentARC/Pixal3D.git
cd Pixal3D
# Follow the official TRELLIS.2/Pixal3D CUDA installation first.
```

Then point the Worker at that checkout:

```bash
export PIXAL3D_ROOT=/opt/Pixal3D
export PIXAL3D_LOW_VRAM=1
export PIXAL3D_RESOLUTION=1024
```

The Worker shells:

```bash
python inference.py --image INPUT.png --output hero.glb --low_vram --resolution 1024
```

### TripoSR — lightweight baseline

Official project:
https://github.com/VAST-AI-Research/TripoSR

TripoSR is MIT licensed and the official repo supports GLB output. Install its
CUDA/PyTorch requirements in a separate environment, then:

```bash
export TRIPOSR_ROOT=/opt/TripoSR
export TRIPOSR_MC_RESOLUTION=256
```

The Worker shells:

```bash
python run.py INPUT.png --output-dir OUTPUT --model-save-format glb
```

## Start the Worker

Install only the HTTP adapter dependencies into the same environment that can
run your selected 3D engine:

```bash
pip install -r workers/hero_asset_worker/requirements.txt
export HERO_WORKER_TOKEN='choose-a-secret'
uvicorn workers.hero_asset_worker.worker:app --host 0.0.0.0 --port 8188
```

Health check:

```bash
curl http://127.0.0.1:8188/health
```

## Connect Mini Utopia

In the Studio environment:

```bash
HERO_ASSET_WORKER_URL=http://GPU-HOST:8188
HERO_ASSET_WORKER_TOKEN=choose-a-secret
HERO_ASSET_MODEL=pixal3d
HERO_ASSET_TIMEOUT_SECONDS=1800
HERO_ASSET_MAX_PER_WORLD=1
```

Reboot Streamlit and re-render a World Preview. During the Build Experience a
new stage appears:

`🐋 正在把主要 Hero 从 Preview 转成真正的 3D GLB…`

For the current spike only the largest major organic Hero is generated. Other
objects retain the deterministic procedural fallback.

## Why a separate Worker?

Pixal3D/TRELLIS/TripoSR bring large PyTorch/CUDA dependency trees. Keeping them
out of the Streamlit process means:

- the Creator UI remains lightweight,
- model environments may use different CUDA/PyTorch versions,
- Pixal3D and TripoSR are replaceable behind one HTTP contract,
- a local GPU, LAN GPU workstation, or cloud GPU can all use the same Studio,
- a failed experimental Hero generation does not break World/Blueprint data.

## Current spike transport

ObjectStorage remains private. For the first spike, the Streamlit server reads
the generated GLB and embeds it as a data URI into the Explore HTML. This proves
the end-to-end pipeline without adding public buckets or signed URLs.

For production, replace data-URI transport with short-lived signed asset URLs;
RenderSpec does not need to change.
