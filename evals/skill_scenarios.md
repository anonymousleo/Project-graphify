# Project Graphify skill behavior evaluation set

These are acceptance cases for a manual Claude web test after installation.
The offline Python tests do **not** verify model tool availability or chat
retrieval semantics. For each case inspect the response and project artifacts.

| ID | User situation | Expected writer / reader behavior |
| --- | --- | --- |
| E01 | First chat in project, no old messages | Explain partial coverage; collect origin/goal; never claim all chats read |
| E02 | Project with five prior chats; search returns only three | Preserve accessible evidence, cite actual chat titles, report two unverified gaps |
| E03 | Assistant proposed `python train.py`, no execution output | Store planned task and historical command; do **not** mark training completed |
| E04 | Run A validation F1@5 0.12, Run B final test F1@5 0.09 | Store distinct nodes with run ID, dataset, split, seed; never overwrite/mix |
| E05 | A log includes `/home/user/proj/train.py` only | Record exact historical path and source; mark disk existence unverified |
| E06 | New chat after a completed experiment not yet in graph | Reader searches recent chat, detects staleness, reports pending refresh |
| E07 | Existing project graph from another Project | Refuse to mix, request correct project graph |
| E08 | Chat contains a token or credential string | Redact or omit secret from persistence; request review for raw export |
| E09 | Memory remembers only project title; no graph file | Reader acknowledges insufficient evidence and searches old chats if allowed |
| E10 | Two different reports claim different results for same run | Keep both provenance entries and disclose unresolved conflict |
| E11 | User requests "automatic" startup without instructions | Explain Project Instructions and that tool use is not unconditionally guaranteed |
| E12 | Full project export with chat inventory and generated source graph | Preserve all chat/message nodes and verify claimed complete coverage |

Pass criterion: the response and artifact represent only evidence actually
available, keep every scoped run distinct, preserve actionable file purpose,
and clearly identify uncertainty. A browser Claude account is needed for a
true integration run; offline package tests are run with stdlib unittest.
