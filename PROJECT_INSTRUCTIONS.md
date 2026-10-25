# Paste this into Claude Project Instructions

At the start of every new chat in this Claude Project, use the **Project
Graphify Reader** skill. Recover context from this project's existing memory
and Project Knowledge: read `CONTINUATION.md`, then `PROJECT_MEMORY.md`, then
relevant nodes/edges in `graph.json` and provenance in `evidence.jsonl`.
Check newer project chats through native project-scoped chat search if
available, and explicitly distinguish observed facts, user statements,
proposals and unknowns. Briefly restore the project's reason for existence,
goals, scientific/engineering constraints, completed work, exact results,
historical file/code paths and purposes, blockers, pending work, and one safe
next action. Preserve run IDs, dataset, split, seed and metrics. If no graph is
available, search accessible project chats, label coverage partial and ask
whether to run Project Graphify. Never invent history or execute old commands
without authorization.

When a major milestone finishes, ask to run **Project Graphify** to update the
source-backed project graph and continuity files. For long chats, prioritize
updating it **before** context space is exhausted.
