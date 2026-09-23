"""
Comprehensive unit tests for LinkBleed: URL normalization, link extraction, PageRank, leakage, and scoring.
"""

import unittest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from link_bleed.crawler import normalize_url, is_internal_url, extract_static_links
from link_bleed.graph import compute_pagerank, analyze_link_graph
from link_bleed.scorer import (
    calculate_leakage_score,
    calculate_depth_score,
    calculate_parity_score,
    calculate_orphan_score,
    score_link_graph,
)
from link_bleed.report_generator import export_markdown_report, export_json_report


class TestLinkBleedCrawler(unittest.TestCase):

    def test_normalize_url_valid(self):
        norm = normalize_url("/about#team", "https://example.com/blog/")
        self.assertEqual(norm, "https://example.com/about")

    def test_normalize_url_trailing_slash(self):
        norm = normalize_url("https://example.com/contact/", "")
        self.assertEqual(norm, "https://example.com/contact/")

    def test_normalize_url_ignore_pseudo_schemes(self):
        self.assertIsNone(normalize_url("mailto:team@example.com"))
        self.assertIsNone(normalize_url("tel:+1234567890"))
        self.assertIsNone(normalize_url("javascript:void(0)"))

    def test_is_internal_url(self):
        self.assertTrue(is_internal_url("https://example.com/pricing", "example.com"))
        self.assertTrue(is_internal_url("https://blog.example.com/post", "example.com"))
        self.assertFalse(is_internal_url("https://twitter.com/xcalibur73", "example.com"))

    def test_extract_static_links(self):
        html = """
        <html>
            <body>
                <a href="/pricing" rel="nofollow">Pricing</a>
                <a href="https://external.com">External</a>
                <a href="/features"><img alt="Product Features" src="img.png"></a>
            </body>
        </html>
        """
        links = extract_static_links(html, "https://example.com/")
        self.assertEqual(len(links), 3)

        pricing_link = next(l for l in links if "/pricing" in l["target_url"])
        self.assertTrue(pricing_link["is_nofollow"])
        self.assertEqual(pricing_link["anchor_text"], "Pricing")

        features_link = next(l for l in links if "/features" in l["target_url"])
        self.assertEqual(features_link["anchor_text"], "[Image: Product Features]")

    def test_extract_static_links_aria_label_and_title(self):
        html = """
        <html>
            <body>
                <a href="/dashboard" aria-label="Go to User Dashboard"><svg></svg></a>
                <a href="/settings" title="Account Settings"><i></i></a>
                <a href="/profile"><span aria-label="View Profile"></span></a>
            </body>
        </html>
        """
        links = extract_static_links(html, "https://example.com/")
        self.assertEqual(len(links), 3)

        dash_link = next(l for l in links if "/dashboard" in l["target_url"])
        self.assertEqual(dash_link["anchor_text"], "Go to User Dashboard")

        settings_link = next(l for l in links if "/settings" in l["target_url"])
        self.assertEqual(settings_link["anchor_text"], "Account Settings")

        profile_link = next(l for l in links if "/profile" in l["target_url"])
        self.assertEqual(profile_link["anchor_text"], "View Profile")


