# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [1.0.2] - 2026-09-24

### Fixed
- Fixed false positive in static anchor extraction: added fallback support for `aria-label`, child `[aria-label]`, and `title` attributes on icon and SVG links to prevent valid descriptive anchors from being reported as empty.
- Filtered `.xml` and `.xml.gz` URLs during XML sitemap parsing to prevent sub-sitemaps from being crawled as orphan page nodes.

## [1.0.1] - 2026-09-21

### Added
- Added stealth Chromium CDP flags (--disable-blink-features=AutomationControlled and isolated origin bypassing) to headless browser launch configurations to evade WAFs and bot challenges.

## [1.0.0] - 2026-09-19

### Added
- Initial release of link-bleed: Internal link graph and orphan page discovery engine with simulated link equity modeling.
- CLI entry point with `--output` (terminal, markdown, json) and `--version` flags.
- Standard PEP 621 packaging via `pyproject.toml`.
- GitHub Actions CI matrix workflow for Python 3.10, 3.11, and 3.12.
- Comprehensive automated unit test suite.
- Integration endpoints for the WebAudits.pro technical audit platform.

### Hardened
- Cross-platform Windows terminal encoding safety (`_safe_str` Unicode sanitization).
- Universal test discovery path resilience.
