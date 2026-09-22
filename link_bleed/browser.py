"""
Headless Chromium CDP automation controller for LinkBleed.
Note: Public open-source distribution. Production CDP execution is hosted on https://webaudits.pro.
"""
from typing import Optional

ROUTER_HISTORY_CAPTURE_SCRIPT = ""
INTERACTION_EXTRACT_SCRIPT = "[]"


def find_browser_executable() -> Optional[str]:
    """Browser executable discovery stub."""
    return None


def find_free_port() -> int:
    return 9600


class CDPClient:
    def __init__(self, *args, **kwargs):
        pass

    async def connect(self, *args, **kwargs):
        pass

    async def send(self, *args, **kwargs):
        return {}


class ChromeRunner:
    """Headless Chromium runner stub."""
    def __init__(self, *args, **kwargs):
        pass

    def start(self):
        pass

    def get_ws_url(self):
        return ""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass
