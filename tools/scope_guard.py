"""PR scope guard: mechanical anti-drift checks (see AGENTS.md §2–§4).

Usage (CI): python tools/scope_guard.py <base_sha> <head_sha>
PR body is read from the PR_BODY environment variable.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

MAX_LINES = 800
ALLOWED_NEW_DOCS = {"docs/V1_PLAN.md"}
ASSET_SUFFIXES = (
    ".png", ".jpg", ".jpeg", ".webp", ".glb", ".gltf", ".bin", ".ogg",
    ".wav", ".mp3", ".mp4", ".import", ".tres", ".res", ".ttf", ".otf",
)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    ).stdout


def field(body: str, label: str) -> str:
    match = re.search(rf"{label}[:：][ \t]*(.*)", body)
    return match.group(1).strip() if match else ""


def main(base: str, head: str) -> int:
    body = os.environ.get("PR_BODY", "")
    has_amend = bool(re.search(r"\bA-\d{3}\b", body))
    errors: list[str] = []

    if not field(body, "任务 ID"):
        errors.append("PR 描述缺少『任务 ID：』（必须来自 docs/V1_PLAN.md）")
    if not field(body, "孩子可见变化"):
        errors.append("PR 描述缺少『孩子可见变化：』")

    added = git("diff", "--name-only", "--diff-filter=A", base, head).split()
    new_docs = [
        p for p in added
        if p.startswith("docs/") and p.endswith(".md")
        and p not in ALLOWED_NEW_DOCS and not p.startswith("docs/archive/")
    ]
    if new_docs and not has_amend:
        errors.append(
            "新增文档需要 AMEND 编号（A-xxx）：" + ", ".join(new_docs)
        )

    total = 0
    for line in git("diff", "--numstat", base, head).splitlines():
        adds, dels, path = line.split("\t", 2)
        if adds == "-" or path.endswith(ASSET_SUFFIXES):
            continue
        total += int(adds) + int(dels)
    if total > MAX_LINES and not has_amend:
        errors.append(
            f"改动 {total} 行，超过 {MAX_LINES} 行上限。请拆分 PR，"
            "或在 AMEND.md 说明并在 PR 描述中引用 A-xxx"
        )

    print(f"scope_guard: {total} changed lines, {len(added)} added files")
    for err in errors:
        print(f"::error::{err}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
