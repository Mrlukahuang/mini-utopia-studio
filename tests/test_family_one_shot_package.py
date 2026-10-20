"""#471 lightweight CI smoke of the runnable one-shot Worker package.

The real Docker named-volume/bind trial is deliberately NOT run against CI
or production data; it requires a separately isolated Docker host.
"""
import ast
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_one_shot_scripts_parse_before_any_container_runs():
    for shell, file in (
        ("bash", "family_one_shot.sh"),
        ("sh", "family_one_shot_entrypoint.sh"),
    ):
        subprocess.run([shell, "-n", str(ROOT / file)], check=True)
    ast.parse((ROOT / "family_one_shot_trial.py").read_text())


def test_one_shot_image_is_explicitly_private_and_contains_existing_worker():
    recipe = (ROOT / "Dockerfile.family-one-shot").read_text()
    ignored = (ROOT / "Dockerfile.family-one-shot.dockerignore").read_text().splitlines()
    entry = (ROOT / "family_one_shot_entrypoint.sh").read_text()
    assert "COPY studio /app/studio" in recipe
    assert "COPY godot /app/godot" in recipe
    assert "sunny_meadow.wav" in recipe
    assert "sha256sum -c -" in recipe
    assert "USER 10001:10001" in recipe
    # Build context comes from git archive under umask 077: files may be 0600.
    # Explicitly make only packaged public code readable, then build-probe as UID10001.
    assert "chmod -R a+rX /app/studio /app/godot /app/tests" in recipe
    assert recipe.index("chmod -R a+rX") < recipe.index("USER 10001:10001")
    assert "RUN test -r /app/tests/family_one_shot_entrypoint.sh" in recipe
    assert "test -r /app/studio/family_render_queue.py" in recipe
    assert "test -r /app/godot/project.godot" in recipe
    assert "studio.family_render_queue" in recipe
    assert "run-one" in recipe
    assert "tests" not in ignored and "godot" not in ignored
    assert all(item in ignored for item in (
        ".git", "data", ".env", "deploy/family/web", "deploy/family/backups",
    ))
    assert "exec \"$@\"" in entry and "export PATH=" in entry


def test_trial_restricts_real_worker_and_requires_api_readonly_media_view():
    script = (ROOT / "family_one_shot.sh").read_text()
    trial = (ROOT / "family_one_shot_trial.py").read_text()
    for flag in (
        "--network none", "--read-only", "--user 10001:10001",
        "--cap-drop ALL", "--security-opt no-new-privileges",
        "--cpus 4", "--memory 4g", "--memory-swap 4g",
        "--pids-limit 256", "/tmp:rw,exec,nosuid",
    ):
        assert flag in script
    assert script.count("dst=/movies,readonly") == 2
    assert "type=volume,src=$VOLUME,dst=/data" in script
    assert "--godot-project /app/godot --store-root /movies run-one" in script
    assert "NO_PRODUCTION_DB_ACCESS" in script
    assert "SYNTHETIC_API_RO_WORKER_RW_RELEASE_OWNER_REVOKE_PASS" in trial
    assert "PRAGMA journal_mode=WAL" in trial
    assert "private_mp4_for_download" in trial
