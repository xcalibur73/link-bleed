# LinkBleed

Internal link graph and orphan page discovery engine.

Part of the [WebAudits.pro](https://webaudits.pro) technical intelligence platform.

---

## What it does

LinkBleed crawls a website's internal architecture to construct a directed link graph, trace crawl depth, and audit link equity flow. It analyzes:
- Internal link equity distribution using an in-memory power iteration graph model (0.85 damping factor).
- Estimated link-equity leakage resulting from external domain links, 404 dead ends, internal `rel="nofollow"` tags, and redirect hops.
- True orphan pages (URLs present in XML sitemaps but possessing zero inbound internal links).
- Dynamic JavaScript navigation discrepancies (links discovered exclusively through CDP interaction routines versus static HTML parsing).
- Crawl depth hierarchy and equity attenuation across depth tiers (click distance from root).

---

## Why it exists

Standard SEO crawlers rely on static HTML parsing. They frequently miss two critical structural issues:
1. Links hidden behind client-side user interactions (dropdown navigation menus, tab clicks, lazy-loaded carousels) that execute only in modern browser event loops.
2. Unintentional link equity sinks: high-value pages that route internal authority out of the domain or into multi-hop redirect chains rather than circulating it through core product and article clusters.

LinkBleed bridges static HTML and dynamic headless Chromium crawl paths, providing an empirical model of site-wide link architecture.

---

## Key features

- **Hybrid Crawl Engine:** Combines fast static HTTP parsing with headless Chromium CDP interaction loops (scrolling, clicking navigation controls).
- **In-Memory Graph Engine:** Constructs directed adjacency matrices and computes simulated link-equity vectors via power iteration.
- **Leakage Vector Breakdown:** Quantifies where internal equity dissipates (external domain leakage, dead ends, nofollow attributes, redirect attenuation).
- **XML Sitemap Discrepancy Auditing:** Cross-references crawled internal nodes against XML sitemaps to isolate true orphan URLs.
- **Actionable Remediation Engine:** Generates prioritized linking recommendations to rebalance equity distribution and eliminate crawl depth traps.

---

## Architecture

```text
[Origin URL + Optional Sitemap]
                |
                v
      [Hybrid Crawl Engine]
                |
                +---> Static HTML Request Pool
                +---> Chromium CDP Interaction Runner (Scroll, Click)
                |
                v
    [Adjacency Matrix Builder]
                |
                +---> Directed Inbound / Outbound Edge Mapping
                +---> Power Iteration Model (0.85 Damping Factor)
                +---> Breadth-First Search (BFS) Crawl Depth Mapping
                +---> Sitemap Orphan Cross-Referencing
                |
                v
  [Link Equity Scoring Engine]
                |
                +---> Terminal Report (Rich Table)
                +---> Markdown Document / JSON Pipeline Output
```

LinkBleed operates in three stages:
1. `crawler.py`: Crawls internal URLs up to a user-defined threshold (default: 15 pages), running both raw HTTP requests and CDP interaction routines.
2. `graph.py`: Builds a directed graph from extracted links, runs PageRank-style power iteration, maps crawl depth from origin, and calculates leakage percentages.
3. `scorer.py`: Evaluates architecture health across five weighted dimensions: Equity Preservation, Crawl Depth Efficiency, Static vs. Dynamic Parity, Orphan Prevention, and Equity Distribution Balance.

---

## Installation

### Prerequisites
- Python 3.10 or higher
- Google Chrome or Chromium installed and available in system PATH

### Install from Source
```bash
git clone https://github.com/xcalibur73/link-bleed.git
cd link-bleed
pip install -r requirements.txt
pip install -e .
```

---

## Usage

### Basic CLI Invocation
```bash
# Audit an origin domain (up to 15 pages)
link-bleed https://webaudits.pro

# Fast static inspection mode (skips Chromium CDP browser)
link-bleed https://example.com --fast

# Cross-reference with custom sitemap to locate true orphans
link-bleed https://example.com --sitemap https://example.com/sitemap.xml --max-pages 25

# Export JSON report for CI/CD internal link auditing
link-bleed https://example.com --output json --save link-graph.json

# Check installed version
link-bleed --version
```

---

## Example output

```text
+-------------------------------------------------------------------------------+
| LinkBleed: Internal Link Graph & Orphan Page Discovery Engine                 |
| Target Origin: https://webaudits.pro                                          |
| Architecture Score: 96.2/100 (Grade: A)                                       |
| Mode: cdp_interactive | Crawled Pages: 15 | Edges: 248 | Leakage: 2.1% | 0 Orphans |
+-------------------------------------------------------------------------------+

Architecture Score Breakdown:
+--------------------------------------+--------+------------+
| Architecture Dimension               | Weight | Score      |
+--------------------------------------+--------+------------+
| PageRank Equity Preservation         | 30%    | 98.0/100   |
| Crawl Depth Efficiency (<= 3 clicks) | 25%    | 100.0/100  |
| Static HTML vs Dynamic Link Parity   | 20%    | 95.0/100   |
| Orphan Page Prevention               | 15%    | 100.0/100  |
| Link Equity Distribution Balance     | 10%    | 88.0/100   |
+--------------------------------------+--------+------------+

PageRank Equity Leakage Vectors:
- Site-Wide PageRank Leakage Ratio: 2.1% (Estimated link-equity leakage heuristic)
- External Domain Equity Loss: 1.4%
- Dead End / 404 Equity Sinks: 0.0%
- Internal rel='nofollow' Losses: 0.0%
- Redirect Attenuation (301/302): 0.7%
```

---

## Benchmark / methodology

### Empirical 12-Site Internal Link Graph Study
- **Dataset:** 12 production websites across media, e-commerce, and SaaS documentation hubs.
- **Command Used:** `python run.py <url> --max-pages 20 --output json`
- **Tool Version:** LinkBleed v1.0.0
- **Environment:** Windows 11, Chromium 128.0, Python 3.12, unthrottled fiber network.
- **Mathematical Calculation:**
  - Power iteration formula: `PR(p) = (1 - d)/N + d * sum(PR(q) / out_links(q))` with damping factor `d = 0.85`.
  - Link equity leakage ratio: `(equity_transferred_externally_or_attenuated / total_system_equity) * 100`.
- **Results:**
  - Identified up to 28.1% estimated link equity leakage on publishing properties due to unattenuated external partner links in primary navigation templates.
  - Complete study dataset: [BENCHMARKS.md](BENCHMARKS.md).

---

## Limitations

- **Diagnostic Heuristic Disclaimer:** The Estimated Link-Equity Leakage Ratio and PageRank scores are project-derived mathematical simulations based on public graph theory literature (Page et al., 1998). They do not represent Google's proprietary live ranking computations, historical link weighting algorithms, or internal PageRank values.
- **Sample Scale:** Crawls up to a user-specified page limit (e.g. 50-100 pages). True domain-wide PageRank calculations require analyzing millions of URLs, which exceeds single-machine CLI memory bounds.
- **Form & Auth Navigation:** Does not submit search forms or traverse login walls to discover deep internal links.

---

## Accuracy / standards

LinkBleed categorizes its graph metrics and analysis as follows:

| Metric / Check | Classification | Authority / Standard |
|:---|:---|:---|
| Crawl Depth (Click Distance) | Web Standard | Breadth-First Search (BFS) Graph Theory |
| Link Parsing & URL Normalization | Web Standard | RFC 3986 (URI Generic Syntax) |
| Simulated Link-Equity Vector | Project-Derived Heuristic | Power iteration model (0.85 damping) |
| Estimated Link-Equity Leakage | Project-Derived Heuristic | Damping loss to sinks & redirects |
| Dynamic Navigation Discrepancy | Experimental Metric | Differential between static & CDP crawl |

---

## Testing

LinkBleed includes unit tests covering crawl simulation, adjacency matrix construction, power iteration calculations, and orphan detection:

```bash
# Run unit test suite
python -m unittest discover -s tests

# Test execution output
# Ran 12 tests in 0.001s
# OK
```

Continuous integration runs automatically on every commit and pull request via GitHub Actions across Linux and Windows environments.

---

## Roadmap

- [x] Initial release with hybrid CDP crawler and power iteration graph solver.
- [x] PEP 621 packaging, CLI `--version`, and Windows cp1252 encoding safety.
- [ ] Gexf / Cytoscape JSON network export for interactive Gephi visualization.
- [ ] Integration with historical crawl archives to detect orphan link regression over time.
- [ ] WebAudits.pro automated internal linking health tracking.

---

## License

MIT License. See [LICENSE](LICENSE) for full details.
