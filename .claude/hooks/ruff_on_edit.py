#!/usr/bin/env python3
"""PostToolUse hook: after Claude edits a Python file in backend/, run ruff on it.

`ruff check --fix` auto-fixes lint issues (e.g. import order); `ruff format` formats the file.
Remaining lint errors are reported back to Claude (exit 2 -> stderr is fed to the model)
so they get fixed right away instead of at commit time.
"""

import json
import subprocess
import sys
from pathlib import Path

payload = json.load(sys.stdin)
file_path = payload.get("tool_input", {}).get("file_path", "")
path = Path(file_path)

project = Path(payload.get("cwd") or ".").resolve()
backend = next((p for p in [project, *project.parents] if (p / "backend").is_dir()), project)
backend = backend / "backend"

if path.suffix != ".py" or backend not in path.resolve().parents:
    sys.exit(0)

ruff = ["uv", "run", "--directory", str(backend), "ruff"]
subprocess.run([*ruff, "format", str(path)], capture_output=True)
check = subprocess.run([*ruff, "check", "--fix", str(path)], capture_output=True, text=True)

if check.returncode != 0:
    print(
        f"ruff found issues it could not auto-fix in {path}:\n{check.stdout}",
        file=sys.stderr,
    )
    sys.exit(2)
sys.exit(0)
