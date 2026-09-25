---
name: end-session
description: End a MediBot learning session - run quality checks, update the roadmap/session log/CLAUDE.md state/decisions, then commit, push the feature branch and open or update the PR. Use when the user says "end session", "wrap up", "let's stop for today", or asks to commit and raise a PR for the day's work.
---

# End a MediBot session

Invoking this skill is the user's request to commit, push and open a PR for the current feature branch.

## Live context (collected when this skill loads)
- Current branch: !`git branch --show-current`
- Changes: !`git status --short`
- Commits not on main: !`git log --oneline main..HEAD 2>/dev/null`
- Recent PRs (match headRefName to the current branch): !`gh pr list --repo Nainagerwani07/medibot-advanced-rag --state all --limit 5 --json number,headRefName,state,url`

## Steps

1. **Guard.** If the branch is `main`, stop and tell the user. Work must be on a feature branch.

2. **Quality checks.** Run them and report results truthfully. If something fails, fix it or tell the user;
   never skip it quietly.
   - `uv run --directory backend ruff check .` and `uv run --directory backend ruff format --check .`
   - `uv run --directory backend pytest` (exit code 5 means "no tests collected", which is fine early on; say so)
   - `pre-commit run --all-files`

3. **Update the project docs** (the next session depends on these):
   - `docs/ROADMAP.md`: set the Day's status (✅ done / 🟡 in progress) and add a session-log entry:
     `### Day N — YYYY-MM-DD` with **Done**, **Learned** (the concepts, in one line each),
     **Open items**, **Next**.
   - `docs/DECISIONS.md`: add a row for any decision made this session (what, alternatives, why).
   - `CLAUDE.md` "Current state": last completed, next step, code written so far.
   - `README.md` / `docs/ARCHITECTURE.md`: only if what we built changes what they say.

4. **Commit.** Stage specific paths (never `git add -A` blindly; check nothing from `data/`, `.env`
   or model caches is staged). Use a conventional message (`feat:`, `chore:`, `docs:`, `fix:`) with
   a body listing the main changes, ending with the Co-Authored-By attribution line.
   If a pre-commit hook fails, fix the cause and make a **new** commit (don't use `--no-verify`).

5. **Push and open or update the PR.**
   - `git push -u origin <branch>`
   - The remote uses an SSH host alias (`github-personal`) that gh can't map to GitHub, so gh needs
     `GH_REPO` (set in `.claude/settings.json`) and an explicit `--head <branch>`.
   - No PR yet: `gh pr create --base main --head <branch>` with a title like `Day N: <topic>` and a body that has
     **Summary**, **Why**, **Requirements covered** (R*/NF* IDs), and **How to verify**, ending with the
     "Generated with Claude Code" attribution line.
   - PR exists: the push updates it; mention the PR URL.
   - Don't merge. The user reviews and merges.

6. **Final summary to the user** (the checkpoint format): what was finished this session and the core
   reason for each piece, check results, the PR link, and what the next session starts with. Then stop.
