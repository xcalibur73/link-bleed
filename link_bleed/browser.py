"""
Browser discovery, Chrome DevTools Protocol (CDP) client, and interaction emulator for LinkBleed.
"""

import asyncio
import json
import os
import shutil
import socket
import subprocess
import time
import urllib.request
from typing import Dict, Any, Optional, List, Set
import websockets

CANDIDATE_BROWSER_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "brave-browser",
]


def find_browser_executable() -> Optional[str]:
    """Find local Chromium-based browser executable."""
    for path in CANDIDATE_BROWSER_PATHS:
        if os.path.isabs(path):
            if os.path.exists(path) and os.path.isfile(path):
                return path
        else:
            resolved = shutil.which(path)
            if resolved:
                return resolved
    return None


def find_free_port(start_port: int = 9750) -> int:
    """Find unbound local port for Chrome remote debugging."""
    for port in range(start_port, start_port + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start_port


class CDPClient:
    """Lightweight Chrome DevTools Protocol WebSocket client."""

    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.ws = None
        self._msg_id = 0

    async def connect(self, timeout: float = 10.0):
        self.ws = await asyncio.wait_for(websockets.connect(self.ws_url), timeout=timeout)

    async def send(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._msg_id += 1
        call_id = self._msg_id
        payload = {
            "id": call_id,
            "method": method,
            "params": params or {}
        }
        await self.ws.send(json.dumps(payload))

        while True:
            raw = await self.ws.recv()
            data = json.loads(raw)
            if data.get("id") == call_id:
                if "error" in data:
                    raise RuntimeError(f"CDP Error ({method}): {data['error']}")
                return data.get("result", {})

    async def close(self):
        if self.ws:
            await self.ws.close()


class ChromeRunner:
    """Headless Chromium browser process manager."""

    def __init__(self, port: int, browser_path: str):
        self.port = port
        self.browser_path = browser_path
        self.proc = None
        self.user_data_dir = None

    def start(self):
        import tempfile
        self.user_data_dir = tempfile.mkdtemp(prefix="linkbleed_chrome_")

        args = [
            self.browser_path,
            f"--remote-debugging-port={self.port}",
            f"--user-data-dir={self.user_data_dir}",
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--mute-audio",
            "--disable-background-networking",
            "--window-size=1440,900",
            "about:blank",
        ]

        self.proc = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        for _ in range(40):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json/version", timeout=0.5) as resp:
                    if resp.status == 200:
                        return
            except Exception:
                time.sleep(0.1)

        raise RuntimeError(f"Headless browser failed to start on port {self.port}")

    def get_ws_url(self) -> str:
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json/list", timeout=2.0) as resp:
            data = json.loads(resp.read().decode())
            for target in data:
                if target.get("type") == "page" and "webSocketDebuggerUrl" in target:
                    return target["webSocketDebuggerUrl"]
        raise RuntimeError("No debuggable page target found")

    def stop(self):
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=2.0)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None

        if self.user_data_dir and os.path.exists(self.user_data_dir):
            try:
                shutil.rmtree(self.user_data_dir, ignore_errors=True)
            except Exception:
                pass


INTERACTION_EXTRACT_SCRIPT = """
(() => {
    // 1. Uncover interactive elements (menus, disclosure toggles, dropdowns)
    const toggles = document.querySelectorAll(
        'button[aria-expanded="false"], [role="button"][aria-expanded="false"], nav summary, header summary, .dropdown-toggle, .menu-toggle'
    );
    toggles.forEach((t) => {
        try { t.click(); } catch(e) {}
    });

    // 2. Extract all anchors from rendered DOM
    const links = [];
    const seen = new Set();
    document.querySelectorAll('a[href]').forEach((a) => {
        const rawHref = a.getAttribute('href') || '';
        const resolvedHref = a.href || '';
        const anchorText = (a.innerText || a.textContent || '').trim();
        const rel = a.getAttribute('rel') || '';
        const target = a.getAttribute('target') || '';

        // Check if visible
        const rect = a.getBoundingClientRect();
        const isVisible = !!(rect.width || rect.height || a.getClientRects().length);

        const key = resolvedHref + '::' + anchorText;
        if (!seen.has(key)) {
            seen.add(key);
            links.push({
                raw_href: rawHref,
                resolved_href: resolvedHref,
                anchor_text: anchorText,
                rel: rel,
                target: target,
                is_visible: isVisible,
                in_nav: !!a.closest('nav, header, footer'),
            });
        }
    });

    return links;
})()
"""

ROUTER_HISTORY_CAPTURE_SCRIPT = """
(() => {
    window.__linkBleedRoutes = [];
    const pushStateOrig = history.pushState;
    const replaceStateOrig = history.replaceState;

    history.pushState = function() {
        if (arguments.length >= 3 && arguments[2]) {
            try {
                const resolved = new URL(arguments[2], window.location.href).href;
                window.__linkBleedRoutes.push({ url: resolved, type: 'pushState' });
            } catch(e) {}
        }
        return pushStateOrig.apply(this, arguments);
    };

    history.replaceState = function() {
        if (arguments.length >= 3 && arguments[2]) {
            try {
                const resolved = new URL(arguments[2], window.location.href).href;
                window.__linkBleedRoutes.push({ url: resolved, type: 'replaceState' });
            } catch(e) {}
        }
        return replaceStateOrig.apply(this, arguments);
    };
})()
"""
