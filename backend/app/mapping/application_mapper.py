"""
Application mapper.

Builds a directed graph connecting:
    Repository -> Source File -> Endpoint (method+path) -> Handler Function

Frontend component -> API relationships are added on a best-effort basis by
searching frontend files for fetch()/axios calls that reference a known
endpoint path. This is a heuristic, clearly labeled as such, not a
guarantee of a true call relationship.
"""
import re
from typing import List

import networkx as nx

from app.analyzers.endpoint_extractor import ExtractedEndpoint
from app.analyzers.repository_analyzer import RepoFileRef

CALL_PATTERN = re.compile(
    r"""(?:fetch|axios\.(?:get|post|put|patch|delete)|axios)\s*\(\s*[`'"]([^`'"]+)[`'"]""",
    re.IGNORECASE,
)


def build_application_map(
    files: List[RepoFileRef],
    endpoints: List[ExtractedEndpoint],
) -> nx.DiGraph:
    graph = nx.DiGraph()

    graph.add_node("repository", type="repository", label="Repository")

    for ep in endpoints:
        file_node = f"file::{ep.source_file}"
        if not graph.has_node(file_node):
            graph.add_node(file_node, type="file", label=ep.source_file)
            graph.add_edge("repository", file_node, relation="contains")

        ep_node = f"endpoint::{ep.method}::{ep.path}"
        graph.add_node(
            ep_node,
            type="endpoint",
            label=f"{ep.method} {ep.path}",
            method=ep.method,
            path=ep.path,
            requires_auth=ep.requires_auth,
            discovered_via=ep.discovered_via,
            source_file=ep.source_file,
            source_line=ep.source_line,
        )
        graph.add_edge(file_node, ep_node, relation="defines")

        if ep.handler_name:
            handler_node = f"handler::{ep.source_file}::{ep.handler_name}"
            graph.add_node(handler_node, type="function", label=ep.handler_name, source_file=ep.source_file)
            graph.add_edge(ep_node, handler_node, relation="handled_by")

    # Best-effort frontend -> endpoint linkage
    endpoint_paths = {ep.path for ep in endpoints}
    for f in files:
        if f.category != "frontend" or not f.content:
            continue
        for m in CALL_PATTERN.finditer(f.content):
            called = m.group(1)
            matched_path = next((p for p in endpoint_paths if p in called or called.endswith(p)), None)
            if not matched_path:
                continue
            fe_node = f"component::{f.path}"
            if not graph.has_node(fe_node):
                graph.add_node(fe_node, type="frontend_component", label=f.path)
                graph.add_edge("repository", fe_node, relation="contains")
            for ep in endpoints:
                if ep.path == matched_path:
                    ep_node = f"endpoint::{ep.method}::{ep.path}"
                    if graph.has_node(ep_node):
                        graph.add_edge(fe_node, ep_node, relation="calls (heuristic)")

    return graph


def graph_to_json(graph: nx.DiGraph) -> dict:
    nodes = [
        {"id": n, **{k: v for k, v in data.items()}}
        for n, data in graph.nodes(data=True)
    ]
    edges = [
        {"source": u, "target": v, "relation": data.get("relation", "")}
        for u, v, data in graph.edges(data=True)
    ]
    return {"nodes": nodes, "edges": edges}
