"""
LinkBleed CLI: Internal Link Graph & Orphan Page Discovery Engine.
"""

import argparse
import json
import sys

from link_bleed.crawler import crawl_site_graph
from link_bleed.graph import analyze_link_graph
from link_bleed.scorer import score_link_graph
from link_bleed.report_generator import (
    print_terminal_report,
    export_markdown_report,
    export_json_report,
)


def run_audit(
    url: str,
    fast: bool = False,
    max_pages: int = 15,
    sitemap_url: str = None,
    simulate_interaction: bool = True,
) -> dict:
    """Execute complete internal link graph audit pipeline on a URL."""
    crawl_data = crawl_site_graph(
        start_url=url,
        max_pages=max_pages,
        use_cdp=not fast,
        simulate_interaction=simulate_interaction,
        sitemap_url=sitemap_url,
    )
    graph_analysis = analyze_link_graph(crawl_data)
    scores = score_link_graph(graph_analysis)

    return {
        "url": crawl_data["start_url"],
        "base_domain": crawl_data["base_domain"],
        "mode": crawl_data["mode"],
        "overall_score": scores["overall_score"],
        "grade": scores["grade"],
        "component_scores": scores["component_scores"],
        "recommendations": scores["recommendations"],
        "graph_analysis": graph_analysis,
    }


def main():
    parser = argparse.ArgumentParser(
        description="LinkBleed: The Internal Link Graph & Orphan Page Discovery Engine",
        epilog="Example: python run.py https://webaudits.pro --max-pages 20",
    )
    parser.add_argument(
        "url",
        help="Target URL or domain root to audit for internal link architecture and PageRank leakage.",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Fast static HTTP scraping mode (skips Chromium CDP browser).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=15,
        help="Maximum internal pages to crawl (default: 15).",
    )
    parser.add_argument(
        "--sitemap",
        type=str,
        default=None,
        help="Optional custom sitemap URL to audit for true orphan pages.",
    )
    parser.add_argument(
        "--no-interaction",
        action="store_true",
        help="Disable automated scrolling and dropdown clicks in CDP mode.",
    )
    parser.add_argument(
        "--output",
        choices=["terminal", "markdown", "json"],
        default="terminal",
        help="Output format (default: terminal).",
    )
    parser.add_argument(
        "--save",
        type=str,
        default=None,
        help="Save report to file path.",
    )

    args = parser.parse_args()

    target_url = args.url.strip()
    if not target_url.startswith("http://") and not target_url.startswith("https://"):
        target_url = "https://" + target_url

    print(f"LinkBleed: Crawling internal link graph on {target_url}...")

    try:
        audit_result = run_audit(
            url=target_url,
            fast=args.fast,
            max_pages=args.max_pages,
            sitemap_url=args.sitemap,
            simulate_interaction=not args.no_interaction,
        )
    except Exception as e:
        print(f"Error during LinkBleed audit: {e}", file=sys.stderr)
        sys.exit(1)

    if args.output == "terminal":
        print_terminal_report(audit_result)
    elif args.output == "markdown":
        md = export_markdown_report(audit_result)
        print(md)
    elif args.output == "json":
        js = export_json_report(audit_result)
        print(js)

    if args.save:
        save_path = args.save
        if save_path.endswith(".json"):
            content = export_json_report(audit_result)
        elif save_path.endswith(".md"):
            content = export_markdown_report(audit_result)
        else:
            content = export_json_report(audit_result)

        with open(save_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"\nReport saved to: {save_path}")


if __name__ == "__main__":
    main()
