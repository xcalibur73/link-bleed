"""
Health scoring and actionable remediation engine for LinkBleed.
"""

from typing import Dict, Any, List


def calculate_leakage_score(leakage_percent: float) -> float:
    """Score PageRank equity preservation (0-100)."""
    if leakage_percent <= 5.0:
        return 100.0
    elif leakage_percent <= 10.0:
        return round(100.0 - ((leakage_percent - 5.0) * 3.0), 1)
    elif leakage_percent <= 20.0:
        return round(85.0 - ((leakage_percent - 10.0) * 2.5), 1)
    elif leakage_percent <= 35.0:
        return round(60.0 - ((leakage_percent - 20.0) * 2.0), 1)
    else:
        return max(0.0, round(30.0 - ((leakage_percent - 35.0) * 1.0), 1))


def calculate_depth_score(depth_dist: Dict[int, int], max_depth: int) -> float:
    """Score crawl depth efficiency (0-100)."""
    total = sum(depth_dist.values())
    if total == 0:
        return 100.0

    deep_pages = depth_dist.get(4, 0)
    deep_ratio = deep_pages / total

    if max_depth <= 2:
        base = 100.0
    elif max_depth == 3:
        base = 90.0
    elif max_depth == 4:
        base = 75.0
    else:
        base = 55.0

    penalty = min(30.0, deep_ratio * 100.0 * 0.5)
    return max(0.0, round(base - penalty, 1))


def calculate_parity_score(js_only_count: int, total_pages: int) -> float:
    """Score static vs dynamic link parity (0-100)."""
    if total_pages == 0 or js_only_count == 0:
        return 100.0
    js_ratio = js_only_count / max(1, total_pages)
    if js_ratio <= 0.05:
        return 95.0
    elif js_ratio <= 0.15:
        return 80.0
    elif js_ratio <= 0.30:
        return 60.0
    else:
        return max(15.0, round(50.0 - (js_ratio * 40.0), 1))


def calculate_orphan_score(orphan_count: int, total_pages: int) -> float:
    """Score orphan page prevention (0-100)."""
    if total_pages == 0 or orphan_count == 0:
        return 100.0
    orphan_ratio = orphan_count / max(1, total_pages)
    if orphan_ratio <= 0.05:
        return 85.0
    elif orphan_ratio <= 0.15:
        return 65.0
    elif orphan_ratio <= 0.30:
        return 40.0
    else:
        return max(0.0, round(30.0 - (orphan_ratio * 50.0), 1))


def score_link_graph(graph_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate composite architecture score, grades, and remediation recommendations."""
    leakage_percent = graph_analysis.get("pagerank_leakage_ratio_percent", 0.0)
    depth_dist = graph_analysis.get("crawl_depth_distribution", {})
    max_depth = graph_analysis.get("max_crawl_depth", 0)
    total_pages = graph_analysis.get("total_internal_pages", 0)
    orphan_count = graph_analysis.get("orphan_count", 0)
    js_only_count = graph_analysis.get("js_only_link_count", 0)
    equity_sinks_count = graph_analysis.get("equity_sinks_count", 0)

    leakage_score = calculate_leakage_score(leakage_percent)
    depth_score = calculate_depth_score(depth_dist, max_depth)
    parity_score = calculate_parity_score(js_only_count, total_pages)
    orphan_score = calculate_orphan_score(orphan_count, total_pages)
    balance_score = max(0.0, 100.0 - (equity_sinks_count * 15.0))

    # Composite weighted score (0-100)
    composite = round(
        (leakage_score * 0.30)
        + (depth_score * 0.25)
        + (parity_score * 0.20)
        + (orphan_score * 0.15)
        + (balance_score * 0.10),
        1,
    )

    if composite >= 95:
        grade = "A+"
    elif composite >= 85:
        grade = "A"
    elif composite >= 75:
        grade = "B"
    elif composite >= 65:
        grade = "C"
    elif composite >= 50:
        grade = "D"
    else:
        grade = "F"

    # Actionable recommendations
    recs = []
    if leakage_percent > 15.0:
        recs.append(
            f"Reduce PageRank leakage ({leakage_percent}% equity lost): Audit external links, "
            f"eliminate broken internal links (404s), and remove internal rel='nofollow' tags."
        )
    elif leakage_percent > 8.0:
        recs.append(
            f"Optimize link equity preservation ({leakage_percent}% leakage): Replace internal redirects "
            f"(301/302) with direct canonical targets to preserve PageRank flow."
        )

    if js_only_count > 0:
        recs.append(
            f"Convert {js_only_count} client-side JavaScript link(s) to semantic <a href> tags: "
            f"Links hidden behind JavaScript event listeners or custom button handlers are invisible "
            f"to search engine first-pass crawlers."
        )

    if orphan_count > 0:
        recs.append(
            f"Integrate {orphan_count} orphan page(s) into site hierarchy: These URLs exist in sitemaps "
            f"or routes but receive zero internal inbound links from crawled templates."
        )

    if max_depth >= 4:
        recs.append(
            f"Flatten crawl depth (current maximum: {max_depth} clicks): Introduce contextual internal links "
            f"from high-authority hub pages or category index templates to bring deep pages within 3 clicks."
        )

    if equity_sinks_count > 0:
        recs.append(
            f"Unblock {equity_sinks_count} high-equity terminal sink(s): These high-PageRank pages contain "
            f"no internal outgoing links, trapping accumulated authority rather than distributing it."
        )

    if not recs:
        recs.append(
            "Internal link graph is well optimized with healthy PageRank distribution, balanced crawl depth, "
            "and strong static HTML link parity."
        )

    return {
        "overall_score": composite,
        "grade": grade,
        "component_scores": {
            "equity_preservation": leakage_score,
            "crawl_depth_efficiency": depth_score,
            "static_parity": parity_score,
            "orphan_prevention": orphan_score,
            "equity_distribution": balance_score,
        },
        "recommendations": recs,
    }
