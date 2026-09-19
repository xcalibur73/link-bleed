# LinkBleed

The Internal Link Graph & Orphan Page Discovery Engine

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Status: Production](https://img.shields.io/badge/status-production-success.svg)](#)
[![Cloud Engine: WebAudits.pro](https://img.shields.io/badge/cloud-webaudits.pro-orange.svg)](https://webaudits.pro/tools/link-bleed)

LinkBleed is a command-line utility and headless Chromium diagnostic engine that audits internal link architecture, calculates PageRank equity leakage, and uncovers hidden client-side routing discrepancies. Most standard SEO crawlers rely on static HTML scraping, completely missing dynamic JavaScript links injected by modern Single Page Application (SPA) routers, interactive menus, or click event listeners.

Key capabilities:
- Hybrid Static vs CDP Crawling: Compares raw HTML anchor tags against fully rendered DOM elements after simulated user interactions (scrolling, menu disclosure clicks, event triggers).
- PageRank Power Iteration Engine: Calculates stationary distribution vectors across internal URL nodes using an iterative power iteration matrix with damping factor d = 0.85 and dangling node equity redistribution.
- Site-Wide PageRank Leakage Ratio: Quantifies link equity lost through outbound external links, 404 dead ends, internal `rel="nofollow"` tags, and redirect hops (301/302).
- Dynamic SPA Route Interception: Hooks into `history.pushState` and `history.replaceState` via Chrome DevTools Protocol to identify client-side transitions invisible to standard bots.
- True Orphan Page Discovery: Ingests XML sitemaps to cross-reference declared canonical URLs against the internal crawl graph, isolating pages receiving zero internal inbound links.
- Crawl Depth Hierarchy Mapping: Measures shortest-path click depth from root to highlight content stranded at 4+ clicks.
- Multi-format reporting: High-contrast terminal dashboard, Markdown audit summaries, and automated JSON pipelines.

---

## The Engineering Problem

Internal linking is one of the highest-leverage organic search optimizations, yet traditional crawlers suffer from two critical architectural blind spots:

1. **The JavaScript Execution Void**: Modern web applications (built with Next.js, Nuxt, React, Vue) frequently render navigation menus, category filters, and pagination links via client-side JavaScript. If a link requires a click or viewport trigger to mount into the DOM, non-rendering search crawlers never discover it.
2. **PageRank Equity Leakage**: Site architectures unintentionally dissipate link equity. Every internal link pointing to a redirected URL (301/302), a broken resource (404), or tagged with `rel="nofollow"` evaporates PageRank that should flow to high-intent conversion pages.

LinkBleed bridges this gap by marrying headless Chromium interaction emulation with mathematical graph analysis.

---

## Mathematical Architecture

LinkBleed models the crawled domain as a directed graph G = (V, E), where:
- V represents the set of unique internal URL nodes.
- E represents the set of directed internal link edges.

### 1. Power Iteration PageRank

The PageRank vector PR is computed iteratively until convergence (|PR^(k+1) - PR^(k)| < 1e-6):

```
PR(u) = (1 - d) / N + d * (sum(PR(v) / Out(v)) + DanglingSum / N)
```

Where:
- d = 0.85 (standard damping factor)
- N = total internal nodes
- Out(v) = number of outgoing followable internal links from node v
- DanglingSum = sum of PageRank from nodes with Out(v) = 0, redistributed uniformly across all N nodes

### 2. PageRank Leakage Ratio

LinkBleed calculates site-wide equity leakage by weighting outgoing edges by the source page's computed PageRank:

```
Leakage Ratio = (0.40 * ExternalLeak + 1.00 * DeadEndLeak + 0.80 * NofollowLeak + 0.50 * RedirectLeak) * 100%
```

Where:
- `ExternalLeak`: Equity directed outside the root domain.
- `DeadEndLeak`: Equity flowing into 404, 410, or 500 status codes.
- `NofollowLeak`: Internal links carrying `rel="nofollow"`, which Google drops rather than redistributing.
- `RedirectLeak`: Equity dissipated across 301/302 redirect hops.

---

## Installation

```bash
git clone https://github.com/xcalibur73/link-bleed.git
cd link-bleed
pip install -r requirements.txt
```

---

## Usage Guide

### 1. Audit Internal Link Graph (Default Hybrid Mode)

```bash
python run.py https://example.com
```

### 2. Fast Static HTTP Scraping Mode

```bash
python run.py https://example.com --fast --max-pages 25
```

### 3. Cross-Reference Custom XML Sitemap for Orphan Discovery

```bash
python run.py https://example.com --sitemap https://example.com/sitemap.xml
```

### 4. Export Markdown Audit Report

```bash
python run.py https://example.com --output markdown --save audit_report.md
```

### 5. Export Structured JSON for CI/CD Quality Gates

```bash
python run.py https://example.com --output json --save audit_data.json
```

---

## Benchmark Case Studies

See [BENCHMARKS.md](BENCHMARKS.md) for empirical link architecture studies across 12 production web properties, demonstrating that enterprise single-page applications leak an average of 19.4% of internal link equity through unlinked client-side routes and redirect hops.

---

## Cloud Architecture

LinkBleed is maintained as part of the WebAudits.pro performance ecosystem. For instant browser-based internal link audits without local Python dependencies, use the cloud engine at [webaudits.pro/tools/link-bleed](https://webaudits.pro/tools/link-bleed).

---

## License

MIT License. Copyright (c) 2026 xcalibur73.
