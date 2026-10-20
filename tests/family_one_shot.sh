#!/usr/bin/env bash
# #471. Only synthetic docker trial; production action is deliberately absent.
set -Eeuo pipefail
umask 077
if [[ "${1:-}" == plan ]]; then
  DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
  python3 "$DIR/family_worker_mount_review.py"
  echo 'NO_WRITE / NO_WORKER / NO_PRODUCTION_DB_ACCESS'
  exit 0
fi
[[ "${1:-}" == synthetic && $# == 2 && "$2" =~ ^[0-9a-f]{40}$ ]] || {
  echo 'Usage: bash tests/family_one_shot.sh synthetic <full-public-git-SHA>' >&2; exit 2;
}
SHA="$2"
test "$(uname -m)" = arm64
for cmd in git tar docker; do command -v "$cmd" >/dev/null; done
docker info --format '{{.OSType}}/{{.Architecture}}' | grep -Eq '^linux/(arm64|aarch64)$'
WORK="$(mktemp -d "${TMPDIR:-/tmp}/mu471-work.XXXXXXXX")"
REPORT="$(mktemp -d "${TMPDIR:-/tmp}/mu471-report.XXXXXXXX")"
chmod 700 "$WORK" "$REPORT"
ID="$(basename "$WORK" | tr '[:upper:]' '[:lower:]')"
IMAGE="mu471-one-shot:$ID"
VOLUME="mu471-volume-$ID"
NAME="mu471-$ID"
MOVIES="$WORK/movies"
mkdir -m 700 "$MOVIES"
HOST_UID="$(id -u)"
HOST_GID="$(id -g)"
OWN_VOLUME=0
OWN_IMAGE=0
# Restricted to our synthetic paths; initializer alone uses CAP_CHOWN/FOWNER.
chown_synthetic() {
  docker run --rm --platform linux/arm64 --network none --read-only \
    --user 0:0 --cap-drop ALL --cap-add CHOWN --cap-add FOWNER \
    --security-opt no-new-privileges --memory 256m --pids-limit 64 \
    --mount "type=volume,src=$VOLUME,dst=/data" \
    --mount "type=bind,src=$MOVIES,dst=/movies" \
    --entrypoint /bin/sh "$IMAGE" -ec \
    "chown -R $1:$2 /data /movies; chmod 700 /data /movies"
}
cleanup() {
  rc=$?
  trap - EXIT
  for kind in seed worker api; do
    docker container rm -f "$NAME-$kind" >/dev/null 2>&1 || true
  done
  if (( OWN_VOLUME && OWN_IMAGE )); then
    chown_synthetic "$HOST_UID" "$HOST_GID" >/dev/null 2>&1 || true
  fi
  (( OWN_VOLUME )) && docker volume rm "$VOLUME" >/dev/null 2>&1 || true
  (( OWN_IMAGE )) && docker image rm "$IMAGE" >/dev/null 2>&1 || true
  rm -rf -- "$WORK" || true
  printf 'SYNTHETIC_EXIT=%s\nLOCAL_REPORT=%s\n' "$rc" "$REPORT"
  exit "$rc"
}
trap cleanup EXIT
git clone -q --no-checkout https://github.com/Mrlukahuang/mini-utopia-studio.git "$WORK/public"
git -C "$WORK/public" checkout -q --detach "$SHA"
test "$(git -C "$WORK/public" rev-parse HEAD)" = "$SHA"
mkdir "$WORK/context"
git -C "$WORK/public" archive "$SHA" | tar -xf - -C "$WORK/context"
for path in tests/Dockerfile.family-one-shot tests/Dockerfile.family-one-shot.dockerignore \
  tests/family_one_shot_trial.py godot/project.godot \
  godot/assets/audio/cc0_music/sunny_meadow.wav studio/family_render_queue.py; do
  test -f "$WORK/context/$path"
done
BASE='python:3.12.12-slim-bookworm'
GODOT_SHA='5dd0d86405cf7e8adf79fb6377b38ba682a2846cb378ffe5364f38c01ad29b9d'
docker pull --platform linux/arm64 "$BASE" >/dev/null
test "$(docker image inspect -f '{{.Architecture}}' "$BASE")" = arm64
BASE_REF="$(docker image inspect -f '{{index .RepoDigests 0}}' "$BASE")"
[[ "$BASE_REF" == *@sha256:* ]] || { echo 'Unpinned base image' >&2; exit 1; }
printf 'source=%s\nbase=%s\ngodot_zip_sha256=%s\n' \
  "$SHA" "$BASE_REF" "$GODOT_SHA" > "$REPORT/manifest.txt"
! docker image inspect "$IMAGE" >/dev/null 2>&1 || exit 1
docker build --platform linux/arm64 --progress plain \
  --build-arg "BASE_REF=$BASE_REF" --build-arg "GODOT_ZIP_SHA=$GODOT_SHA" \
  -f "$WORK/context/tests/Dockerfile.family-one-shot" -t "$IMAGE" \
  "$WORK/context" 2>&1 | tee "$REPORT/build.log"
OWN_IMAGE=1
! docker volume inspect "$VOLUME" >/dev/null 2>&1 || exit 1
docker volume create "$VOLUME" >/dev/null
OWN_VOLUME=1
chown_synthetic 10001 10001 >/dev/null
COMMON=(--rm --platform linux/arm64 --network none --read-only
  --user 10001:10001 --cap-drop ALL --security-opt no-new-privileges
  --cpus 4 --memory 4g --memory-swap 4g --pids-limit 256
  --tmpfs /tmp:rw,exec,nosuid,size=1536m,mode=1777
  --tmpfs /scratch:rw,nosuid,noexec,size=256m,mode=1777
  --shm-size 256m --mount "type=volume,src=$VOLUME,dst=/data")
docker run --name "$NAME-seed" "${COMMON[@]}" \
  --mount "type=bind,src=$MOVIES,dst=/movies,readonly" "$IMAGE" \
  python /app/tests/family_one_shot_trial.py seed 2>&1 | tee "$REPORT/seed.log"
docker run --name "$NAME-worker" "${COMMON[@]}" \
  --mount "type=bind,src=$MOVIES,dst=/movies" "$IMAGE" \
  python -m studio.family_render_queue --db /data/studio.db \
  --godot-project /app/godot --store-root /movies run-one 2>&1 | tee "$REPORT/worker.log"
docker run --name "$NAME-api" "${COMMON[@]}" \
  --mount "type=bind,src=$MOVIES,dst=/movies,readonly" "$IMAGE" \
  python /app/tests/family_one_shot_trial.py verify 2>&1 | tee "$REPORT/api.log"
echo WORKER_BUNDLE_SYNTHETIC_TOPOLOGY_PASS
