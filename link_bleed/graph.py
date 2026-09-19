"""
Graph builder, PageRank power iteration, and PageRank Leakage Ratio analyzer for LinkBleed.
"""

from typing import Dict, Any, List, Set, Tuple, Optional
import collections
import math


def compute_pagerank(
    nodes: List[str],
    edges: List[Tuple[str, str]],
    damping: float = 0.85,
    max_iter: int = 100,
    tol: float = 1e-6,
) -> Dict[str, float]:
    """
    Computes PageRank using Power Iteration with handling for dangling nodes.
    - nodes: list of unique URL strings
    - edges: list of (source, target) tuples
    - damping: damping factor (default 0.85)
    Returns dict mapping node to normalized PageRank score (sum = 1.0).
    """
    n = len(nodes)
    if n == 0:
        return {}
    if n == 1:
        return {nodes[0]: 1.0}

    node_set = set(nodes)
    node_to_idx = {node: i for i, node in enumerate(nodes)}

    # Build adjacency mapping (outgoing edges)
    out_edges = collections.defaultdict(list)
    for src, tgt in edges:
        if src in node_set and tgt in node_set:
            out_edges[src].append(tgt)

    # Initialize uniform PageRank vector
    pr = [1.0 / n] * n

    for iteration in range(max_iter):
        next_pr = [(1.0 - damping) / n] * n
        dangling_sum = 0.0

        for i, node in enumerate(nodes):
            out_targets = out_edges.get(node, [])
            if not out_targets:
                dangling_sum += pr[i]
            else:
                share = (damping * pr[i]) / len(out_targets)
                for tgt in out_targets:
                    tgt_idx = node_to_idx[tgt]
                    next_pr[tgt_idx] += share

        # Distribute dangling node equity uniformly
        if dangling_sum > 0:
            dangling_share = (damping * dangling_sum) / n
            for i in range(n):
                next_pr[i] += dangling_share

        # Check convergence
        diff = sum(abs(next_pr[i] - pr[i]) for i in range(n))
        pr = next_pr
        if diff < tol:
            break

    # Normalize sum to 1.0
    total = sum(pr)
    if total > 0:
        pr = [p / total for p in pr]

    return {nodes[i]: pr[i] for i in range(n)}


