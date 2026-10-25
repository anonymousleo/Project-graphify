# Current-project history retrieval playbook

## Project isolation and feasible coverage

Search **only** the current Claude Project unless user explicitly asks to
cross projects. Respect enabled chat-search features and tool permissions.
Native project search is retrieval, not enumeration. Search can miss messages,
and hidden memory may be compressed. Record `coverage.mode`, `exhaustive=false`,
topics searched, observed chat IDs or titles, earliest/latest accessible chat,
and missing topics. A complete exported chat inventory may allow an exhaustive
claim, but only with explicit proof of which chats were included.

For source-level audit, attach chat title, message link/ID if provided, date,
and a concise exact excerpt. Do not invent message IDs or copy large chunks of
private content. The default CLI omits full message text on purpose.

## Search matrix

Run enough independent queries to cover every family, not one giant query:

| Family | Suggested project chat searches | Extract |
| --- | --- | --- |
| Origin | started, motivation, research gap, problem statement | Why the project exists |
| Target | goal, thesis, paper, success, deadline, metric target | Acceptance criteria |
| Protocol | frozen, split, seed, datasets, preprocessing, leakage, test seal | Invariants |
| Architecture | method, design, module, loss, mechanism, ablation | Decisions and dependencies |
| Code & paths | `/home/`, `~/`, `.py`, `.sh`, git, checkpoint, sha256 | File purpose, creation, path, run |
| Experiments | baseline, training, validation, final test, evaluation | Commands, runs, scope |
| Results | F1, HR, NDCG, MRR, table, PASS, FAIL, accuracy | Exact values + metric unit |
| Status | completed, pending, still running, killed, blocker | Verified state |
| Handoffs | continue, resume, next step, step number, recovery | Safe next action |
| Corrections | correction, not actually, retracted, invalid, stale | Superseded claims |

Also search distinctive model names and dataset names from discovered facts.
Capture warnings as facts, not just successful runs. A failed or aborted run
must remain visible. Distinguish code *proposed*, *written*, *launched* and
*verified*; none implies the next.

## File / code registry fields

For each path, record: exact historical path; project and machine; file type;
why it was created; what it reads; what it produces; linked functions and
modules; how it was invoked; validation status; first and latest cited chat;
hash/commit if present; whether existence has been checked independently;
replacement/supersession history.

Project chat text does not provide direct filesystem access. Never invent file
contents or certify a file exists based only on command output pasted months
ago. Distinguish a directory *appearing in an example command* from a verified
artifact. If the user shares a real repository, analyze it using actual tools.

## Results registry fields

Store result by `(dataset, method, checkpoint, run_id, seed, split, metric,
@K, units, candidate_universe, protocol_version)`. The result should point to
the chat/log/test artifact and the Experiment that produced it. Include
execution status, time if known, replication status, hashes when supplied,
warnings and drift from frozen protocol. Never convert percentages silently.

## Write and refresh workflow

1. Identify the project and inspect existing graph snapshot/memory first.
2. Search the matrix, collecting only supported facts with source evidence.
3. Merge new facts and keep old, source-linked history. If execution tools are
   available, normalize into JSON and run `tools/project_graphify.py build`.
4. If an original Graphify code graph was actually generated, include it via
   `--code-graph`. Do not assume the browser ZIP runs local Python.
5. Validate unresolved paths, unsupported completion flags, conflicting facts
   and differences against older Project Graphify snapshots.
6. Save `graph.json`, `evidence.jsonl`, `GRAPH_REPORT.md`, `PROJECT_MEMORY.md`,
   `CONTINUATION.md` in persistent **Project Knowledge** or the available
   file destination; where writes are unavailable, explicitly hand downloadable
   files to the user for uploading.
7. Ask native Claude memory to remember a *compact index* only. Verify whether
   it accepted the memory request. A hidden-memory update is not guaranteed.
8. Tell the user the exact date/freshness, how many chats were accessible,
   what is known, what is not known, and what evidence to provide next.

## Cross-chat starter instruction

Add to Claude Project Instructions (user action):

> At the beginning of each chat, invoke `project-graphify-reader` if available.
> Read `CONTINUATION.md`, `PROJECT_MEMORY.md` and `graph.json` from Project
> Knowledge, then search newer chats for changes. State what is verified,
> what is pending, and the next safe step. If graph files are unavailable,
> search past chats in the current Project and acknowledge partial coverage.

Claude may autonomously choose tool calls; the instructions guide that behavior
but cannot enforce a background job or bypass account access settings.
