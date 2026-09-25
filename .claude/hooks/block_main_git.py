#!/usr/bin/env python3
"""PreToolUse hook: block `git commit` / `git push` that would land on main.

Claude Code sends the tool call as JSON on stdin. Exit code 2 blocks the call and
stderr is shown to Claude as the reason. Exit 0 allows it.
"""

import json
import re
import subprocess
import sys

PROTECTED = "main"

payload = json.load(sys.stdin)
command = payload.get("tool_input", {}).get("command", "")

# Look at each sub-command separately so `git switch -c x && git commit` is judged correctly.
parts = re.split(r"&&|\|\||;|\n", command)
git_commit = any(re.search(r"\bgit\b.*\bcommit\b", p) for p in parts)
git_push = [p for p in parts if re.search(r"\bgit\b.*\bpush\b", p)]

if not git_commit and not git_push:
    sys.exit(0)

branch = subprocess.run(
    ["git", "branch", "--show-current"],
    capture_output=True,
    text=True,
    cwd=payload.get("cwd"),
).stdout.strip()

# A command that switches branches first (git switch/checkout) is judged by where it ends up,
# which we can't know in advance; only block when we're on main and not switching away.
switches_away = re.search(r"\bgit\s+(switch|checkout)\b", command)

reasons = []
if branch == PROTECTED and not switches_away:
    reasons.append(f"you are on '{PROTECTED}'")
if any(re.search(rf"(\s|:){PROTECTED}(\s|$)", p) for p in git_push):
    reasons.append(f"the push targets '{PROTECTED}'")

if reasons:
    print(
        f"Blocked: {' and '.join(reasons)}. Project rule (CLAUDE.md): all work goes on "
        "feature branches (feature/day-<N>-<topic>) and reaches main via PR.",
        file=sys.stderr,
    )
    sys.exit(2)
sys.exit(0)
