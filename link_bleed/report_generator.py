"""
Report generator for LinkBleed Internal Link Graph & Orphan Page Audits.
Outputs Rich terminal tables, Markdown documents, and JSON objects.
"""

import json
from typing import Dict, Any, List

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


def print_terminal_report(audit_result: Dict[str, Any]) -> None:
    """Print complete internal link graph audit report to terminal."""
    if not HAS_RICH:
        _print_plain_report(audit_result)
        return

    console = Console()

    url = audit_result.get("url", "")
    score = audit_result.get("overall_score", 0.0)
    grade = audit_result.get("grade", "F")
    graph = audit_result.get("graph_analysis", {})
    comp = audit_result.get("component_scores", {})
    mode = audit_result.get("mode", "http_static")

    score_color = "green" if score >= 80 else ("yellow" if score >= 60 else "red")

    header = Text()
    header.append("LinkBleed: Internal Link Graph & Orphan Page Discovery Engine\n", style="bold cyan")
    header.append(f"Target Origin: {url}\n", style="bold white")
    header.append(f"Architecture Score: {score}/100 (Grade: {grade})\n", style=f"bold {score_color}")
    header.append(
        f"Mode: {mode} | Crawled Pages: {graph.get('total_internal_pages')} | "
        f"Internal Edges: {graph.get('total_internal_edges')} | "
        f"Leakage Ratio: {graph.get('pagerank_leakage_ratio_percent')}% | "
        f"Orphans: {graph.get('orphan_count')}",
        style="dim",
    )

    console.print(Panel(header, border_style="cyan"))

    # Component Scores Table
    comp_table = Table(title="Architecture Score Breakdown", show_header=True, header_style="bold cyan")
    comp_table.add_column("Architecture Dimension", style="white")
    comp_table.add_column("Weight", justify="center", style="dim")
    comp_table.add_column("Score", justify="right", style="bold green")

    weights = {
        "equity_preservation": "30%",
        "crawl_depth_efficiency": "25%",
        "static_parity": "20%",
        "orphan_prevention": "15%",
        "equity_distribution": "10%",
    }
    labels = {
        "equity_preservation": "PageRank Equity Preservation",
        "crawl_depth_efficiency": "Crawl Depth Efficiency (<= 3 clicks)",
        "static_parity": "Static HTML vs Dynamic Link Parity",
        "orphan_prevention": "Orphan Page Prevention",
        "equity_distribution": "Link Equity Distribution Balance",
    }
    for k, v in comp.items():
        comp_table.add_row(labels.get(k, k), weights.get(k, "10%"), f"{v}/100")
    console.print(comp_table)

    # PageRank Leakage Breakdown Panel
    leakage = graph.get("leakage_breakdown", {})
    leak_text = Text()
    leak_text.append(f"Site-Wide PageRank Leakage Ratio: {graph.get('pagerank_leakage_ratio_percent')}%\n", style="bold yellow")
    leak_text.append(f"- External Domain Equity Loss: {leakage.get('external_leakage_ratio')}%\n", style="white")
    leak_text.append(f"- Dead End / 404 Equity Sinks: {leakage.get('dead_end_leakage_ratio')}%\n", style="white")
    leak_text.append(f"- Internal rel='nofollow' Losses: {leakage.get('nofollow_leakage_ratio')}%\n", style="white")
    leak_text.append(f"- Redirect Attenuation (301/302): {leakage.get('redirect_leakage_ratio')}%\n", style="white")
    console.print(Panel(leak_text, title="PageRank Equity Leakage Vectors", border_style="yellow"))

    # Crawl Depth Distribution
    depth_dist = graph.get("crawl_depth_distribution", {})
    depth_table = Table(title="Crawl Depth Hierarchy (Clicks from Root)", show_header=True, header_style="bold magenta")
    depth_table.add_column("Click Depth Level", style="white")
    depth_table.add_column("Page Count", justify="center", style="bold cyan")
    depth_table.add_column("Status", justify="right")

    for level in range(5):
        count = depth_dist.get(level, 0)
        lvl_str = f"Depth {level}" if level < 4 else "Depth 4+ (Risk)"
        status = "[green]Optimal[/green]" if level <= 2 else ("[yellow]Acceptable[/yellow]" if level == 3 else "[red]High Latency[/red]")
        depth_table.add_row(lvl_str, str(count), status)
    console.print(depth_table)

    # Top Equity Pages Table
    top_pages = graph.get("top_pages_by_equity", [])
    if top_pages:
        top_table = Table(title="Top Internal Pages by Calculated PageRank", show_header=True, header_style="bold blue")
        top_table.add_column("URL Path", style="cyan")
        top_table.add_column("In-Links", justify="center", style="white")
        top_table.add_column("Out-Links", justify="center", style="white")
        top_table.add_column("Depth", justify="center", style="dim")
        top_table.add_column("PageRank Index", justify="right", style="bold green")

        for p in top_pages[:6]:
            top_table.add_row(
                p.get("url", ""),
                str(p.get("in_links", 0)),
                str(p.get("out_links", 0)),
                str(p.get("depth", 0)),
                str(p.get("pagerank_score", 0.0)),
            )
        console.print(top_table)

    # Orphan & JS Discrepancies
    orphans = graph.get("orphan_pages", [])
    if orphans:
        orphan_table = Table(title=f"Detected Orphan Pages ({len(orphans)} sample)", show_header=True, header_style="bold red")
        orphan_table.add_column("Orphan URL", style="red")
        orphan_table.add_column("In Sitemap", justify="center", style="white")
        orphan_table.add_column("PageRank", justify="right", style="dim")
        for o in orphans[:5]:
            orphan_table.add_row(o.get("url", ""), str(o.get("in_sitemap", False)), str(o.get("pagerank", 0.0)))
        console.print(orphan_table)

    js_pages = graph.get("js_only_pages", [])
    if js_pages:
        js_table = Table(title=f"JavaScript-Only Links Discrepancies ({len(js_pages)} sample)", show_header=True, header_style="bold yellow")
        js_table.add_column("Dynamic Target URL", style="yellow")
        js_table.add_column("Dynamic Inbound Links", justify="center", style="white")
        for j in js_pages[:5]:
            js_table.add_row(j.get("url", ""), str(j.get("dynamic_inlinks_count", 0)))
        console.print(js_table)

    # Remediation Plan
    recs = audit_result.get("recommendations", [])
    if recs:
        rec_table = Table(title="Actionable Internal Linking Remediation", show_header=True, header_style="bold green")
        rec_table.add_column("Priority", justify="center", style="bold yellow")
        rec_table.add_column("Recommended Action", style="white")
        for idx, rec in enumerate(recs, 1):
            rec_table.add_row(str(idx), rec)
        console.print(rec_table)


