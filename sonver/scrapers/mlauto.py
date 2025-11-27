from typing import Any, Dict, List

from .base import BaseScraper


class MLAutoScraper(BaseScraper):
    base_url = "https://www.mlauto.example"
    platform = "MLAUTO"

    def fetch_all(self) -> List[Dict[str, Any]]:
        # Placeholder for future implementation.
        return []
