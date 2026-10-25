#!/usr/bin/env python3
"""Dependency-free, source-backed project history knowledge graph.

The Graphify AST engine is distributed separately under resources/graphify-source.
This tool deals with conversations, semantic facts and optional Graphify graph
imports. It does not contact Claude, index private accounts, or infer semantic
facts from arbitrary chat text without a language model.
"""

from __future__ import annotations

import argparse
from collections import Counter, deque
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys

SCHEMA = "project-graphify/v1"
ACCEPTED_SCHEMAS = {SCHEMA, "project-graphify-1.0"}
KINDS = {
    "Project", "Goal", "Requirement", "Decision", "File", "Function",
    "Environment", "Experiment", "Result", "Metric", "Task", "Blocker",
    "Dataset", "Source", "Conversation", "Message", "Reference", "CodeNode",
}
EVIDENCE_STATES = {"observed", "user_reported", "assistant_proposed", "inferred", "unknown"}
PATH_PATTERN = re.compile(r"(?<![\w])(?:/home/[\w.-]+/|~/|\$HOME/|/workspace/)[\w./()_-]+")


def graph_edges(graph: dict) -> list[dict]:
    """Read either historical graph dialect without silently losing links."""
    edges = graph.get("edges")
    links = graph.get("links")
    if edges is not None and links is not None and edges != links:
        raise ValueError("graph.edges and graph.links disagree; resolve before merging")
    result = edges if edges is not None else links
    if result is None:
        return []
    if not isinstance(result, list):
        raise ValueError("graph relationships must be a list")
    return result


def stable_id(kind: str, key: str) -> str:
    signature = json.dumps([kind, str(key)], ensure_ascii=False, separators=(",", ":"))
    return "pg_" + hashlib.sha256(signature.encode("utf-8")).hexdigest()[:24]


def edge_id(source: str, target: str, relation: str) -> str:
    return stable_id("edge", source + "|" + relation + "|" + target)


def sorted_unique(items: list[dict]) -> list[dict]:
    unique = {json.dumps(x, sort_keys=True, ensure_ascii=False): x for x in items}
    return [unique[key] for key in sorted(unique)]


def evidence_items(items: list[dict], warnings: list[str], origin: str) -> list[dict]:
    out = []
    for item in items:
        if not isinstance(item, dict):
            warnings.append(f"{origin}: non-object evidence ignored")
            continue
        entry = dict(item)
        if entry.get("confidence") not in EVIDENCE_STATES:
            entry["confidence"] = "unknown"
            warnings.append(f"{origin}: evidence lacked a recognized confidence")
        entry.setdefault("excerpt_kind", "unverified_excerpt" if entry.get("excerpt") else "missing")
        if str(entry.get("source_id", "")).startswith("mem:account:"):
            entry["source_scope"] = "external_account_memory"
        out.append(entry)
    return sorted_unique(out)


def mark_derived_excerpts(node: dict):
    attrs = node.get("attributes", {})
    summaries = {str(attrs.get("purpose", "")), str(node.get("details", ""))}
    summaries.discard("")
    for evidence in node.get("evidence", []):
        if str(evidence.get("excerpt", "")).strip() in summaries:
            evidence["excerpt_kind"] = "derived_summary"


