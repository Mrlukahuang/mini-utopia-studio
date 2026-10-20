#!/bin/sh
# For the existing code's verified /tmp/godot binary path on ARM64.
set -eu
test "$(id -u)" = 10001
mkdir -p /tmp/godot
cp /opt/godot/Godot_v4.7.2-stable_linux.arm64 /tmp/godot/
chmod 755 /tmp/godot/Godot_v4.7.2-stable_linux.arm64
cmp /opt/godot/Godot_v4.7.2-stable_linux.arm64 /tmp/godot/Godot_v4.7.2-stable_linux.arm64
/tmp/godot/Godot_v4.7.2-stable_linux.arm64 --headless --version >/dev/null
exec "$@"
