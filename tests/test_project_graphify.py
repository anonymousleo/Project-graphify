"""Offline acceptance checks for the actual packaged project history engine."""

import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import project_graphify as pg  # noqa: E402


def sample():
    return json.loads((ROOT / "examples" / "sample_history.json").read_text("utf-8"))


def make_graph(data=None, old=None):
    data = data or sample()
    builder = pg.Builder(old)
    builder.load_data(data)
    return builder.output(data["project"], data.get("coverage", {}))


def browser_graph_fixture():
    """Synthetic reproduction of the Claude browser's original graph dialect."""
    return {
        "schema": "project-graphify/v1",
        "project": {"id": "legacy-project-id", "name": "Demo"},
        "coverage": {"exhaustive": False, "chats_with_no_retrievable_content": ["lost-chat"]},
        "nodes": [
            {"id": "old-project", "type": "Project", "key": "demo", "title": "Demo"},
            {"id": "old-experiment", "type": "Experiment", "key": "grid", "title": "Grid"},
            {"id": "old-result", "type": "Result", "key": "score", "title": "Score",
             "attributes": {"model": "M", "dataset": "D", "split": "test",
                            "metric": "F1@5", "seed": 2026},
             "evidence": [{"source_id": "chat:run", "confidence": "user_reported",
                           "excerpt": "score: 0.12"}]},
            {"id": "old-file", "type": "File", "key": "train.py", "title": "train.py",
             "details": "Train the model", "attributes": {"path": "train.py",
              "purpose": "Train the model", "verified_on_disk": False},
             "evidence": [{"source_id": "chat:run", "confidence": "assistant_proposed",
                           "excerpt": "Train the model"}]},
            {"id": "old-chat", "type": "Conversation", "key": "chat:lost-chat",
             "title": "Old chat", "status": "accessible"},
            {"id": "old-source", "type": "Source", "key": "chat:run", "title": "Log"},
            {"id": "old-blocker", "type": "Blocker", "key": "blocked", "title": "Blocked"},
            {"id": "old-task", "type": "Task", "key": "task", "title": "Task"},
        ],
        "edges": [
            {"id": "wrong-generated", "source": "old-result", "target": "old-experiment",
             "relation": "generated"},
            {"id": "wrong-blocker", "source": "old-blocker", "target": "old-task",
             "relation": "failed_due_to"},
        ],
        "warnings": [],
    }