class TestLinkBleedGraphAndPageRank(unittest.TestCase):

    def test_pagerank_simple_cycle(self):
        nodes = ["https://ex.com/a", "https://ex.com/b"]
        edges = [("https://ex.com/a", "https://ex.com/b"), ("https://ex.com/b", "https://ex.com/a")]
        pr = compute_pagerank(nodes, edges)
        self.assertAlmostEqual(pr["https://ex.com/a"], 0.5, places=3)
        self.assertAlmostEqual(pr["https://ex.com/b"], 0.5, places=3)
        self.assertAlmostEqual(sum(pr.values()), 1.0, places=4)

    def test_pagerank_dangling_node(self):
        # A links to B, B has no outgoing links (dangling)
        nodes = ["https://ex.com/a", "https://ex.com/b"]
        edges = [("https://ex.com/a", "https://ex.com/b")]
        pr = compute_pagerank(nodes, edges)
        self.assertGreater(pr["https://ex.com/b"], pr["https://ex.com/a"])
        self.assertAlmostEqual(sum(pr.values()), 1.0, places=4)

    def test_analyze_link_graph_leakage_and_orphans(self):
        crawl_data = {
            "start_url": "https://example.com/",
            "base_domain": "example.com",
            "crawled_nodes": {
                "https://example.com/": {"status_code": 200, "crawl_depth": 0, "is_redirect": False},
                "https://example.com/blog": {"status_code": 200, "crawl_depth": 1, "is_redirect": False},
                "https://example.com/dead": {"status_code": 404, "crawl_depth": 1, "is_redirect": False},
            },
            "edges": [
                {
                    "source_url": "https://example.com/",
                    "target_url": "https://example.com/blog",
                    "anchor_text": "Blog",
                    "is_internal": True,
                    "is_static": True,
                    "is_dynamic": False,
                    "is_nofollow": False,
                },
                {
                    "source_url": "https://example.com/",
                    "target_url": "https://example.com/dead",
                    "anchor_text": "Broken Link",
                    "is_internal": True,
                    "is_static": True,
                    "is_dynamic": False,
                    "is_nofollow": False,
                },
                {
                    "source_url": "https://example.com/",
                    "target_url": "https://external.org",
                    "anchor_text": "External Partner",
                    "is_internal": False,
                    "is_static": True,
                    "is_dynamic": False,
                    "is_nofollow": False,
                },
            ],
            "sitemap_urls": ["https://example.com/orphan-page"],
            "mode": "http_static",
        }

        res = analyze_link_graph(crawl_data)
        self.assertGreater(res["pagerank_leakage_ratio_percent"], 0.0)
        self.assertGreaterEqual(res["orphan_count"], 1)
        self.assertTrue(any(o["url"] == "https://example.com/orphan-page" for o in res["orphan_pages"]))


class TestLinkBleedScorer(unittest.TestCase):

    def test_leakage_score(self):
        self.assertEqual(calculate_leakage_score(2.0), 100.0)
        self.assertLess(calculate_leakage_score(40.0), 30.0)

    def test_depth_score(self):
        depth_dist = {0: 1, 1: 5, 2: 10, 3: 2, 4: 0}
        self.assertEqual(calculate_depth_score(depth_dist, 3), 90.0)

    def test_score_link_graph_grade(self):
        mock_graph = {
            "pagerank_leakage_ratio_percent": 3.5,
            "crawl_depth_distribution": {0: 1, 1: 4, 2: 8, 3: 1, 4: 0},
            "max_crawl_depth": 3,
            "total_internal_pages": 14,
            "orphan_count": 0,
            "js_only_link_count": 0,
            "equity_sinks_count": 0,
        }
        res = score_link_graph(mock_graph)
        self.assertIn(res["grade"], ("A+", "A"))
        self.assertGreaterEqual(res["overall_score"], 90.0)


class TestLinkBleedReports(unittest.TestCase):

    def test_markdown_export(self):
        audit_res = {
            "url": "https://example.com",
            "overall_score": 92.5,
            "grade": "A",
            "mode": "http_static",
            "component_scores": {
                "equity_preservation": 100.0,
                "crawl_depth_efficiency": 90.0,
                "static_parity": 100.0,
                "orphan_prevention": 85.0,
                "equity_distribution": 100.0,
            },
            "graph_analysis": {
                "total_internal_pages": 10,
                "total_internal_edges": 18,
                "pagerank_leakage_ratio_percent": 4.2,
                "leakage_breakdown": {
                    "external_leakage_ratio": 2.0,
                    "dead_end_leakage_ratio": 0.0,
                    "nofollow_leakage_ratio": 0.0,
                    "redirect_leakage_ratio": 0.0,
                },
                "orphan_count": 0,
                "js_only_link_count": 0,
                "crawl_depth_distribution": {0: 1, 1: 5, 2: 4, 3: 0, 4: 0},
            },
            "recommendations": ["Internal link graph is healthy."],
        }
        md = export_markdown_report(audit_res)
        self.assertIn("# LinkBleed Internal Link Graph Audit", md)
        self.assertIn("Architecture Score", md)

        js = export_json_report(audit_res)
        self.assertIn("overall_score", js)


if __name__ == "__main__":
    unittest.main()