def analyze_link_graph(crawl_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyzes the complete internal link graph:
    1. Builds directed graph
    2. Runs PageRank simulation
    3. Calculates PageRank Leakage Ratio
    4. Identifies orphan pages, JS-only discrepancies, and dead-end equity traps
    5. Computes crawl depth distribution
    """
    crawled_nodes = crawl_data.get("crawled_nodes", {})
    all_edges = crawl_data.get("edges", [])
    sitemap_urls = crawl_data.get("sitemap_urls", [])
    base_domain = crawl_data.get("base_domain", "")

    # Define universe of internal nodes:
    # All crawled pages + sitemap pages + internal link targets
    internal_nodes_set: Set[str] = set(crawled_nodes.keys())
    for url in sitemap_urls:
        internal_nodes_set.add(url)
    for edge in all_edges:
        if edge.get("is_internal"):
            internal_nodes_set.add(edge["target_url"])
            internal_nodes_set.add(edge["source_url"])

    internal_nodes = sorted(list(internal_nodes_set))
    total_internal_pages = len(internal_nodes)

    if total_internal_pages == 0:
        return {
            "total_pages": 0,
            "pagerank_leakage_ratio": 0.0,
            "status": "No internal pages found",
        }

    # Extract internal directed edges for PageRank calculation
    internal_graph_edges: List[Tuple[str, str]] = []
    in_links = collections.defaultdict(list)
    out_links = collections.defaultdict(list)
    external_out_links = collections.defaultdict(list)
    static_in_links = collections.defaultdict(list)
    dynamic_in_links = collections.defaultdict(list)
    nofollow_internal_links = []
    redirect_edges = []

    for edge in all_edges:
        src = edge["source_url"]
        tgt = edge["target_url"]
        is_internal = edge.get("is_internal", False)
        is_static = edge.get("is_static", True)
        is_dynamic = edge.get("is_dynamic", False)
        is_nofollow = edge.get("is_nofollow", False)

        if is_internal:
            out_links[src].append(tgt)
            in_links[tgt].append(src)

            if is_static:
                static_in_links[tgt].append(src)
            if is_dynamic and not is_static:
                dynamic_in_links[tgt].append(src)

            if is_nofollow:
                nofollow_internal_links.append(edge)

            # Node status check
            tgt_info = crawled_nodes.get(tgt, {})
            if tgt_info.get("is_redirect"):
                redirect_edges.append(edge)

            # Only followable internal edges transfer full PageRank
            if not is_nofollow:
                internal_graph_edges.append((src, tgt))
        else:
            external_out_links[src].append(tgt)

    # Calculate PageRank
    pagerank_map = compute_pagerank(internal_nodes, internal_graph_edges)

    # 1. PageRank Leakage Ratio Calculation
    # Leakage vectors:
    # A. External links from internal pages: equity directed out of site
    # B. Internal links to 404 or dead ends
    # C. Internal links tagged with rel="nofollow" (equity destroyed)
    # D. Internal links passing through 301/302 redirects
    total_weighted_leakage = 0.0
    external_leakage_weight = 0.0
    dead_leakage_weight = 0.0
    nofollow_leakage_weight = 0.0
    redirect_leakage_weight = 0.0

    for node in internal_nodes:
        pr_score = pagerank_map.get(node, 0.0)
        total_out = len(out_links.get(node, [])) + len(external_out_links.get(node, []))
        if total_out == 0:
            continue

        # External leakage
        ext_count = len(external_out_links.get(node, []))
        if ext_count > 0:
            ext_leak = pr_score * (ext_count / total_out)
            external_leakage_weight += ext_leak

        # Internal leaking edges
        int_targets = out_links.get(node, [])
        for tgt in int_targets:
            tgt_status = crawled_nodes.get(tgt, {}).get("status_code", 200)
            is_redirect = crawled_nodes.get(tgt, {}).get("is_redirect", False)

            # 404 or broken
            if tgt_status in (404, 410, 500, 502, 503, 0):
                dead_leakage_weight += pr_score * (1.0 / total_out)

            # Redirect
            if is_redirect:
                redirect_leakage_weight += pr_score * (0.15 / total_out)  # 15% crawl/equity dissipation

    for edge in nofollow_internal_links:
        src = edge["source_url"]
        pr_score = pagerank_map.get(src, 0.0)
        total_out = max(1, len(out_links.get(src, [])) + len(external_out_links.get(src, [])))
        nofollow_leakage_weight += pr_score * (1.0 / total_out)

    total_weighted_leakage = (
        external_leakage_weight * 0.40  # External links are natural, scaled to 40% weight
        + dead_leakage_weight * 1.00     # Broken links are 100% waste
        + nofollow_leakage_weight * 0.80 # Internal nofollow is 80% waste
        + redirect_leakage_weight * 0.50 # Redirects are 50% waste
    )

    leakage_ratio_percent = min(100.0, round(total_weighted_leakage * 100.0, 2))

    # 2. Orphan Pages Identification
    # Pages that exist in sitemap or were visited, but have ZERO internal in-links from crawl
    orphan_pages = []
    start_url = crawl_data.get("start_url", "")
    for node in internal_nodes:
        if node == start_url:
            continue
        in_degree = len(in_links.get(node, []))
        if in_degree == 0:
            orphan_pages.append({
                "url": node,
                "in_sitemap": node in sitemap_urls,
                "pagerank": round(pagerank_map.get(node, 0.0) * 1000, 3),
            })

    # 3. JS-Only Discrepancy Identification
    # Pages that have static_in_links == 0, but dynamic_in_links > 0
    js_only_pages = []
    for node in internal_nodes:
        if len(static_in_links.get(node, [])) == 0 and len(dynamic_in_links.get(node, [])) > 0:
            js_only_pages.append({
                "url": node,
                "dynamic_inlinks_count": len(dynamic_in_links.get(node, [])),
                "inbound_sources": dynamic_in_links.get(node, [])[:3],
            })

    # 4. Crawl Depth Distribution
    depth_distribution = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    max_depth = 0
    for node, info in crawled_nodes.items():
        d = info.get("crawl_depth", 0)
        bucket = min(4, d)
        depth_distribution[bucket] = depth_distribution.get(bucket, 0) + 1
        if d > max_depth:
            max_depth = d

    # 5. High Equity Traps / Sinks
    # Pages in top 20% PageRank that have 0 internal outgoing links
    sorted_by_pr = sorted(pagerank_map.items(), key=lambda x: x[1], reverse=True)
    equity_sinks = []
    top_threshold = sorted_by_pr[max(1, len(sorted_by_pr) // 5)][1] if len(sorted_by_pr) >= 5 else 0.0
    for node, pr_score in sorted_by_pr:
        if pr_score >= top_threshold and len(out_links.get(node, [])) == 0:
            equity_sinks.append({
                "url": node,
                "pagerank": round(pr_score * 1000, 3),
                "in_links_count": len(in_links.get(node, [])),
            })

    # Top PageRank distribution
    top_pages_by_equity = [
        {
            "url": node,
            "pagerank_score": round(score * 1000, 3),
            "in_links": len(in_links.get(node, [])),
            "out_links": len(out_links.get(node, [])),
            "depth": crawled_nodes.get(node, {}).get("crawl_depth", 0),
        }
        for node, score in sorted_by_pr[:10]
    ]

    return {
        "total_internal_pages": total_internal_pages,
        "total_internal_edges": len(internal_graph_edges),
        "total_external_edges": sum(len(ext) for ext in external_out_links.values()),
        "pagerank_leakage_ratio_percent": leakage_ratio_percent,
        "leakage_breakdown": {
            "external_leakage_ratio": round(external_leakage_weight * 100, 2),
            "dead_end_leakage_ratio": round(dead_leakage_weight * 100, 2),
            "nofollow_leakage_ratio": round(nofollow_leakage_weight * 100, 2),
            "redirect_leakage_ratio": round(redirect_leakage_weight * 100, 2),
        },
        "orphan_count": len(orphan_pages),
        "orphan_pages": orphan_pages[:10],
        "js_only_link_count": len(js_only_pages),
        "js_only_pages": js_only_pages[:10],
        "equity_sinks_count": len(equity_sinks),
        "equity_sinks": equity_sinks[:5],
        "crawl_depth_distribution": depth_distribution,
        "max_crawl_depth": max_depth,
        "top_pages_by_equity": top_pages_by_equity,
    }
