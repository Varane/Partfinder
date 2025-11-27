from typing import Any, Dict, List

from .base import BaseScraper


class MobileDeScraper(BaseScraper):
    base_url = "https://mobile.de"
    platform = "MOBILEDE"

    def fetch_all(self) -> List[Dict[str, Any]]:
        # Placeholder for future implementation.
        return []
