"""
Hybrid static and dynamic link discovery engine with sitemap parsing for LinkBleed.
"""

import asyncio
import re
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Set, Optional, Tuple
import requests
from bs4 import BeautifulSoup

from link_bleed.browser import (
    find_browser_executable,
    find_free_port,
    ChromeRunner,
    CDPClient,
    INTERACTION_EXTRACT_SCRIPT,
    ROUTER_HISTORY_CAPTURE_SCRIPT,
)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 (LinkBleed/1.0.0)"
)


def get_base_domain(url: str) -> str:
    """Extract registered domain or hostname from URL."""
    try:
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc.lower().split(":")[0]
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return ""


def normalize_url(url: str, base_url: str = "") -> Optional[str]:
    """
    Normalize URL:
    - Resolves relative URLs against base_url
    - Strips fragment identifiers (#...)
    - Ignores mailto:, tel:, javascript:, data:
    - Normalizes scheme to https if empty
    - Normalizes trailing slashes for directory paths
    """
    if not url or not isinstance(url, str):
        return None

    cleaned = url.strip()
    lower = cleaned.lower()
    if (
        lower.startswith("javascript:")
        or lower.startswith("mailto:")
        or lower.startswith("tel:")
        or lower.startswith("data:")
        or lower.startswith("#")
    ):
        return None

    try:
        if base_url:
            resolved = urllib.parse.urljoin(base_url, cleaned)
        else:
            resolved = cleaned

        parsed = urllib.parse.urlparse(resolved)
        if not parsed.scheme or parsed.scheme not in ("http", "https"):
            return None

        # Strip fragment
        netloc = parsed.netloc.lower()
        path = parsed.path
        if not path:
            path = "/"

        # Remove default ports
        if netloc.endswith(":80") and parsed.scheme == "http":
            netloc = netloc[:-3]
        elif netloc.endswith(":443") and parsed.scheme == "https":
            netloc = netloc[:-4]

        # Reconstruct canonical URL
        query = f"?{parsed.query}" if parsed.query else ""
        canonical = f"{parsed.scheme}://{netloc}{path}{query}"
        return canonical
    except Exception:
        return None


def is_internal_url(target_url: str, base_domain: str) -> bool:
    """Determine if a URL belongs to the target domain."""
    target_domain = get_base_domain(target_url)
    if not target_domain or not base_domain:
        return False
    return target_domain == base_domain or target_domain.endswith("." + base_domain)


def extract_static_links(html: str, page_url: str) -> List[Dict[str, Any]]:
    """Extract links from static HTML response using BeautifulSoup."""
    soup = BeautifulSoup(html, "html.parser")
    base_tag = soup.find("base", href=True)
    effective_base = base_tag["href"] if base_tag else page_url

    links = []
    seen = set()

    for a in soup.find_all("a", href=True):
        raw_href = a["href"]
        normalized = normalize_url(raw_href, effective_base)
        if not normalized:
            continue

        anchor_text = a.get_text(separator=" ", strip=True)
        # If no text, check image alt inside anchor, aria-label, or title
        if not anchor_text:
            img = a.find("img", alt=True)
            if img:
                anchor_text = f"[Image: {img['alt'].strip()}]"
            elif a.get("aria-label"):
                anchor_text = a["aria-label"].strip()
            elif a.find(attrs={"aria-label": True}):
                anchor_text = a.find(attrs={"aria-label": True})["aria-label"].strip()
            elif a.get("title"):
                anchor_text = a["title"].strip()

        rel = a.get("rel", [])
        if isinstance(rel, list):
            rel_str = " ".join(rel).lower()
        else:
            rel_str = str(rel).lower()

        key = (normalized, anchor_text)
        if key not in seen:
            seen.add(key)
            links.append({
                "raw_href": raw_href,
                "target_url": normalized,
                "anchor_text": anchor_text,
                "rel": rel_str,
                "is_nofollow": "nofollow" in rel_str,
                "is_sponsored": "sponsored" in rel_str,
                "is_ugc": "ugc" in rel_str,
                "is_static": True,
                "is_dynamic": False,
            })

    return links


