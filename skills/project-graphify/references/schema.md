# Project Graphify evidence graph schema v1 (plugin 1.0.1)

This is a **temporal, sourced** graph. The graph is not equivalent to a factual
database: every assertion must be attributable to a chat, file, run log, or user
statement. Keep older observations when later work changes an outcome.

## Browser/CLI compatibility

Canonical schema: `project-graphify/v1`. Browser-built archives use `edges`;
the CLI also exports an **identical** `links` alias for clients of v1.0.0.
Both fields describe directed edges with `id`, `source`, `relation`, `target`.
The CLI accepts historical `project-graphify-1.0` graphs and either relationship
field. If both fields exist but disagree, it raises an error rather than
silently choosing one. Importing older graphs preserves node IDs, normalizes
known inverted relationship directions and flags questionable evidence.

The old browser builder used a different node-ID hash than the local CLI.
Incremental imports must deduplicate by `(type,key)` and keep previously
assigned IDs; rehashing all old nodes disconnects saved edges.

## Input envelope

`tools/project_graphify.py build` accepts UTF-8 JSON:

```json
{
  "project": {"id": "stable-project-id", "name": "Research project", "updated_at": "2026-10-26"},
  "coverage": {"mode": "native_project_search", "exhaustive": false,
               "included_chats": 2, "notes": "Some old chats not indexed"},
  "sources": [
    {"id": "chat:experiment-1", "type": "chat", "title": "Baseline reproduction",
     "date": "2026-10-20", "complete": false}
  ],
  "conversations": [
    {"id": "chat:experiment-1", "title": "Baseline reproduction", "messages": [
      {"id": "message:1", "role": "user", "timestamp": "2026-10-20",
       "content": "All runs are saved under ~/Desktop/Research/results/"}
    ]}
  ],
  "facts": [
    {"kind": "Goal", "key": "publish-paper", "title": "Publish the paper",
     "details": "Why this project started and what successful completion means",
     "status": "active", "attributes": {"deadline": "2027-03-01"},
     "evidence": [{"source_id": "chat:experiment-1",
                   "message_id": "message:1", "date": "2026-10-20",
                   "confidence": "user_reported", "excerpt": "..."}],
     "links": [{"relation": "depends_on", "target_kind": "Task", "target_key": "reproduce-baselines"}]}
  ]
}
```

The script imports all explicitly supplied `conversations` and each message
as provenance nodes. By default it stores a SHA256 digest, role, length,
timestamp and chat sequence, not arbitrary sensitive message text. Use
`--include-message-text` **only after reviewing privacy** if full transcript
text is needed. It detects historical Linux file-path mentions, but cannot
verify file existence or infer each file's purpose. Supply semantic `facts`
derived from actual source inspection or Claude's grounded reading.

## Node families and key conventions

| Type | Stable key and attributes |
| --- | --- |
| Project | Project-scoped unique ID; don't mix projects |
| Goal | Research or product outcome; why, success criterion |
| Requirement | Frozen splits, seeds, safety and publication rules |
| Decision | Choice, rationale, discarded alternatives, date |
| File | `path`, purpose, inputs, outputs, creator, `verified_on_disk`, SHA256 when known |
| Function | File path, symbol and callable behavior |
| Environment | Machine, GPU, conda env, dependencies, exact versions |
| Dataset | Origin, version, split, preprocessing, hash |
| Experiment | Run ID, command, model, dataset, seed, config, status |
| Metric | Defined statistic, K, units, aggregation and candidate set |
| Result | **Unique** per run + dataset + split + seed + metric + K |
| Task | Work item with current status and acceptance gate |
| Blocker | Problem, scope, verified impact and recovery condition |
| Conversation | Chat ID, title, created/updated timestamps |
| Message | Chat ID + message ID; role, hash and optional opt-in text |
| Source | Chat, log, path, commit, test artifact, PDF or dataset |

Store exact evidence on the relevant node. `confidence` is one of
`observed`, `user_reported`, `assistant_proposed`, `inferred`, `unknown`.
Confidence is an evidence category, not a numeric probability.

Every evidence record should contain `source_id`, source date/message locator
if known, and `excerpt_kind`: `verbatim_unverified` for source text transcribed
by the agent, `derived_summary` for an interpretation or description,
`unverified_excerpt` for imported records without quote-level provenance,
or `missing`. An `observed` label is still only as trustworthy as the actual
referenced artifact. Cross-project account-memory evidence must be explicitly
marked `source_scope=external_account_memory` and not silently applied to the
current Project. **Do not copy the generated File purpose into its supporting
excerpt and present the two identical strings as independent evidence.**

Examples of relations: `has_goal`, `depends_on`, `implements`, `generated`,
`measures`, `uses_dataset`, `used_seed`, `supersedes`, `failed_due_to`,
`located_at`, `derived_from`, `supported_by`, `contains_message`, `mentions_path`,
`calls`, `imports`, `inherits`, `contains`, `affects`.

Important directions:

| Source type | Relationship | Target type | Example |
| --- | --- | --- | --- |
| Experiment | `generated` | Result | A grid-search run generated an F1 value |
| Task / Experiment / Decision | `failed_due_to` | Blocker | A blocked run failed due to missing data |
| Newer result/decision | `supersedes` | Older result/decision | Verified rerun supersedes an invalid earlier run |
| Result / File / other fact | `supported_by` | Source | Evaluation result supported by a log |

Only correct reversed `generated` / `failed_due_to` relationships when the
two endpoint types make the inversion unambiguous; otherwise preserve and warn.
No semantic edge can substitute for an actual evidence source.

## Safety and inference

1. Never mark `status=completed` using only a generated suggestion. The CLI
   demotes unsupported completion claims to `unverified_completion`.
2. Never overwrite conflicting values. Identical stable-key nodes preserve
   conflicts and warnings until a human resolves them with evidence.
3. Historical chat paths need `verified_on_disk=false` until checked.
4. Results must distinguish validation/test, model/checkpoint, evaluation
   protocol, dataset, seed and metric definition. If any are unknown, say so.
5. `coverage.exhaustive=true` requires `verified_complete_export=true` plus
   a verifiable complete chat inventory. Native relevance search alone cannot
   prove completeness.
6. Newly created local IDs are SHA256 over `type:key`; imported historical
   IDs are preserved. New edges use relation plus both IDs.
   Merge time and storage scale linearly with node and edge counts, apart from
   deterministic sorting of output. No network or paid inference is needed.
7. Original Graphify graphs can be imported using `--code-graph`; their raw
   source survives as `code-graph.original.json`, including hyperedges and
   metadata. Normalized `CodeNode` relations enable cross-domain querying.
   For advanced native Graphify analysis, use its bundled engine and original
   graph rather than claiming the history CLI implements every AST operation.