class Builder:
    def __init__(self, previous: dict | None = None):
        previous = previous or {}
        if previous.get("schema", SCHEMA) not in ACCEPTED_SCHEMAS:
            raise ValueError(f"Unsupported graph schema: {previous.get('schema')}")
        self.nodes: dict[str, dict] = {n["id"]: deepcopy(n) for n in previous.get("nodes", [])}
        self.node_keys = {(n["type"], str(n["key"])): n["id"]
                          for n in self.nodes.values()}
        if len(self.node_keys) != len(self.nodes):
            raise ValueError("existing graph contains duplicate (type, key) node identities")
        self.links: dict[str, dict] = {}
        self.edge_keys: dict[tuple[str, str, str], str] = {}
        self.warnings: list[str] = list(previous.get("warnings", []))
        self.code_graph = dict(previous.get("code_graph", {}))
        self.old_coverage = dict(previous.get("coverage", {}))
        for n in self.nodes.values():
            if n.get("evidence"):
                n["evidence"] = evidence_items(n["evidence"], self.warnings,
                                                 f"{n['type']}:{n['key']}")
                mark_derived_excerpts(n)
        for edge in graph_edges(previous):
            self.edge(edge["source"], edge["target"], edge["relation"],
                      **{k: deepcopy(v) for k, v in edge.items()
                         if k not in {"source", "target", "relation", "id"}},
                      _original_id=edge.get("id"))

    def node_id(self, kind: str, key: str) -> str:
        return self.node_keys.get((kind, str(key)), stable_id(kind, key))

    def node(self, kind: str, key: str, title: str | None = None, **attrs) -> str:
        node_id = self.node_id(kind, key)
        if attrs.get("evidence"):
            attrs["evidence"] = evidence_items(attrs["evidence"], self.warnings,
                                                f"{kind}:{key}")
        candidate = {"id": node_id, "type": kind, "key": str(key), "title": str(title or key), **deepcopy(attrs)}
        mark_derived_excerpts(candidate)
        if node_id not in self.nodes:
            self.nodes[node_id] = candidate
            self.node_keys[(kind, str(key))] = node_id
            return node_id
        old = self.nodes[node_id]
        if old.get("attributes", {}).get("placeholder") and not candidate.get("attributes", {}).get("placeholder"):
            if old.get("evidence"):
                candidate["evidence"] = sorted_unique(old["evidence"] + candidate.get("evidence", []))
            self.nodes[node_id] = candidate
            return node_id
        for prop, val in candidate.items():
            if prop not in old or old[prop] in (None, "", {}, []):
                old[prop] = val
            elif prop == "evidence":
                old[prop] = sorted_unique(list(old[prop]) + list(val))
            elif prop == "conflicts":
                old[prop] = sorted_unique(list(old[prop]) + list(val))
            elif old[prop] != val and prop not in {"id", "type", "key"}:
                old.setdefault("conflicts", [])
                conflict = {"field": prop, "existing": old[prop], "incoming": val}
                if conflict not in old["conflicts"]:
                    old["conflicts"].append(conflict)
                    self.warnings.append(f"Conflicting {prop} values for {kind}:{key}; retained both")
        return node_id

    def edge(self, source: str, target: str, relation: str, _original_id=None, **attrs):
        st = self.nodes.get(source, {}).get("type")
        tt = self.nodes.get(target, {}).get("type")
        reversed_legacy = ((relation == "generated" and st == "Result" and tt == "Experiment")
                           or (relation == "failed_due_to" and st == "Blocker"
                               and tt in {"Experiment", "Task", "Decision"}))
        if reversed_legacy:
            source, target = target, source
            st, tt = tt, st
            self.warnings.append(f"Corrected reversed {relation} relationship: {source} -> {target}")
            if _original_id:
                attrs["legacy_edge_id"] = _original_id
                _original_id = None
        if relation == "generated" and st and tt and (st, tt) != ("Experiment", "Result"):
            self.warnings.append(f"Review ambiguous generated relation: {st} -> {tt}")
        if relation == "failed_due_to" and st and tt and tt != "Blocker":
            self.warnings.append(f"Review ambiguous failed_due_to relation: {st} -> {tt}")
        ident = self.edge_keys.get((source, target, relation))
        if ident is None:
            ident = _original_id or edge_id(source, target, relation)
            if ident in self.links:
                ident = edge_id(source, target, relation)
            self.edge_keys[(source, target, relation)] = ident
        old = self.links.get(ident, {})
        self.links[ident] = {**old, "id": ident, "source": source, "target": target,
                             "relation": relation, **attrs}

    def load_data(self, data: dict, include_message_text: bool = False):
        project = data.get("project", {})
        if not isinstance(project, dict) or not project.get("id"):
            raise ValueError("input.project.id is required")
        old_projects = [n for n in self.nodes.values() if n["type"] == "Project"]
        if len(old_projects) == 1 and old_projects[0].get("key") != str(project["id"]):
            # Early browser builds used a project slug as the node key and a
            # different project.id hash. Preserve the existing node identity.
            project_id = old_projects[0]["id"]
        else:
            project_id = self.node("Project", str(project["id"]), project.get("name", project["id"]),
                                   attributes=project)

        for source in data.get("sources", []):
            if not isinstance(source, dict) or not source.get("id"):
                raise ValueError("each source requires id")
            source_id = self.node("Source", str(source["id"]), source.get("title", source["id"]),
                                  attributes=source)
            self.edge(project_id, source_id, "has_source")

        for conv in data.get("conversations", []):
            if not isinstance(conv, dict) or not conv.get("id"):
                raise ValueError("each conversation requires id")
            chat_key = str(conv["id"])
            cid = self.node("Conversation", chat_key, conv.get("title", chat_key),
                            attributes={k: v for k, v in conv.items() if k != "messages"})
            self.edge(project_id, cid, "has_conversation")
            prev_mid = None
            for idx, msg in enumerate(conv.get("messages", [])):
                message_key = f"{chat_key}:{msg.get('id', idx)}"
                content = str(msg.get("content", ""))
                msg_attrs = {"role": msg.get("role", "unknown"),
                             "timestamp": msg.get("timestamp"),
                             "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                             "content_length": len(content)}
                if include_message_text:
                    msg_attrs["content"] = content
                mid = self.node("Message", message_key, f"{msg_attrs['role']} message {idx + 1}",
                                attributes=msg_attrs)
                self.edge(cid, mid, "contains_message")
                if prev_mid:
                    self.edge(prev_mid, mid, "next_message")
                prev_mid = mid
                for path in sorted(set(PATH_PATTERN.findall(content))):
                    path_id = self.node("File", path, path,
                                        attributes={"path": path, "verified_on_disk": False,
                                                    "discovery": "historical_chat_path"},
                                        evidence=[{"source_id": chat_key, "message_id": message_key,
                                                   "confidence": "user_reported"
                                                   if msg.get("role") == "user" else "assistant_proposed",
                                                   "excerpt": "path reference only"}])
                    self.edge(mid, path_id, "mentions_path")

        for idx, fact in enumerate(data.get("facts", [])):
            if not isinstance(fact, dict) or not fact.get("kind") or not fact.get("key"):
                raise ValueError(f"fact #{idx + 1} requires kind and key")
            kind = str(fact["kind"]).strip().title()
            if kind not in KINDS:
                self.warnings.append(f"Fact {idx + 1}: unrecognized kind {kind}; keeping it")
            key = str(fact["key"])
            evidence = evidence_items(fact.get("evidence", []), self.warnings, f"{kind}:{key}")
            status = fact.get("status", "unknown")
            if status == "completed" and not any(
                x["confidence"] in {"observed", "user_reported"} for x in evidence
            ):
                status = "unverified_completion"
                self.warnings.append(f"{kind}:{key}: completion lacks observed/user-reported evidence")
            node_id = self.node(kind, key, fact.get("title", key),
                                details=fact.get("details", ""), status=status,
                                attributes=fact.get("attributes", {}), evidence=evidence)
            self.edge(project_id, node_id, "has_fact")
            for ev in evidence:
                if ev.get("source_id"):
                    source_key = str(ev["source_id"])
                    src_id = self.node_id("Source", source_key)
                    if src_id not in self.nodes:
                        src_id = self.node("Source", source_key, source_key,
                                           attributes={"identity": "source_id from fact evidence"})
                    self.edge(node_id, src_id, "supported_by")
            for link in fact.get("links", []):
                target_kind = str(link["target_kind"]).strip().title()
                target_key = str(link["target_key"])
                target_id = self.node_id(target_kind, target_key)
                if target_id not in self.nodes:
                    self.node(target_kind, target_key, target_key, status="unknown",
                              attributes={"placeholder": True})
                self.edge(node_id, target_id, str(link.get("relation", "related_to")))

    def merge_code_graph(self, path: Path):
        raw = json.loads(path.read_text(encoding="utf-8"))
        original_nodes = raw.get("nodes", [])
        original_links = raw.get("links", raw.get("edges", []))
        mapping = {}
        for n in original_nodes:
            orig_id = str(n.get("id", n.get("key", "")))
            if not orig_id:
                self.warnings.append("Code graph contained a node without id")
                continue
            nid = self.node("CodeNode", "graphify:" + orig_id,
                            str(n.get("label", n.get("name", orig_id))),
                            attributes={"origin": "Graphify", "graphify": n})
            mapping[orig_id] = nid
        for link in original_links:
            def endpoint_id(value):
                v = str(value.get("id")) if isinstance(value, dict) else str(value)
                return mapping.get(v)
            src = endpoint_id(link.get("source"))
            dst = endpoint_id(link.get("target"))
            if src and dst:
                self.edge(src, dst, str(link.get("relation", link.get("type", "code_link"))),
                          attributes={"origin": "Graphify", "graphify": link})
            else:
                self.warnings.append("Code graph had an edge with missing endpoint")
        self.code_graph = {"original_file": path.name,
                           "original_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                           "node_count": len(original_nodes), "edge_count": len(original_links),
                           "hyperedges": raw.get("hyperedges", []),
                           "other_metadata": {k: v for k, v in raw.items()
                                              if k not in {"nodes", "links", "edges", "hyperedges"}}}

    def output(self, project: dict, coverage: dict) -> dict:
        coverage = {**self.old_coverage, **dict(coverage or {})}
        if coverage.get("exhaustive") is True and not coverage.get("verified_complete_export"):
            coverage["exhaustive"] = False
            self.warnings.append("Coverage cannot be marked exhaustive without verified_complete_export")
        coverage.setdefault("exhaustive", False)
        self.current_coverage = coverage
        self.validate()
        normalized_edges = [self.links[k] for k in sorted(self.links)]
        return {"schema": SCHEMA, "project": project, "coverage": coverage,
                "nodes": [self.nodes[k] for k in sorted(self.nodes)],
                "edges": normalized_edges, "links": normalized_edges,
                "code_graph": self.code_graph, "warnings": sorted(set(self.warnings))}

    def validate(self):
        source_keys = {n["key"] for n in self.nodes.values()
                       if n["type"] in {"Source", "Conversation"}}
        for edge in self.links.values():
            if edge["source"] not in self.nodes or edge["target"] not in self.nodes:
                self.warnings.append(f"Dangling relationship: {edge['id']}")
        missing_chats = set(self.current_coverage.get("chats_with_no_retrievable_content", []))
        for n in self.nodes.values():
            attrs = n.get("attributes", {})
            if n["type"] == "Conversation":
                chat_key = str(n["key"]).removeprefix("chat:")
                if chat_key in missing_chats and n.get("status") == "accessible":
                    self.warnings.append(f"Conversation {chat_key} marked accessible but content was unavailable")
            if n["type"] == "File" and not attrs.get("path"):
                self.warnings.append(f"File {n['key']} lacks a recorded path")
            if n["type"] == "Result":
                needed = {"model", "dataset", "split", "metric", "seed"}
                missing = sorted(k for k in needed if attrs.get(k) in (None, ""))
                if missing:
                    self.warnings.append(f"Result {n['key']} missing structured fields: {', '.join(missing)}")
            for e in n.get("evidence", []):
                if e.get("confidence") not in EVIDENCE_STATES:
                    e["confidence"] = "unknown"
                    self.warnings.append(f"Node {n['key']} had invalid evidence confidence")
                excerpt = str(e.get("excerpt", "")).strip()
                if not excerpt:
                    e["excerpt_kind"] = "missing"
                    self.warnings.append(f"Node {n['key']} has evidence without a source excerpt")
                elif excerpt in {str(attrs.get("purpose", "")), str(n.get("details", ""))}:
                    e["excerpt_kind"] = "derived_summary"
                    self.warnings.append(f"Node {n['key']} has a circular source excerpt; verify quotation")
                if str(e.get("source_id", "")).startswith("mem:account:"):
                    e["source_scope"] = "external_account_memory"
                if e.get("source_id") and e["source_id"] not in source_keys:
                    self.warnings.append(f"Unresolved evidence source for {n['key']}: {e['source_id']}")


def by_type(graph: dict, kind: str) -> list[dict]:
    return sorted((n for n in graph.get("nodes", []) if n["type"] == kind),
                  key=lambda n: (n.get("title", "").lower(), n["id"]))


def node_line(n: dict) -> str:
    status = n.get("status", "unknown")
    attrs = n.get("attributes", {})
    path = attrs.get("path")
    base = f"- **{n['title']}** [{status}]"
    if path and path != n["title"]:
        base += f" (`{path}`)"
    if n.get("details"):
        base += ": " + str(n["details"]).replace("\n", " ")
    if n.get("conflicts"):
        base += f" (CONFLICTS: {len(n['conflicts'])})"
    return base


def report(graph: dict) -> str:
    project = graph["project"]
    cov = graph["coverage"]
    counts = Counter(n["type"] for n in graph["nodes"])
    lines = [f"# Project Graphify: {project.get('name', project['id'])}", "",
             f"Project ID: `{project['id']}`", f"Graph schema: `{SCHEMA}`",
             f"Coverage: **{'exhaustive' if cov['exhaustive'] else 'partial / unverified'}**",
             f"Included conversations: {counts['Conversation']}; messages: {counts['Message']}; "
             f"knowledge nodes: {len(graph['nodes'])}; edges: {len(graph['links'])}", ""]
    for kind in ("Goal", "Requirement", "Decision", "Experiment", "Result", "File",
                 "Function", "Task", "Blocker", "Dataset", "Environment"):
        rows = by_type(graph, kind)
        if rows:
            lines += [f"## {kind} ({len(rows)})", ""]
            lines.extend(node_line(n) for n in rows)
            lines.append("")
    if graph.get("code_graph"):
        meta = graph["code_graph"]
        lines += ["## Original Graphify code graph", "",
                  f"Imported {meta.get('node_count', 0)} nodes and {meta.get('edge_count', 0)} edges; "
                  "the unmodified original graph should be retained alongside this normalized graph.", ""]
    if graph["warnings"]:
        lines += ["## Verification warnings", ""]
        lines.extend(f"- {w}" for w in graph["warnings"])
    return "\n".join(lines).rstrip() + "\n"


def memory_digest(graph: dict) -> str:
    project = graph["project"]
    lines = [f"# Project memory index: {project.get('name', project['id'])}", "",
             "Persistent source: Project Knowledge files `graph.json`, `GRAPH_REPORT.md`, "
             "`CONTINUATION.md`, `evidence.jsonl`. Claude memory is an index, not the graph.",
             f"Coverage exhaustive: {graph['coverage']['exhaustive']}", ""]
    for kind, heading, limit in (("Goal", "Goals", 12), ("Requirement", "Frozen constraints", 12),
                                 ("Result", "Achieved results", 16), ("Task", "Tasks", 16),
                                 ("Blocker", "Blockers", 10)):
        rows = by_type(graph, kind)
        lines += [f"## {heading}", ""]
        lines.extend(node_line(n) for n in rows[:limit])
        if len(rows) > limit:
            lines.append(f"- {len(rows) - limit} more in graph.json")
        if not rows:
            lines.append("- No verified entries in available sources")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def continuation(graph: dict) -> str:
    lines = [f"# Continue {graph['project'].get('name', graph['project']['id'])}", "",
             "Read `PROJECT_MEMORY.md` and query `graph.json` for file paths and exact results; "
             "verify current status against newer project chats.", "",
             "## Immediate safe resume targets", ""]
    work = [n for kind in ("Blocker", "Task") for n in by_type(graph, kind)
            if n.get("status", "unknown") not in {"completed", "resolved"}]
    lines.extend(node_line(n) for n in work[:15])
    if not work:
        lines.append("- No outstanding action established; inspect the latest project chat")
    lines += ["", "## Reliability", "",
              f"- Chat coverage exhaustive: {graph['coverage']['exhaustive']}",
              "- Historical file paths are not live filesystem checks.",
              "- Proposed commands and experiments are not proof of execution.",
              "- Do not rerun training, evaluation or destructive operations without fresh approval.", ""]
    return "\n".join(lines)


def build(args):
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    previous = json.loads(Path(args.existing).read_text(encoding="utf-8")) if args.existing else None
    if previous and previous.get("project", {}).get("id") != data.get("project", {}).get("id"):
        raise ValueError("existing graph belongs to a different project")
    b = Builder(previous)
    b.load_data(data, include_message_text=args.include_message_text)
    if args.code_graph:
        b.merge_code_graph(Path(args.code_graph))
    graph = b.output(data["project"], data.get("coverage", {}))
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    (out / "graph.json").write_text(json.dumps(graph, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "GRAPH_REPORT.md").write_text(report(graph), encoding="utf-8")
    (out / "PROJECT_MEMORY.md").write_text(memory_digest(graph), encoding="utf-8")
    (out / "CONTINUATION.md").write_text(continuation(graph), encoding="utf-8")
    with (out / "evidence.jsonl").open("w", encoding="utf-8") as dst:
        for n in graph["nodes"]:
            for e in n.get("evidence", []):
                dst.write(json.dumps({"node_id": n["id"], "node_type": n["type"], **e},
                                     ensure_ascii=False, sort_keys=True) + "\n")
    if args.code_graph:
        (out / "code-graph.original.json").write_bytes(Path(args.code_graph).read_bytes())
    print(f"Wrote {len(graph['nodes'])} nodes, {len(graph['links'])} edges to {out}")
    print(f"Coverage exhaustive: {graph['coverage']['exhaustive']}; warnings: {len(graph['warnings'])}")


def query(graph: dict, term: str, limit: int = 15) -> list[dict]:
    term = term.lower()
    out = []
    for n in graph.get("nodes", []):
        searchable = " ".join((n.get("title", ""), n.get("key", ""),
                               n.get("details", ""),
                               json.dumps(n.get("attributes", {}), ensure_ascii=False)))
        if term in searchable.lower():
            out.append(n)
            if len(out) >= limit:
                break
    return out


def find_path(graph: dict, start: str, finish: str, max_depth: int = 10) -> list[str] | None:
    lookup = {n["id"]: n for n in graph["nodes"]}
    def resolve(name):
        if name in lookup:
            return name
        matches = [n["id"] for n in graph["nodes"] if n.get("key") == name or n.get("title") == name]
        if len(matches) != 1:
            raise ValueError(f"node `{name}` is unknown or ambiguous ({len(matches)} matches)")
        return matches[0]
    src, dst = resolve(start), resolve(finish)
    adjacency = {}
    for e in graph_edges(graph):
        adjacency.setdefault(e["source"], []).append(e["target"])
    queue = deque([src])
    predecessor = {src: None}
    depth = {src: 0}
    while queue:
        node = queue.popleft()
        if node == dst:
            path = []
            while node is not None:
                path.append(lookup[node]["title"])
                node = predecessor[node]
            return path[::-1]
        if depth[node] >= max_depth:
            continue
        for nxt in adjacency.get(node, []):
            if nxt in lookup and nxt not in predecessor:
                predecessor[nxt] = node
                depth[nxt] = depth[node] + 1
                queue.append(nxt)
    return None


def audit(graph: dict) -> dict:
    """Read-only integrity audit, including safe normalization diagnostics."""
    if not isinstance(graph.get("project"), dict) or not graph["project"].get("id"):
        raise ValueError("graph has no project.id")
    b = Builder(graph)
    normalized = b.output(graph["project"], graph.get("coverage", {}))
    return {"schema": normalized["schema"], "project": normalized["project"]["id"],
            "nodes": len(normalized["nodes"]), "edges": len(normalized["edges"]),
            "evidence": sum(len(n.get("evidence", [])) for n in normalized["nodes"]),
            "original_schema": graph.get("schema", "unknown"),
            "warnings": normalized["warnings"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("build", help="Build graph from normalized chat and fact JSON")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--existing", help="Previous Project Graphify graph.json")
    p.add_argument("--code-graph", help="Optional graph.json generated by original Graphify")
    p.add_argument("--include-message-text", action="store_true",
                   help="Explicitly include entire transcripts (may contain private information)")
    p = commands.add_parser("query", help="Search graph nodes by label, attributes and details")
    p.add_argument("--graph", required=True)
    p.add_argument("--term", required=True)
    p.add_argument("--limit", type=int, default=15)
    p = commands.add_parser("path", help="Find a directed shortest path between graph nodes")
    p.add_argument("--graph", required=True)
    p.add_argument("--from", dest="from_node", required=True)
    p.add_argument("--to", required=True)
    p.add_argument("--max-depth", type=int, default=10)
    p = commands.add_parser("audit", help="Read-only audit of a saved browser or CLI graph")
    p.add_argument("--graph", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            build(args)
        else:
            graph = json.loads(Path(args.graph).read_text(encoding="utf-8"))
            if args.command == "audit":
                print(json.dumps(audit(graph), indent=2, ensure_ascii=False))
            elif args.command == "query":
                print(json.dumps(query(graph, args.term, args.limit), indent=2, ensure_ascii=False))
            else:
                print(json.dumps(find_path(graph, args.from_node, args.to, args.max_depth),
                                 ensure_ascii=False))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"Project Graphify error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
