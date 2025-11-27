import time
import logging
from typing import Any, Dict, List, Optional

import requests


logger = logging.getLogger(__name__)


class BaseScraper:
    """Base class for platform scrapers.

    Subclasses should implement :meth:`fetch_all` and use the helper
    :meth:`get` to perform HTTP requests with retry/backoff.
    """

    base_url: str = ""
    platform: str = ""

    def __init__(self, session: Optional[requests.Session] = None, delay: float = 0.5):
        self.session = session or requests.Session()
        self.delay = delay

    def get(self, url: str, params: Optional[Dict[str, Any]] = None, retries: int = 3) -> Optional[requests.Response]:
        """Perform a GET request with basic retry support."""

        for attempt in range(1, retries + 1):
            try:
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                return response
            except requests.RequestException as exc:  # pragma: no cover - network errors
                logger.warning("GET %s failed on attempt %s/%s: %s", url, attempt, retries, exc)
                time.sleep(self.delay * attempt)
        return None

    def fetch_all(self) -> List[Dict[str, Any]]:
        """Return all raw items found on the platform."""

        raise NotImplementedError
