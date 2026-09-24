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
4. Prefer showing real output (print chunks, log scores, inspect payloads) over explaining in the abstract.
5. Retrieval goes through **qdrant-client directly**, not LangChain's vector-store wrapper (D3).
6. CPU-only machine: pick CPU-friendly models; Docling OCR off (D4).
7. Public repo: never commit secrets, `.env`, or the dataset. Commit only when the user asks.
8. **Git workflow: all work happens on feature branches, never directly on `main`.** Only the initial docs setup
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
- **Last completed:** Day 0 — requirements, architecture, docs.
- **Next:** Day 1 — environment setup (Python venv, deps, Qdrant via docker-compose, Groq key in `.env`), unzip the dataset
  into `data/`, look at the PDFs and the `mediassist.db` schema.
- **Code written so far:** none.

## Environment facts
- Dataset zip (outside repo): `/home/naina/Downloads/codebasics/29-aug-session-5/Medibot_Assignment_Resources/mediassist_data.zip`
  → contains `billing/ clinical/ equipment/ general/ nursing/ db/mediassist.db`
- Original brief: same folder, `MediBot_Assignment_Instructions.pdf` / `Medibot_Assignment_Instruction.md`
- Reference notebook from the bootcamp (uses LangChain; for reference only): `/home/naina/Downloads/codebasics/29-aug-session-5/Session_5_Resource_1/advanced__RAG.ipynb`
- Platform: Linux, CPU only, Docker available.
