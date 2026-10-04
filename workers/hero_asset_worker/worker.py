from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import Response


app = FastAPI(title="Mini Utopia Hero Asset Worker", version="0.1")


def _authorized(authorization: str | None) -> bool:
    expected = os.getenv("HERO_WORKER_TOKEN", "").strip()
    if not expected:
        return True
    return authorization == f"Bearer {expected}"


def _python() -> str:
    return os.getenv("HERO_PYTHON", sys.executable)


def _engine_root(model: str) -> Path:
    if model == "pixal3d":
        value = os.getenv("PIXAL3D_ROOT", "").strip()
    elif model == "triposr":
        value = os.getenv("TRIPOSR_ROOT", "").strip()
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported model: {model}")
    if not value:
        raise HTTPException(
            status_code=503,
            detail=f"{model} root is not configured on this GPU Worker.",
        )
    root = Path(value).expanduser().resolve()
    if not root.exists():
        raise HTTPException(
            status_code=503,
            detail=f"Configured {model} root does not exist: {root}",
        )
    return root


def _run_pixal3d(*, root: Path, image_path: Path, output_path: Path) -> None:
    command = [
        _python(),
        str(root / "inference.py"),
        "--image",
        str(image_path),
        "--output",
        str(output_path),
    ]
    if os.getenv("PIXAL3D_LOW_VRAM", "1").lower() not in {"0", "false", "no"}:
        command.append("--low_vram")
    resolution = os.getenv("PIXAL3D_RESOLUTION", "1024").strip()
    if resolution:
        command.extend(["--resolution", resolution])
    subprocess.run(
        command,
        cwd=root,
        check=True,
        timeout=float(os.getenv("HERO_INFERENCE_TIMEOUT_SECONDS", "1800")),
    )


def _run_triposr(*, root: Path, image_path: Path, output_dir: Path) -> Path:
    command = [
        _python(),
        str(root / "run.py"),
        str(image_path),
        "--output-dir",
        str(output_dir),
        "--model-save-format",
        "glb",
        "--mc-resolution",
        os.getenv("TRIPOSR_MC_RESOLUTION", "256"),
    ]
    subprocess.run(
        command,
        cwd=root,
        check=True,
        timeout=float(os.getenv("HERO_INFERENCE_TIMEOUT_SECONDS", "1800")),
    )
    return output_dir / "0" / "mesh.glb"


@app.get("/health")
def health():
    configured = {
        "pixal3d": bool(os.getenv("PIXAL3D_ROOT", "").strip()),
        "triposr": bool(os.getenv("TRIPOSR_ROOT", "").strip()),
    }
    return {
        "ok": True,
        "configured": configured,
        "cuda_visible_devices": os.getenv("CUDA_VISIBLE_DEVICES", ""),
    }


@app.post("/generate")
async def generate(
    image: UploadFile = File(...),
    model: str = Form("pixal3d"),
    element_id: str = Form("hero"),
    appearance_json: str = Form("{}"),
    authorization: str | None = Header(default=None),
):
    if not _authorized(authorization):
        raise HTTPException(status_code=401, detail="Invalid Hero Worker token.")

    model = model.strip().lower()
    root = _engine_root(model)
    try:
        appearance = json.loads(appearance_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid appearance_json.") from exc

    payload = await image.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Input image is empty.")

    safe_id = "".join(
        char if char.isalnum() or char in {"-", "_"} else "_"
        for char in element_id
    )[:80] or "hero"

    with tempfile.TemporaryDirectory(prefix="mini-utopia-hero-") as temp_dir:
        work = Path(temp_dir)
        image_path = work / f"{safe_id}.png"
        image_path.write_bytes(payload)
        (work / "appearance.json").write_text(
            json.dumps(appearance, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        try:
            if model == "pixal3d":
                output_path = work / "hero.glb"
                _run_pixal3d(
                    root=root,
                    image_path=image_path,
                    output_path=output_path,
                )
            else:
                output_path = _run_triposr(
                    root=root,
                    image_path=image_path,
                    output_dir=work / "triposr-output",
                )
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(
                status_code=504,
                detail=f"{model} inference timed out.",
            ) from exc
        except subprocess.CalledProcessError as exc:
            raise HTTPException(
                status_code=500,
                detail=f"{model} inference failed with exit code {exc.returncode}.",
            ) from exc

        if not output_path.exists():
            raise HTTPException(
                status_code=500,
                detail=f"{model} did not produce the expected GLB: {output_path}",
            )
        glb = output_path.read_bytes()
        if not glb:
            raise HTTPException(status_code=500, detail="Generated GLB is empty.")

    return Response(
        content=glb,
        media_type="model/gltf-binary",
        headers={
            "X-Hero-Model": model,
            "X-Hero-Element": safe_id,
        },
    )
