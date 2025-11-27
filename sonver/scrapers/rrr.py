import json
import logging
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from .base import BaseScraper


logger = logging.getLogger(__name__)


class RRRScraper(BaseScraper):
    base_url = "https://rrr.lt"
    platform = "RRR"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
                "Accept": "application/json, text/html;q=0.9",
            }
        )

    # -----------------------
    # JSON helpers
    # -----------------------
    def _fetch_json(self, path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        response = self.get(f"{self.base_url}{path}", params=params)
        if not response:
            return None
        try:
            return response.json()
        except json.JSONDecodeError:
            return None

    # -----------------------
    # Discovery helpers
    # -----------------------
    def fetch_brands(self) -> List[Dict[str, str]]:
        data = self._fetch_json("/api/brands")
        if isinstance(data, list) and data:
            return [
                {"id": str(item.get("id")), "name": item.get("name", "")}
                for item in data
                if item.get("id") and item.get("name")
            ]

        # fallback to HTML form parsing
        url = f"{self.base_url}/en"
        response = self.get(url)
        if not response:
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        brands: List[Dict[str, str]] = []
        for option in soup.select("select[id*=brand] option, select[name*=brand] option"):
            value = option.get("value")
            text = option.get_text(strip=True)
            if value and text:
                brands.append({"id": value, "name": text})
        return brands

    def fetch_models(self, brand: Dict[str, str]) -> List[Dict[str, str]]:
        data = self._fetch_json("/api/models", params={"brand": brand["id"]})
        if isinstance(data, list) and data:
            return [
                {"id": str(item.get("id")), "name": item.get("name", "")}
                for item in data
                if item.get("id") and item.get("name")
            ]

        url = f"{self.base_url}/en/auto-parts/{brand['id']}"
        response = self.get(url)
        if not response:
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        models: List[Dict[str, str]] = []
        for option in soup.select("select[id*=model] option, select[name*=model] option"):
            value = option.get("value")
            text = option.get_text(strip=True)
            if value and text:
                models.append({"id": value, "name": text})
        return models

    def fetch_generations(self, brand: Dict[str, str], model: Dict[str, str]) -> List[Dict[str, str]]:
        data = self._fetch_json(
            "/api/generations", params={"brand": brand["id"], "model": model["id"]}
        )
        if isinstance(data, list) and data:
            return [
                {"id": str(item.get("id")), "name": item.get("name", "")}
                for item in data
                if item.get("id") and item.get("name")
            ]
        return []

    def fetch_categories(self, brand: Dict[str, str], model: Dict[str, str], generation: Dict[str, str]) -> List[Dict[str, str]]:
        data = self._fetch_json(
            "/api/categories",
            params={"brand": brand["id"], "model": model["id"], "generation": generation["id"]},
        )
        if isinstance(data, list) and data:
            return [
                {"id": str(item.get("id")), "name": item.get("name", "")}
                for item in data
                if item.get("id") and item.get("name")
            ]
        return []

    # -----------------------
    # Parts parsing
    # -----------------------
    def parse_parts_page(
        self, html: str, brand: str, model: str, generation: str, category: str
    ) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        parts: List[Dict[str, Any]] = []
        for item in soup.select("div.part, div.search-item, li.search-item"):
            article = item.get("data-article") or item.get("data-code") or ""
            title_el = item.select_one(".title, .search-item__title, h3")
            description = title_el.get_text(strip=True) if title_el else ""
            price_el = item.select_one(".price, .search-item__price, .item-price")
            price_text = price_el.get_text(strip=True) if price_el else ""
            price, currency = self._parse_price(price_text)
            url_el = item.select_one("a")
            url = self.base_url + url_el.get("href", "") if url_el else ""
            image_el = item.select_one("img")
            image_url = image_el.get("src") if image_el else ""
            location_el = item.select_one(".location, .search-item__location")
            location = location_el.get_text(strip=True) if location_el else ""

            parts.append(
                {
                    "platform": self.platform,
                    "article": article,
                    "brand": brand,
                    "model": model,
                    "generation": generation,
                    "category": category,
                    "description": description,
                    "price": price,
                    "currency": currency,
                    "location": location,
                    "url": url,
                    "image_url": image_url,
                }
            )
        return parts

    @staticmethod
    def _parse_price(text: str) -> (float, str):
        if not text:
            return 0.0, "EUR"
        parts = text.replace("\xa0", " ").split()
        currency = "EUR"
        amount = 0.0
        for token in parts:
            try:
                amount = float(token.replace(",", "."))
            except ValueError:
                if token.isalpha():
                    currency = token
        return amount, currency

    def parse_json_item(
        self, item: Dict[str, Any], brand: str, model: str, generation: str, category: str
    ) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "article": item.get("article") or item.get("code") or item.get("partNumber") or "",
            "brand": brand,
            "model": model,
            "generation": generation,
            "category": category,
            "description": item.get("title") or item.get("description") or "",
            "price": float(item.get("price") or 0),
            "currency": item.get("currency") or item.get("currencyCode") or "EUR",
            "location": item.get("location") or item.get("city") or "",
            "url": item.get("url") or item.get("link") or "",
            "image_url": item.get("image") or item.get("imageUrl") or "",
        }

    def fetch_parts(
        self, brand: Dict[str, str], model: Dict[str, str], generation: Dict[str, str], category: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        page = 1
        results: List[Dict[str, Any]] = []
        while True:
            params = {
                "page": page,
                "brand": brand["id"],
                "model": model["id"],
                "generation": generation["id"],
                "category": category["id"],
                "size": 50,
            }
            data = self._fetch_json("/api/search", params=params)
            if isinstance(data, dict) and data.get("items"):
                items = data.get("items") or []
                for itm in items:
                    results.append(
                        self.parse_json_item(itm, brand["name"], model["name"], generation["name"], category["name"])
                    )
                if len(items) < params["size"]:
                    break
                page += 1
                continue

            response = self.get(f"{self.base_url}/en/auto-parts/search", params=params)
            if not response:
                break
            page_items = self.parse_parts_page(
                response.text, brand["name"], model["name"], generation["name"], category["name"]
            )
            if not page_items:
                break
            results.extend(page_items)
            page += 1
        return results

    def fetch_all(self) -> List[Dict[str, Any]]:
        logger.info("Fetching data from RRR.lt")
        all_items: List[Dict[str, Any]] = []

        brands = self.fetch_brands()
        for brand in brands:
            models = self.fetch_models(brand)
            for model in models:
                generations = self.fetch_generations(brand, model) or [{"id": "", "name": ""}]
                for generation in generations:
                    categories = self.fetch_categories(brand, model, generation) or [{"id": "", "name": "All"}]
                    for category in categories:
                        parts = self.fetch_parts(brand, model, generation, category)
                        all_items.extend(parts)
        return all_items
