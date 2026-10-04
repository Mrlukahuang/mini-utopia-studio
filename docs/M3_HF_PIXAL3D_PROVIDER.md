# M3.6 Hugging Face Pixal3D Direct Provider

Mini Utopia can use the public `TencentARC/Pixal3D` Hugging Face Space
directly with an authenticated Hugging Face account. A separately deployed GPU
Worker is no longer required for the normal family/development setup.

## Current public Space contract

Verified against the public Space on 2026-10-05.

The Space is a Gradio Server application and exposes:

1. `/preprocess`
2. `/generate_3d`
3. `/extract_glb_api`

Mini Utopia uses the official `gradio_client` package and supplies `HF_TOKEN`
to `Client(..., token=...)`. This attributes ZeroGPU usage to the authenticated
Hugging Face account.

Source:

- https://huggingface.co/spaces/TencentARC/Pixal3D
- https://huggingface.co/docs/hub/spaces-api-endpoints

## Provider priority

```text
HERO_ASSET_WORKER_URL configured
        ↓ yes
Self-hosted HttpHeroAssetProvider

otherwise

HF_TOKEN configured
        ↓ yes
HuggingFacePixal3DProvider

otherwise

Procedural fallback only
```

The explicit Worker remains available for a future commercial deployment or
another model. Hugging Face is the default low-ops provider during the current
stage.

## Secrets

Never commit the actual token.

Runtime secret:

```text
HF_TOKEN=hf_...
```

The project also supports:

```text
HF_HERO_SPACE_ID=TencentARC/Pixal3D
HF_PIXAL3D_RESOLUTION=1024
HF_PIXAL3D_DECIMATION_TARGET=300000
HF_PIXAL3D_TEXTURE_SIZE=2048
HF_PIXAL3D_SEED=42
```

The 1024 / 300k / 2048 defaults are Mini Utopia's first web-oriented quality
profile. They deliberately trade some maximum reconstruction detail for smaller
GLB assets and lower runtime cost. The profile can be raised to 1536 / 1M /
4096 for a signature Hero benchmark without changing the provider contract.

## Generation sequence

```text
World Preview
  ↓ Vision bbox crop
/preprocess
  ↓ foreground-prepared image
/generate_3d
  ↓ state_path
/extract_glb_api
  ↓
validated GLB
  ↓
Reusable Asset Library
  ↓
WorldRenderSpec
  ↓
Three.js
```

The provider uses a deterministic seed and its cache identity includes:

- Space ID
- generation resolution
- decimation target
- texture size
- seed

Changing the quality profile therefore invalidates the old generation
fingerprint rather than accidentally returning a lower-quality cached asset.

## Global generated-Hero reuse

M3.6 promotes generated Hero GLBs into the persistent Reusable Asset Library.

The exact generation fingerprint combines:

- provider/quality identity
- Preview crop bytes
- structured ObjectAppearanceSpec

If another World later requests the exact same generated input, Mini Utopia can
reuse the global GLB without another ZeroGPU call.

This is intentionally stricter than semantic reuse. A merely similar
`sky_whale` should not silently become an old whale if the child created a
different appearance. Broader semantic reuse will require an explicit creator
choice or a future similarity/asset-selection system.

## Failure behavior

Hugging Face / ZeroGPU is a quality upgrade, not a World creation dependency.

If Space/API/quota generation fails:

- the exception is recorded in Hero diagnostics
- existing procedural nodes remain
- Explore still opens
- no Blueprint logic changes

That preserves the core product rule: GPU availability must never prevent a
child from entering a created World.
