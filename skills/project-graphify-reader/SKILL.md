---
name: project-graphify-reader
description: Restore prior Claude Project context in a new chat, resume research, recover project goals, historical code paths, verified experiments, achieved metrics, blockers and next steps by querying Project Graphify graph.json and evidence.jsonl. Use when continuing a project or asking what was done before.
---

# Project Graphify Reader

Read saved Project Graphify state and recover the **best-supported current context**. The graph may be incomplete, stale or internally inconsistent. Reading a summary alone does not demonstrate knowledge-graph retrieval. Never silently import decisions from other Projects.

## Recovery order

1. Identify the current Claude Project; never silently combine projects.
2. Read `CONTINUATION.md`, `PROJECT_MEMORY.md` and `GRAPH_REPORT.md` as *indexes*. Retrieve relevant raw nodes and relationships from **`graph.json`** and corroborating provenance from **`evidence.jsonl`** in Project Knowledge. State explicitly which files were actually read. Both `edges` and `links` are supported relationship fields; if both exist, their content must agree. Do not infer records from counts alone.
3. If no graph artifact exists, use Claude's native *project-scoped* past-chat search if available. Search by goal, latest progress, result, filename, blocker and next action; mark coverage as partial.
4. Inspect `coverage.exhaustive`, missing/unretrievable chats, graph build date, and any `warnings`. Check recent conversations for changes since the snapshot. A search index cannot prove that every historical message was retrieved. Report the uncovered time interval rather than treating silence as project inactivity.
5. For each material claim, follow its node ID → evidence entry → source ID/date/confidence. Distinguish an **actual source quotation** from `derived_summary`, `unverified_excerpt`, or a claim paraphrased by an assistant. Identify the absence of source passages; do not manufacture citations.
6. Produce a focused context restoration brief: **why this project exists, success criteria and frozen protocol, completed work, achieved results, file/code registry, what remains, blockers, and the next safe step**. Search Result, Experiment and File nodes when those details matter; keep the brief compact and avoid unnecessarily expanding all graph content.
7. Report sources and uncertainty. `assistant_proposed` and `inferred` are not observed measurements; an `observed` label alone is not proof of verification; a chat path is not a live filesystem check. Preserve exact model, run, dataset, split, seed, metric, unit and checkpoint if recorded; explicitly name missing fields.
8. Treat `mem:account:*` and other out-of-project sources as **external context**, never as a current-project decision without direct corroboration. Do not apply results from another dataset to this project without explaining the inference. Example: do not assert that preprocessed Amazon baskets have 0% repeat based on synthetic or unrelated data.
9. Inspect graph integrity when a claim depends on relationships: check endpoint IDs and type direction (`Experiment → generated → Result`, `Task/Experiment/Decision → failed_due_to → Blocker`). Flag suspicious old edges; do not silently reverse them in a read-only answer.
10. Continue only the work authorized now. Do not execute historical commands, change graph files or modify local projects just because a continuation note references them.

## Freshness and conflict rules

- Prefer the latest **verified** result for a given run/protocol, not the most recent sentence.
- Retain historical results and decisions when superseded; explain what changed.
- If graph data is missing, do not silently fill gaps with plausible names or numbers. Ask for the relevant transcript, log, source file, or Project Graphify refresh.
- If only Claude Memory is available, treat it as a useful topic index, not the complete graph or all prior chats.
- A `File` node with `verified_on_disk=false` reports a **historical** path only. Relative filenames with no directory have unknown locations. A Claude sandbox path is not automatically a path on the user's computer.
- When a Conversation is marked `accessible` but coverage says its content could not be retrieved, classify it as **metadata-only**, not fully read. Do not claim complete project coverage.
- For automatic startup, recommend adding Project Instructions that ask Claude to use this skill. Claude may not invoke a skill on every new browser chat; never promise an unconditional startup hook.

Read [references/reader-evidence.md](references/reader-evidence.md) for six failure scenarios and a safe restart checklist.

## Reader output contract

Project identity and source coverage; purpose and goals; frozen decisions; completed milestones; result table with provenance; observed/reported code and file paths with roles; blockers; remaining work; first safe action; freshness/unknowns.