class ProjectGraphifyTests(unittest.TestCase):
    def test_browser_graph_normalizes_without_discarding_old_nodes(self):
        previous = browser_graph_fixture()
        b = pg.Builder(previous)
        graph = b.output(previous["project"], {})
        self.assertEqual(len(graph["nodes"]), 8)
        self.assertEqual(len(graph["edges"]), 2)
        self.assertEqual(graph["edges"], graph["links"])
        self.assertIn({"source": "old-experiment", "relation": "generated",
                       "target": "old-result"},
                      [{k: e[k] for k in ("source", "relation", "target")}
                       for e in graph["edges"]])
        self.assertTrue(any("Corrected reversed generated" in x for x in graph["warnings"]))
        self.assertTrue(any("circular source excerpt" in x for x in graph["warnings"]))
        self.assertTrue(any("content was unavailable" in x for x in graph["warnings"]))
        again = pg.Builder(graph).output(previous["project"], {})
        self.assertEqual(again, graph)

    def test_browser_incremental_merge_preserves_node_ids_and_relations(self):
        previous = browser_graph_fixture()
        b = pg.Builder(previous)
        b.load_data({"project": previous["project"], "facts": [
            {"kind": "Result", "key": "score", "title": "Score", "status": "completed",
             "attributes": {"model": "M", "dataset": "D", "split": "test",
                            "metric": "F1@5", "seed": 2026},
             "evidence": [{"source_id": "chat:run", "confidence": "observed",
                           "excerpt": "score: 0.12"}]},
        ]})
        merged = b.output(previous["project"], {})
        self.assertEqual(len(pg.by_type(merged, "Project")), 1)
        self.assertEqual(len(pg.by_type(merged, "Result")), 1)
        self.assertEqual(len(merged["edges"]), len({(e["source"], e["target"], e["relation"])
                                                  for e in merged["edges"]}))

    def test_mismatched_edge_aliases_rejected(self):
        data = browser_graph_fixture()
        data["links"] = []
        with self.assertRaisesRegex(ValueError, "disagree"):
            pg.Builder(data)

    def test_edge_only_reader_path(self):
        graph = browser_graph_fixture()
        graph["edges"] = [{"id": "e", "source": "old-experiment",
                           "target": "old-result", "relation": "generated"}]
        self.assertEqual(pg.find_path(graph, "grid", "score"), ["Grid", "Score"])

    def test_read_only_audit_preserves_original(self):
        graph = browser_graph_fixture()
        original = json.dumps(graph, sort_keys=True)
        outcome = pg.audit(graph)
        self.assertEqual(outcome["nodes"], 8)
        self.assertEqual(outcome["edges"], 2)
        self.assertEqual(outcome["original_schema"], "project-graphify/v1")
        self.assertEqual(json.dumps(graph, sort_keys=True), original)

    def test_reject_duplicate_legacy_type_key(self):
        graph = browser_graph_fixture()
        graph["nodes"].append({"id": "duplicate-result", "type": "Result", "key": "score"})
        with self.assertRaisesRegex(ValueError, "duplicate"):
            pg.Builder(graph)

    def test_incomplete_result_scope_is_reported_without_fabrication(self):
        data = sample()
        data["facts"][2]["attributes"].pop("seed")
        graph = make_graph(data)
        self.assertTrue(any("missing structured fields: seed" in w for w in graph["warnings"]))
        result = pg.by_type(graph, "Result")[0]
        self.assertNotIn("seed", result["attributes"])
    def test_goal_results_and_file_purpose(self):
        graph = make_graph()
        self.assertEqual(len(pg.by_type(graph, "Goal")), 1)
        result = pg.by_type(graph, "Result")[0]
        self.assertEqual(result["attributes"]["seed"], 2026)
        self.assertEqual(result["attributes"]["split"], "validation")
        self.assertEqual(result["attributes"]["metric"], "F1@5")
        f = next(n for n in pg.by_type(graph, "File") if n["key"] == "train-log")
        self.assertEqual(f["attributes"]["purpose"], "Audit training")
        self.assertFalse(f["attributes"]["verified_on_disk"])

    def test_chat_preserved_with_private_content_omitted(self):
        graph = make_graph()
        self.assertEqual(len(pg.by_type(graph, "Message")), 2)
        self.assertTrue(all("content" not in n["attributes"] for n in pg.by_type(graph, "Message")))
        self.assertTrue(any(n["attributes"].get("discovery") == "historical_chat_path"
                            for n in pg.by_type(graph, "File")))

    def test_opt_in_full_message_text(self):
        builder = pg.Builder()
        builder.load_data(sample(), include_message_text=True)
        self.assertTrue(any("Goal is" in n["attributes"]["content"] for n in
                            pg.by_type(builder.output(sample()["project"], {}), "Message")))

    def test_proposals_do_not_prove_completion(self):
        data = sample()
        fact = data["facts"][3]
        fact["status"] = "completed"
        graph = make_graph(data)
        task = next(x for x in pg.by_type(graph, "Task") if x["key"] == "baseline-task")
        self.assertEqual(task["status"], "unverified_completion")
        self.assertTrue(any("completion" in warning for warning in graph["warnings"]))

    def test_partial_coverage_guard(self):
        data = sample()
        data["coverage"]["exhaustive"] = True
        graph = make_graph(data)
        self.assertFalse(graph["coverage"]["exhaustive"])

    def test_conflicts_are_preserved(self):
        data = sample()
        graph = make_graph(data)
        data["facts"][2]["attributes"]["value"] = 0.29
        merged = make_graph(data, old=graph)
        result = pg.by_type(merged, "Result")[0]
        self.assertGreater(len(result["conflicts"]), 0)
        self.assertEqual(result["attributes"]["value"], 0.12)

    def test_duplicate_run_determinism(self):
        data = sample()
        one = make_graph(data)
        two = make_graph(data)
        self.assertEqual(one, two)
        repeated = make_graph(data, old=one)
        self.assertEqual(len(repeated["nodes"]), len(one["nodes"]))
        self.assertEqual(len(repeated["links"]), len(one["links"]))

    def test_bfs_and_search(self):
        graph = make_graph()
        path = pg.find_path(graph, "research-goal", "baseline-task")
        self.assertEqual(path, ["Reproducible paper", "Reproduce another baseline"])
        self.assertTrue(pg.query(graph, "baseline", limit=5))

    def test_code_graph_merge_keeps_original(self):
        with tempfile.TemporaryDirectory() as temp:
            code_path = Path(temp) / "source.json"
            code = {"nodes": [{"id": "A", "label": "main"}, {"id": "B", "label": "helper"}],
                    "links": [{"source": "A", "target": "B", "type": "calls"}],
                    "hyperedges": [{"members": ["A", "B"]}], "directed": True}
            code_path.write_text(json.dumps(code), encoding="utf-8")
            builder = pg.Builder()
            builder.load_data(sample())
            builder.merge_code_graph(code_path)
            graph = builder.output(sample()["project"], {})
            self.assertEqual(len(pg.by_type(graph, "CodeNode")), 2)
            self.assertEqual(graph["code_graph"]["hyperedges"], code["hyperedges"])
            self.assertTrue(any(edge["relation"] == "calls" for edge in graph["links"]))

    def test_cli_outputs_evidence_and_reader_files(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "out"
            args = argparse.Namespace(input=str(ROOT / "examples" / "sample_history.json"),
                                      output=str(out), existing=None, code_graph=None,
                                      include_message_text=False)
            pg.build(args)
            self.assertEqual(sorted(p.name for p in out.iterdir()),
                             sorted(["graph.json", "GRAPH_REPORT.md", "PROJECT_MEMORY.md",
                                     "CONTINUATION.md", "evidence.jsonl"]))
            self.assertIn("Reproducible paper", (out / "PROJECT_MEMORY.md").read_text("utf-8"))
            self.assertIn("baseline-task", pg.by_type(json.loads((out / "graph.json").read_text("utf-8")),
                                                     "Task")[0]["key"])

    def test_previous_project_cannot_be_reused(self):
        with tempfile.TemporaryDirectory() as temp:
            first = Path(temp) / "previous.json"
            graph = make_graph()
            graph["project"]["id"] = "a-different-project"
            first.write_text(json.dumps(graph), encoding="utf-8")
            args = argparse.Namespace(input=str(ROOT / "examples" / "sample_history.json"),
                                      output=str(Path(temp) / "out"), existing=str(first),
                                      code_graph=None, include_message_text=False)
            with self.assertRaises(ValueError):
                pg.build(args)


if __name__ == "__main__":
    unittest.main()
