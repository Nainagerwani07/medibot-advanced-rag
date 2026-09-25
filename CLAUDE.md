# CLAUDE.md — session context for MediBot

Read this file at the start of every session. It holds the working rules and current state of the project.

## What this project is
MediBot: a secure healthcare assistant for "MediAssist Health Network" (Codebasics AI Engineering Bootcamp assignment).
Hybrid RAG (dense + BM25 in Qdrant) → cross-encoder rerank → Groq LLM, plus SQL RAG over SQLite, with
**RBAC enforced as a Qdrant metadata filter**. FastAPI backend, Next.js frontend.

- Requirements: `docs/REQUIREMENTS.md` (R1–R8, NF1–NF5; code should trace back to these IDs)
- Architecture: `docs/ARCHITECTURE.md`
- Decisions: `docs/DECISIONS.md` (don't reopen a decision unless the user asks; add new ones at the bottom)
- Progress + session log: `docs/ROADMAP.md` ← **check this first to know where we are**

## Working rules (from the user — follow them strictly)
1. **This is a learning project.** The user is a senior software engineer learning AI engineering (chunking, embeddings,
   transformers, vector DBs, RAG, Docling).
2. **Never write code without first explaining what we're about to build, why it's needed, and which requirement it serves.**
   Wait for the user's go-ahead when a step introduces a new concept.
3. Work **step by step**, about 2 hours per session, following the Day plan in `docs/ROADMAP.md`. Don't jump ahead to later days.
4. **Checkpoint format.** After finishing a block of work, do NOT end with questions or option menus. End with a
   **summary**: what is finished so far, and the core reason behind each piece. Then stop and wait for the user to
   review and give the next command. Don't start the next step on your own.
5. Prefer showing real output (print chunks, log scores, inspect payloads) over explaining in the abstract.
6. Retrieval goes through **qdrant-client directly**, not LangChain's vector-store wrapper (D3).
7. CPU-only machine: pick CPU-friendly models; Docling OCR off (D4).
8. Public repo: never commit secrets, `.env`, or the dataset. Commit only when the user asks.
9. **Git workflow: all work happens on feature branches, never directly on `main`.** Only the initial docs setup
   (Day 0) was pushed to `main`. Branch naming: `feature/day-<N>-<short-topic>` (e.g. `feature/day-1-env-setup`);
   use `fix/<topic>` or `docs/<topic>` for small non-Day changes. Merge to `main` via PR.

## Session start checklist
1. Read `docs/ROADMAP.md`: find the current Day and the last session-log entry.
2. Tell the user in 2–3 lines: where we left off, today's goal, the concepts we'll cover.
3. Explain the first step and why, then build.

## Session end checklist
1. Update the Day's status in `docs/ROADMAP.md` and add a session-log entry (done / learned / open items / next).
2. Record any new decision in `docs/DECISIONS.md`.
3. Update the "Current state" section below.
4. Suggest a commit message (don't commit unless asked).

## Current state
- **Last completed:** Day 1 — env setup, quality tooling, Qdrant, Groq check, data exploration
  (PR from `feature/day-1-env-setup`; check whether it's merged before branching for Day 2).
- **Next:** Day 2 — Docling parsing (`uv add docling` then; OCR off). Inspect structure of all 12 files.
- **Code written so far:** tooling only (backend/pyproject.toml, pre-commit, .claude hooks/skills, docker-compose).
  No application code yet; `backend/src/medibot/__init__.py` is empty.
- **Open items:** see the Day 1 entry in `docs/ROADMAP.md`.

## Environment facts
- Dataset zip (outside repo): `/home/naina/Downloads/codebasics/29-aug-session-5/Medibot_Assignment_Resources/mediassist_data.zip`
  → contains `billing/ clinical/ equipment/ general/ nursing/ db/mediassist.db`
- Original brief: same folder, `MediBot_Assignment_Instructions.pdf` / `Medibot_Assignment_Instruction.md`
- Reference notebook from the bootcamp (uses LangChain; for reference only): `/home/naina/Downloads/codebasics/29-aug-session-5/Session_5_Resource_1/advanced__RAG.ipynb`
- Unzipped dataset (gitignored): `data/mediassist_data/{general,clinical,nursing,billing,equipment,db}/`
- Qdrant: `docker compose up -d` → http://localhost:6333 (dashboard at /dashboard)
- Groq models on our key: `openai/gpt-oss-120b`, `openai/gpt-oss-20b` (no Llama 70B). gpt-oss reasons internally,
  so hidden tokens count toward `max_tokens`; keep it generous or answers come back empty.
- Never read or print `.env`. Load it into the environment only (`set -a; . ./.env; set +a`).
- gh: remote uses SSH alias `github-personal`; gh needs `GH_REPO=Nainagerwani07/medibot-advanced-rag`
  (set in `.claude/settings.json`) and explicit `--head <branch>`.
- Platform: Linux, CPU only (12 cores, 23 GB RAM), Docker available, system Python 3.10 (uv provides 3.12), no `jq`.
