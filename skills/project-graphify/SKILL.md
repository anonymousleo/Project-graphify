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

For every claim record an available conversation identifier or title, message/date, **source-derived** supporting excerpt, and evidence status:

- `observed`: execution output, inspected file, hash, or directly verified artifact.
- `user_reported`: statement supplied by the user without independent corroboration.
- `assistant_proposed`: a suggestion, draft path, expected command, or planned result.
- `inferred`: reasonable deduction, explicitly uncertain.
- `unknown`: not established by accessible evidence.

Never turn an assistant's proposed command into a completed action. A path appearing in a chat is *historical information*, not proof that it still exists. Preserve exact metrics with model, dataset, split, @K, seed, unit, and run ID. Never mix validation with test results.

**Never manufacture evidence.** A builder-generated purpose/description is not a quotation from a chat. Copy exact short excerpts only when the underlying source text is actually accessible, and label them `excerpt_kind=verbatim_unverified` unless independently matched. Label paraphrases `excerpt_kind=derived_summary`; unsupported claims should have missing/unknown evidence and an explicit gap. Do not present third-person assistant summaries as direct user statements. Preserve original evidence rather than raising confidence to make a cleaner report.

Treat account-wide memory and information from another Project as **external evidence** (`source_scope=external_account_memory`), not part of the current Project by default. Never declare the project's status or measured result resolved using an unrelated dataset or a synthetic-data inference. Record the scope and request confirmation before adopting it.

## 3. Construct and update the graph

Use [references/schema.md](references/schema.md) and the bundled `tools/project_graphify.py` if a compatible execution environment is actually available. Project, Goal, Decision, Requirement, File, Function, Environment, Experiment, Result, Metric, Task, Blocker, Dataset, Source, Conversation and Message are distinct node types. Preserve `calls`/`imports` and other native Graphify relations when an actual code graph is merged.

Use schema `project-graphify/v1`. Record relationships as directed `edges` (and an identical `links` compatibility alias if using the CLI). **Experiment → generated → Result**, and **Task/Experiment/Decision → failed_due_to → Blocker**. Validate both endpoints exist. A result does not generate the experiment that produced it. `status=accessible` on a Conversation means content was actually retrieved; use `metadata_only` for a title/URL without usable messages. Never mark `exhaustive=true` merely because searches stopped returning new chats.

Deduplicate source facts by stable content hash. Retain contradictory claims with separate provenance; `supersedes` links require a reasoned chronology, not mere recency. Missing evidence never becomes success by default.

Store every numerical Result by model, dataset, split, metric (and K where applicable), seed, run/checkpoint, unit and protocol when available. An aggregate/range or an unscoped historical statement stays narrative and must be **flagged incomplete**, not filled with guessed fields. Preserve measured negative results and failed experiments. For File nodes, retain the exact historical path or bare filename, purpose, inputs/outputs and source where known; never invent a parent directory or set `verified_on_disk=true` based only on chat claims.

An authorized environment can ingest structured claims and normalized chat exports with the CLI; the original Graphify Python engine is bundled for genuine AST code analysis. In Claude browser chat, rely on native search and available file/code tools; do not claim the bundled engine ran merely because it is installed.

## 4. Persist a useful continuation

Produce or refresh `graph.json`, `GRAPH_REPORT.md`, `PROJECT_MEMORY.md`, `CONTINUATION.md`, and `evidence.jsonl` where tools allow. **Read an existing graph before updating; preserve old node identities, provenance, and relationships.** Audit unresolved citations, duplicated facts, `generated` direction, evidence excerpts, incomplete Result fields, conversation coverage and cross-project scope. A validator warning count of zero is not evidence of quality if those checks were not run. Never silently overwrite the user's only copy of an existing graph; prepare versioned or recoverable output first. A graph may be saved as Project Knowledge if the current host actually supports that write; otherwise offer the files for download and ask the user to add them to Project Knowledge.

Ask Claude to remember **only** a compact durable project digest (goal, constraints, current checkpoint, results index, graph artifact location, top blockers). Verify whether Claude actually saved it. Do not claim that a plugin can write arbitrary JSON into hidden memory topics or maintain an unlimited database there.

Update a coverage ledger with date, source count, earliest/latest accessible chat, retrieval topics, gaps, and `exhaustive=false` unless proven. At the end, recommend the **next single safe step**, not speculative execution.

## 5. Stop and report blockers

If no old chats or exports are visible, say so and provide the minimal export instructions. If sources conflict, preserve both. If a transcript contains credentials or personal secrets, redact before long-term persistence and ask before external sharing. Do not install packages, clone repositories, run training, change project files, or activate external connectors beyond the user's authorization.

### Handoff

Give Project Graphify Reader the current graph identity, latest verified state, explicit missing history, and next-action evidence. The reader must always check whether the saved snapshot is stale.
