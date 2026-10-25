---
name: project-graphify-reader
description: Automatically restore relevant context when starting or continuing a chat in the same Claude Project, including why it started, goals, decisions, code files and paths, work completed, measured results, blockers, and next steps. Use whenever the user asks to continue, resume, recall earlier research, or locate a project artifact.
---

# Project Graphify Reader

Read existing Project Graphify state and **recover the most accurate current context** before the user continues work. Do not rebuild the entire graph unless missing or stale; route substantive refresh work to Project Graphify.

## Recovery order

1. Identify the current Claude Project; never silently combine projects.
2. Read available project memory and Project Knowledge / project Library files: `CONTINUATION.md` first, then `PROJECT_MEMORY.md`, `GRAPH_REPORT.md`, and relevant nodes/edges from `graph.json` or a connected graph-query service. Confirm each file/tool is actually accessible.
3. If no graph artifact exists, use Claude's native *project-scoped* past-chat search if available. Search by goal, latest progress, result, filename, blocker and next action; mark coverage as partial.
4. Compare graph timestamp with recent conversations. Search newer chats for work completed since the graph was written, and reconcile rather than trusting a stale checkpoint.
5. Produce a concise context restoration brief: **why this project exists, target outcome, frozen protocol, what is done, achieved results, file/code registry, what is left, blockers, and the next safe step**.
6. Report sources and uncertainty. `assistant_proposed` is not `observed`; a chat path is not a current filesystem verification; old validation results are not new test results. Use exact run, split, seed and metric scope.
7. Continue only the work the user has authorized. Do not execute historical commands or modify local projects just because they appear in a continuation note.

## Freshness and conflict rules

- Prefer the latest **verified** result for a given run/protocol, not the most recent sentence.
- Retain historical results and decisions when superseded; explain what changed.
- If graph data is missing, do not silently fill gaps with plausible names or numbers. Ask for the relevant transcript, log, source file, or Project Graphify refresh.
- If only Claude Memory is available, treat it as a useful topic index, not the complete graph or all prior chats.

Read [references/reader-evidence.md](references/reader-evidence.md) for six failure scenarios and a safe restart checklist.

## Reader output contract

Project identity and source coverage; purpose and goals; frozen decisions; completed milestones; result table with provenance; observed/reported code and file paths with roles; blockers; remaining work; first safe action; freshness/unknowns.