def parse_sitemap_urls(sitemap_url: str, timeout: int = 15) -> List[str]:
    """Parse XML sitemap (or sitemap index) to collect all listed URLs."""
    urls = []
    headers = {"User-Agent": DEFAULT_USER_AGENT}
    try:
        resp = requests.get(sitemap_url, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            return []

        root = ET.fromstring(resp.content)
        # Check namespace
        ns = ""
        if root.tag.startswith("{"):
            ns = root.tag.split("}")[0] + "}"

        # If sitemapindex, parse child sitemaps (first 3)
        if root.tag.endswith("sitemapindex"):
            for sitemap in root.findall(f"{ns}sitemap")[:3]:
                loc = sitemap.find(f"{ns}loc")
                if loc is not None and loc.text:
                    urls.extend(parse_sitemap_urls(loc.text.strip(), timeout=timeout))
        elif root.tag.endswith("urlset"):
            for url_tag in root.findall(f"{ns}url"):
                loc = url_tag.find(f"{ns}loc")
                if loc is not None and loc.text:
                    loc_text = loc.text.strip()
                    if not loc_text.lower().endswith((".xml", ".xml.gz")):
                        norm = normalize_url(loc_text)
                        if norm:
                            urls.append(norm)
    except Exception:
        pass
    return list(dict.fromkeys(urls))


async def crawl_dynamic_page_cdp(
    url: str,
    browser_path: str,
    simulate_interaction: bool = True
) -> Dict[str, Any]:
    """
    Load page via headless Chrome, emulate user interactions, and extract dynamic links.
    """
    port = find_free_port()
    runner = ChromeRunner(port, browser_path)
    runner.start()

    try:
        ws_url = runner.get_ws_url()
        client = CDPClient(ws_url)
        await client.connect(timeout=8.0)

        # Enable domains
        await client.send("Page.enable")
        await client.send("DOM.enable")
        await client.send("Runtime.enable")

        # Inject history interceptor
        await client.send("Page.addScriptToEvaluateOnNewDocument", {
            "source": ROUTER_HISTORY_CAPTURE_SCRIPT
        })

        # Navigate
        await client.send("Page.navigate", {"url": url})
        await asyncio.sleep(2.5)

        # Capture dynamic SPA routes intercepted so far
        router_res = await client.send("Runtime.evaluate", {
            "expression": "window.__linkBleedRoutes || []",
            "returnByValue": True
        })
        spa_routes = router_res.get("result", {}).get("value", [])

        if simulate_interaction:
            # Scroll down and back to trigger lazy rendering and infinite scroll
            await client.send("Runtime.evaluate", {
                "expression": "window.scrollTo(0, document.body.scrollHeight / 2);"
            })
            await asyncio.sleep(0.6)
            await client.send("Runtime.evaluate", {
                "expression": "window.scrollTo(0, document.body.scrollHeight);"
            })
            await asyncio.sleep(0.8)

        # Extract all rendered links and click triggers
        links_res = await client.send("Runtime.evaluate", {
            "expression": INTERACTION_EXTRACT_SCRIPT,
            "returnByValue": True
        })
        raw_rendered_links = links_res.get("result", {}).get("value", [])

        rendered_links = []
        seen = set()
        for item in raw_rendered_links:
            raw_href = item.get("raw_href", "")
            resolved = normalize_url(item.get("resolved_href", ""), url)
            if not resolved:
                continue

            anchor = item.get("anchor_text", "")
            rel = (item.get("rel") or "").lower()
            key = (resolved, anchor)
            if key not in seen:
                seen.add(key)
                rendered_links.append({
                    "raw_href": raw_href,
                    "target_url": resolved,
                    "anchor_text": anchor,
                    "rel": rel,
                    "is_nofollow": "nofollow" in rel,
                    "is_sponsored": "sponsored" in rel,
                    "is_ugc": "ugc" in rel,
                    "is_visible": item.get("is_visible", True),
                    "in_nav": item.get("in_nav", False),
                    "is_static": False,
                    "is_dynamic": True,
                })

        await client.close()
        return {
            "rendered_links": rendered_links,
            "spa_routes": spa_routes,
            "success": True,
        }
    except Exception as e:
        return {
            "rendered_links": [],
            "spa_routes": [],
            "success": False,
            "error": str(e),
        }
    finally:
        runner.stop()


def crawl_site_graph(
    start_url: str,
    max_pages: int = 15,
    use_cdp: bool = True,
    simulate_interaction: bool = True,
    sitemap_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Orchestrates site crawl to construct internal link graph, identifying static vs JS-only links
    and orphan pages.
    """
    normalized_start = normalize_url(start_url)
    if not normalized_start:
        raise ValueError(f"Invalid start URL: {start_url}")

    base_domain = get_base_domain(normalized_start)
    browser_path = find_browser_executable() if use_cdp else None
    cdp_available = browser_path is not None and use_cdp

    headers = {"User-Agent": DEFAULT_USER_AGENT}
    session = requests.Session()
    session.headers.update(headers)

    # 1. Discover declared URLs from sitemap
    sitemap_pages: List[str] = []
    if sitemap_url:
        sitemap_pages = parse_sitemap_urls(sitemap_url)
    else:
        # Check standard sitemap locations
        parsed_root = urllib.parse.urlparse(normalized_start)
        auto_sitemap = f"{parsed_root.scheme}://{parsed_root.netloc}/sitemap.xml"
        sitemap_pages = parse_sitemap_urls(auto_sitemap)

    # Queue of URLs to crawl
    queue: List[Tuple[str, int]] = [(normalized_start, 0)]
    visited_urls: Set[str] = set()
    crawled_nodes: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, Any]] = []

    static_targets_seen: Set[str] = set()
    dynamic_targets_seen: Set[str] = set()

    while queue and len(visited_urls) < max_pages:
        current_url, depth = queue.pop(0)
        if current_url in visited_urls:
            continue

        visited_urls.add(current_url)

        # A. Fetch static HTML
        status_code = 200
        html = ""
        try:
            resp = session.get(current_url, timeout=12, allow_redirects=True)
            status_code = resp.status_code
            html = resp.text
            final_url = normalize_url(resp.url) or current_url
        except Exception:
            status_code = 0
            final_url = current_url

        crawled_nodes[current_url] = {
            "url": current_url,
            "status_code": status_code,
            "crawl_depth": depth,
            "is_redirect": final_url != current_url and status_code in (301, 302, 307, 308),
            "redirect_target": final_url if final_url != current_url else None,
        }

        if status_code != 200 or not html:
            continue

        # Extract static links
        static_links = extract_static_links(html, current_url)
        static_url_map = {link["target_url"]: link for link in static_links}
        for link in static_links:
            static_targets_seen.add(link["target_url"])

        # B. If CDP available, capture dynamic / rendered links
        dynamic_links: List[Dict[str, Any]] = []
        if cdp_available and len(visited_urls) <= 5:  # Limit heavy CDP to first 5 core pages
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                cdp_res = loop.run_until_complete(
                    crawl_dynamic_page_cdp(current_url, browser_path, simulate_interaction)
                )
                if cdp_res.get("success"):
                    dynamic_links = cdp_res.get("rendered_links", [])
                    for d_link in dynamic_links:
                        dynamic_targets_seen.add(d_link["target_url"])
            except Exception:
                pass
            finally:
                loop.close()

        # Merge links for current page
        merged_targets: Dict[str, Dict[str, Any]] = {}

        # 1. Add static links
        for s_link in static_links:
            t_url = s_link["target_url"]
            merged_targets[t_url] = {
                "source_url": current_url,
                "target_url": t_url,
                "anchor_text": s_link["anchor_text"],
                "is_static": True,
                "is_dynamic": False,
                "is_internal": is_internal_url(t_url, base_domain),
                "is_nofollow": s_link["is_nofollow"],
                "is_sponsored": s_link["is_sponsored"],
            }

        # 2. Add or augment with dynamic links
        for d_link in dynamic_links:
            t_url = d_link["target_url"]
            if t_url in merged_targets:
                merged_targets[t_url]["is_dynamic"] = True
            else:
                # JS-Only link discovered!
                merged_targets[t_url] = {
                    "source_url": current_url,
                    "target_url": t_url,
                    "anchor_text": d_link["anchor_text"],
                    "is_static": False,
                    "is_dynamic": True,
                    "is_internal": is_internal_url(t_url, base_domain),
                    "is_nofollow": d_link["is_nofollow"],
                    "is_sponsored": d_link["is_sponsored"],
                }

        # Record edges and enqueue internal links
        for edge_data in merged_targets.values():
            edges.append(edge_data)
            target = edge_data["target_url"]
            if (
                edge_data["is_internal"]
                and target not in visited_urls
                and not any(q[0] == target for q in queue)
                and depth + 1 <= 5
            ):
                queue.append((target, depth + 1))

    return {
        "start_url": normalized_start,
        "base_domain": base_domain,
        "mode": "cdp_hybrid" if cdp_available else "http_static",
        "crawled_nodes": crawled_nodes,
        "edges": edges,
        "sitemap_urls": sitemap_pages,
        "static_targets_count": len(static_targets_seen),
        "dynamic_targets_count": len(dynamic_targets_seen),
    }