def _print_plain_report(audit_result: Dict[str, Any]) -> None:
    """Plain-text report fallback when rich is not available."""
    url = audit_result.get("url", "")
    score = audit_result.get("overall_score", 0.0)
    grade = audit_result.get("grade", "F")
    graph = audit_result.get("graph_analysis", {})

    print("=" * 70)
    print(f"LinkBleed: Internal Link Graph & Orphan Page Discovery Engine")
    print(f"Target: {url}")
    print(f"Architecture Score: {score}/100 (Grade: {grade})")
    print(f"PageRank Leakage Ratio: {graph.get('pagerank_leakage_ratio_percent')}%")
    print(f"Total Internal Pages: {graph.get('total_internal_pages')}")
    print(f"Orphan Pages: {graph.get('orphan_count')}")
    print(f"JS-Only Links: {graph.get('js_only_link_count')}")
    print("=" * 70)
    print("\nActionable Remediation Steps:")
    for idx, rec in enumerate(audit_result.get("recommendations", []), 1):
        print(f"  {idx}. {rec}")
    print("=" * 70)


def export_markdown_report(audit_result: Dict[str, Any]) -> str:
    """Generate comprehensive Markdown audit report."""
    url = audit_result.get("url", "")
    score = audit_result.get("overall_score", 0.0)
    grade = audit_result.get("grade", "F")
    graph = audit_result.get("graph_analysis", {})
    comp = audit_result.get("component_scores", {})
    leakage = graph.get("leakage_breakdown", {})
    depth_dist = graph.get("crawl_depth_distribution", {})

    md = [
        f"# LinkBleed Internal Link Graph Audit: {url}",
        "",
        f"**Architecture Score**: `{score} / 100` (Grade: **{grade}**)  ",
        f"**Crawl Mode**: `{audit_result.get('mode')}`  ",
        f"**PageRank Leakage Ratio**: `{graph.get('pagerank_leakage_ratio_percent')}%`  ",
        f"**Total Pages Analyzed**: `{graph.get('total_internal_pages')}`  ",
        f"**Total Internal Directed Edges**: `{graph.get('total_internal_edges')}`  ",
        f"**Orphan Pages Detected**: `{graph.get('orphan_count')}`  ",
        f"**JavaScript-Only Links**: `{graph.get('js_only_link_count')}`  ",
        "",
        "---",
        "",
        "## Component Score Breakdown",
        "",
        "| Dimension | Weight | Score |",
        "|:---|:---:|:---:|",
        f"| PageRank Equity Preservation | 30% | {comp.get('equity_preservation', 0)}/100 |",
        f"| Crawl Depth Efficiency | 25% | {comp.get('crawl_depth_efficiency', 0)}/100 |",
        f"| Static HTML vs Dynamic Link Parity | 20% | {comp.get('static_parity', 0)}/100 |",
        f"| Orphan Page Prevention | 15% | {comp.get('orphan_prevention', 0)}/100 |",
        f"| Equity Distribution Balance | 10% | {comp.get('equity_distribution', 0)}/100 |",
        "",
        "---",
        "",
        "## PageRank Equity Leakage Vectors",
        "",
        f"- **External Outbound Leakage**: `{leakage.get('external_leakage_ratio')}%`",
        f"- **Dead End / 404 Leakage**: `{leakage.get('dead_end_leakage_ratio')}%`",
        f"- **Internal rel='nofollow' Loss**: `{leakage.get('nofollow_leakage_ratio')}%`",
        f"- **Redirect Hop Attenuation**: `{leakage.get('redirect_leakage_ratio')}%`",
        "",
        "---",
        "",
        "## Crawl Depth Distribution",
        "",
        "| Click Depth from Root | Page Count | Status |",
        "|:---:|:---:|:---|",
        f"| Depth 0 (Homepage) | {depth_dist.get(0, 0)} | Optimal |",
        f"| Depth 1 | {depth_dist.get(1, 0)} | Optimal |",
        f"| Depth 2 | {depth_dist.get(2, 0)} | Optimal |",
        f"| Depth 3 | {depth_dist.get(3, 0)} | Acceptable |",
        f"| Depth 4+ (Risk) | {depth_dist.get(4, 0)} | High Crawl Latency |",
        "",
        "---",
        "",
        "## Actionable Remediation Plan",
        "",
    ]

    for idx, rec in enumerate(audit_result.get("recommendations", []), 1):
        md.append(f"{idx}. {rec}")

    md.append("")
    return "\n".join(md)


def export_json_report(audit_result: Dict[str, Any]) -> str:
    """Generate formatted JSON report."""
    return json.dumps(audit_result, indent=2)
