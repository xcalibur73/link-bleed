# LinkBleed

Internal link graph and orphan page discovery engine.

Part of the [WebAudits.pro](https://webaudits.pro) technical intelligence platform.

---

## Quickstart

Install in editable mode and audit internal link equity in seconds:

```bash
# Clone and install
git clone https://github.com/xcalibur73/link-bleed.git
cd link-bleed
pip install -r requirements.txt
pip install -e .

# Audit target URL
link-bleed https://example.com

# Fast static inspection mode
link-bleed https://example.com --fast
```

---

## What It Does & Why It Matters

LinkBleed crawls a website's internal architecture to construct a directed link graph, trace crawl depth, and audit internal link equity circulation.

Standard SEO crawlers rely on static HTML parsing, missing links hidden behind client-side user interactions (dropdown navigation menus, tab clicks, lazy carousels) while ignoring internal equity sinks where authority flows out of the domain or into redirect chains.

LinkBleed bridges static HTML and dynamic headless Chromium crawl paths:
- **Link Equity Distribution:** Evaluates relative internal authority using an in-memory power iteration graph model (0.85 damping factor).
- **Estimated Equity Leakage Heuristic:** Identifies where internal equity dissipates (external domain links, 404 dead ends, internal `rel="nofollow"` attributes, redirect hops).
- **True Orphan Detection:** Cross-references crawled internal nodes against XML sitemaps to locate URLs with zero inbound internal links.
- **Dynamic JS Navigation Discrepancies:** Isolates links discovered exclusively through CDP interaction routines versus static HTML parsing.
- **Crawl Depth Hierarchy:** Quantifies click distance from root and flags deep pages (> 3 clicks) suffering equity attenuation.

---

## Usage & CLI Options

```bash
# Audit an origin domain (up to 15 pages)
link-bleed https://webaudits.pro

# Fast static inspection mode (skips Chromium CDP browser)
link-bleed https://example.com --fast

# Cross-reference with custom sitemap to locate true orphans
link-bleed https://example.com --sitemap https://example.com/sitemap.xml --max-pages 25

# Export machine-readable JSON for CI/CD architecture checks
link-bleed https://example.com --output json --save link-audit.json

# Check installed version
link-bleed --version
```

---

## Example Output

```text
+-------------------------------------------------------------------------------+
| LinkBleed: Internal Link Graph & Equity Auditor                               |
| Target URL: https://webaudits.pro                                             |
| Architecture Health Score: 94.2/100 (Grade: A)                                |
| Crawled Pages: 12 | Internal Edges: 148 | External Edges: 14 | Orphans: 0     |
+-------------------------------------------------------------------------------+

Component Score Breakdown:
+-----------------------------------+--------+------------+
| Component Dimension               | Weight | Score      |
+-----------------------------------+--------+------------+
| Link Equity Preservation          | 30%    | 95.0/100   |
| Crawl Depth Efficiency            | 25%    | 100.0/100  |
| Static vs. Dynamic Parity         | 20%    | 90.0/100   |
| Orphan Page Prevention            | 15%    | 100.0/100  |
| Equity Distribution Balance       | 10%    | 86.0/100   |
+-----------------------------------+--------+------------+

Link-Equity Leakage Breakdown (Project-Defined Heuristic):
- External Outbound Leakage: 8.6% (14 links to authority targets)
- 404 Dead End Sinks: 0.0% (0 broken destination links)
- Nofollow Equity Waste: 0.0% (0 internal nofollow directives)
- Redirect Attenuation: 0.0% (Clean direct links)
```

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

- `crawler.py`: Crawls internal URLs up to a user-defined threshold, running both raw HTTP requests and CDP interaction routines.
- `graph.py`: Builds a directed graph from extracted links, runs PageRank-style power iteration, maps crawl depth from origin, and calculates leakage percentages.
- `scorer.py`: Evaluates architecture health across five weighted dimensions: Equity Preservation, Crawl Depth Efficiency, Static vs. Dynamic Parity, Orphan Prevention, and Equity Distribution Balance.

---

## Standards & Heuristics

LinkBleed separates formal web standards from project-derived graph heuristics:

| Metric / Check | Classification | Authority / Basis |
|:---|:---|:---|
| HTML Anchor Specifications | Web Standard | W3C HTML5 Specification |
| XML Sitemap Schema | Web Standard | Sitemaps.org Protocol |
| Simulated Link-Equity | Project-Derived Heuristic | Power iteration algorithm with 0.85 damping factor |
| Equity Leakage Heuristic | Project-Derived Heuristic | Ratio of dissipated outbound and broken edge weights |
| Architecture Health Score | Project-Derived Heuristic | 5-factor weighted internal linking formula |

> **Estimated Equity vs. Google PageRank:** The link-equity metrics reported are project-defined heuristics modeling topological connectivity within the crawled sample. They do not represent Google's internal PageRank database or search ranking algorithms.

---

## Limitations

- **Crawl Sample Scope:** Intended for targeted architectural audits (up to 50 pages); comprehensive multi-thousand URL audits should be processed via dedicated enterprise batch pipelines.
- **Topological Simulation:** Power iteration models structural link equity flow within the audited subgraph; external backlink signals from third-party domains are excluded from internal calculations.
- **Authentication Barriers:** Focuses on publicly discoverable internal link paths; password-protected sections or shopping carts are excluded from standard crawls.

---

## Testing & CI

```bash
# Run unit tests
python -m unittest discover -s tests

# Output
# Ran 12 tests in 0.002s
# OK
```

Continuous integration runs automatically across Ubuntu and Windows runners on every commit via GitHub Actions.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
