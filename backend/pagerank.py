import networkx as nx


def calculate_pagerank_analysis(crawl_result: dict, top_n: int = 10) -> dict:
    graph = nx.DiGraph()

    node_meta = {}
    for node in crawl_result["nodes"]:
        node_id = node["id"]
        node_meta[node_id] = node
        graph.add_node(node_id, depth=node.get("depth", 0))

    for edge in crawl_result["edges"]:
        src = edge["from"]
        dst = edge["to"]
        if src in node_meta and dst in node_meta:
            graph.add_edge(src, dst)

    if graph.number_of_nodes() == 0:
        return {
            "top_10": [],
            "graph_nodes": [],
            "graph_edges": [],
        }

    scores = nx.pagerank(graph, alpha=0.85, max_iter=100, tol=1e-06)

    ranked_items = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    top_10 = []

    for rank, (url, score) in enumerate(ranked_items[:top_n], start=1):
        meta = node_meta.get(url, {})
        top_10.append({
            "rank": rank,
            "url": url,
            "pagerank": round(float(score), 6),
            "depth": meta.get("depth", 0),
            "in_degree": graph.in_degree(url),
            "out_degree": graph.out_degree(url),
        })

    # Siapkan data node & edge untuk visualisasi graf di frontend
    max_score = max(scores.values()) if scores else 1.0
    top_10_urls = {item["url"] for item in top_10}

    graph_nodes = []
    for node_id in graph.nodes():
        meta = node_meta.get(node_id, {})
        pr_score = float(scores.get(node_id, 0.0))
        norm_score = (pr_score / max_score) if max_score > 0 else 0.0
        graph_nodes.append({
            "id": node_id,
            "label": node_id,
            "depth": meta.get("depth", 0),
            "pagerank": round(pr_score, 6),
            "in_degree": graph.in_degree(node_id),
            "out_degree": graph.out_degree(node_id),
            "is_top_10": node_id in top_10_urls,
            "size": round(12 + norm_score * 24, 2),
        })

    graph_edges = [
        {"from": src, "to": dst, "arrows": "to"}
        for src, dst in graph.edges()
    ]

    return {
        "top_10": top_10,
        "graph_nodes": graph_nodes,
        "graph_edges": graph_edges,
    }
