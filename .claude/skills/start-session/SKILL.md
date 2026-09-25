---
name: start-session
description: Start a MediBot learning session - recap where we left off, set up the day's feature branch, and introduce today's first concept. Use when the user says "start Day N", "continue", "let's begin", or opens a new session on this project.
---

# Start a MediBot session

## Live context (collected when this skill loads)
- Current branch: !`git branch --show-current`
- Working tree: !`git status --short | head -20`
- Recent commits: !`git log --oneline -5`
- Recent PRs: !`gh pr list --repo Nainagerwani07/medibot-advanced-rag --state all --limit 5 --json number,headRefName,state,url`
- Latest session-log entry:
!`awk '/^### Day/{buf=""} {buf=buf"\n"$0} END{print buf}' docs/ROADMAP.md`

## Steps

1. **Read state.** Read `CLAUDE.md` ("Current state" + working rules) and `docs/ROADMAP.md`
   (Day table + latest log entry above). Work out today's Day number N and its topic.
   If the latest log says the previous Day is unfinished, today continues that Day.

2. **Check git before doing anything.**
   - Uncommitted changes from a previous session: tell the user what they are; don't discard them.
   - Previous Day's PR still open: tell the user; continuing on top of it is fine but say so.
   - Previous PR merged: `git switch main && git pull`, then branch.
   - Create or switch to `feature/day-<N>-<short-topic>` (topic from the ROADMAP row, kebab-case).
     Never work on `main`.

3. **Recap for the user (short, 3–5 lines):**
   - Where we left off (last Day finished, open items from the log)
   - Today's goal and "done when" from the ROADMAP row
   - The concepts we'll learn today

4. **Explain the first step before any code:** what we're building, why it's needed, and which
   requirement ID (R*/NF*) it serves (`docs/REQUIREMENTS.md`). Then wait for the user's go-ahead.

## Rules that apply all session
- Explain before coding; show real output; one step at a time.
- After each block of work, end with a **summary** (what's done + core reason for each piece),
  then wait. No questions or option menus at checkpoints.
- Add dependencies with `uv add` only when a step first needs them, and say why.
