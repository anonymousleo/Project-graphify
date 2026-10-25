---
name: project-graphify
description: Build or update a source-backed knowledge graph of the current Claude Project's conversations, goals, decisions, files, code, experiments, verified results, blockers, and remaining work. Use to consolidate project history, preserve context, or prepare for a new chat after the conversation becomes long.
---

# Project Graphify

Build and refresh an evidence-backed record of the **current** Claude Project. This is the *writer*; Project Graphify Reader is the recovery skill.

## 1. Establish access and coverage

Confirm the project identity. Check whether native Claude past-chat search is actually available and enabled. Search is relevance-based and does **not** prove every message was read. Never invent an API to enumerate all project chats. If search is unavailable, request exported or pasted conversation records. To claim exhaustive coverage, require a complete export or independently verified list of included chats.

Check which persistent destinations really exist: Claude project memory, Project Knowledge / project Library, connected user storage, or downloadable files. The plugin has no privileged write access to Claude's internal memory database. Memory is a compact index; the complete graph belongs in a persistent file.

## 2. Collect separate evidence families

Follow [references/retrieval-playbook.md](references/retrieval-playbook.md). Search/review the project's **origin and why**, research or engineering goals, frozen constraints, decisions, completed checkpoints, failures, measurements, file/code paths and purposes, blockers, active tasks, recent conversation changes, and contradictions.

For every claim record an available conversation identifier or title, message/date, literal supporting excerpt, and evidence status:

- `observed`: execution output, inspected file, hash, or directly verified artifact.
- `user_reported`: statement supplied by the user without independent corroboration.
- `assistant_proposed`: a suggestion, draft path, expected command, or planned result.
- `inferred`: reasonable deduction, explicitly uncertain.
- `unknown`: not established by accessible evidence.

Never turn an assistant's proposed command into a completed action. A path appearing in a chat is *historical information*, not proof that it still exists. Preserve exact metrics with model, dataset, split, @K, seed, unit, and run ID. Never mix validation with test results.

## 3. Construct and update the graph

Use [references/schema.md](references/schema.md) and the bundled `tools/project_graphify.py` if a compatible execution environment is actually available. Project, Goal, Decision, Requirement, File, Function, Environment, Experiment, Result, Metric, Task, Blocker, Dataset, Source, Conversation and Message are distinct node types. Preserve `calls`/`imports` and other native Graphify relations when an actual code graph is merged.

Deduplicate source facts by stable content hash. Retain contradictory claims with separate provenance; `supersedes` links require a reasoned chronology, not mere recency. Missing evidence never becomes success by default.

An authorized environment can ingest structured claims and normalized chat exports with the CLI; the original Graphify Python engine is bundled for genuine AST code analysis. In Claude browser chat, rely on native search and available file/code tools; do not claim the bundled engine ran merely because it is installed.

## 4. Persist a useful continuation

Produce or refresh `graph.json`, `GRAPH_REPORT.md`, `PROJECT_MEMORY.md`, `CONTINUATION.md`, and `evidence.jsonl` where tools allow. A graph may be saved as Project Knowledge if the current host actually supports that write; otherwise offer the files for download and ask the user to add them to Project Knowledge.

Ask Claude to remember **only** a compact durable project digest (goal, constraints, current checkpoint, results index, graph artifact location, top blockers). Verify whether Claude actually saved it. Do not claim that a plugin can write arbitrary JSON into hidden memory topics or maintain an unlimited database there.

Update a coverage ledger with date, source count, earliest/latest accessible chat, retrieval topics, gaps, and `exhaustive=false` unless proven. At the end, recommend the **next single safe step**, not speculative execution.

## 5. Stop and report blockers

If no old chats or exports are visible, say so and provide the minimal export instructions. If sources conflict, preserve both. If a transcript contains credentials or personal secrets, redact before long-term persistence and ask before external sharing. Do not install packages, clone repositories, run training, change project files, or activate external connectors beyond the user's authorization.

### Handoff

Give Project Graphify Reader the current graph identity, latest verified state, explicit missing history, and next-action evidence. The reader must always check whether the saved snapshot is stale.
