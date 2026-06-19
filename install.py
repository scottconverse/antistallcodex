#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parent
SKILL_SRC = ROOT / "skill" / "antistall-codex"


def codex_home() -> pathlib.Path:
    import os

    return pathlib.Path(os.environ.get("CODEX_HOME") or pathlib.Path.home() / ".codex").resolve()


def copy_skill(target_home: pathlib.Path) -> pathlib.Path:
    dst = target_home / "skills" / "antistall-codex"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(SKILL_SRC, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return dst


def main() -> int:
    if not SKILL_SRC.is_dir():
        print(f"missing packaged skill: {SKILL_SRC}", file=sys.stderr)
        return 2

    home = codex_home()
    home.mkdir(parents=True, exist_ok=True)
    skill_dst = copy_skill(home)
    print(f"installed skill -> {skill_dst}")

    helper = skill_dst / "scripts" / "antistall.py"
    result = subprocess.run([sys.executable, str(helper), "install-hook"], check=False)
    if result.returncode != 0:
        return result.returncode

    print("\nNext:")
    print("  1. In Codex Desktop, open /hooks and trust the AntiStallCodex hook if prompted.")
    print("  2. Use `AntistallON: <goal>` in a project thread to arm it.")
    print("  3. Use `AntistallOFF` to disarm it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
