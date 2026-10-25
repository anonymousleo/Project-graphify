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


class ProjectGraphifyTests(unittest.TestCase):
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
