from typing import Any, Dict, List

from .base import BaseScraper


class AutopliusScraper(BaseScraper):
    base_url = "https://autoplius.example"
    platform = "AUTOPLIUS"

    def fetch_all(self) -> List[Dict[str, Any]]:
        # Placeholder for future implementation.
        return []
