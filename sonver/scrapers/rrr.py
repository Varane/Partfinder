import logging
from typing import Any, Dict, List

from bs4 import BeautifulSoup

from .base import BaseScraper


logger = logging.getLogger(__name__)


class RRRScraper(BaseScraper):
    base_url = "https://rrr.lt"
    platform = "RRR"

    def fetch_brands(self) -> List[Dict[str, str]]:
        url = f"{self.base_url}/en"
        response = self.get(url)
        if not response:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        brands = []
        for option in soup.select("select[id*=brand] option, select[name*=brand] option"):
            value = option.get("value")
            text = option.get_text(strip=True)
            if value and text:
                brands.append({"id": value, "name": text})
        return brands

    def fetch_models(self, brand: Dict[str, str]) -> List[Dict[str, str]]:
        url = f"{self.base_url}/en/auto-parts/{brand['id']}"
        response = self.get(url)
        if not response:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        models = []
        for option in soup.select("select[id*=model] option, select[name*=model] option"):
            value = option.get("value")
            text = option.get_text(strip=True)
            if value and text:
                models.append({"id": value, "name": text})
        return models

    def fetch_categories(self) -> List[Dict[str, str]]:
        url = f"{self.base_url}/en/auto-parts"
        response = self.get(url)
        if not response:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        categories = []
        for option in soup.select("select[id*=category] option, select[name*=category] option"):
            value = option.get("value")
            text = option.get_text(strip=True)
            if value and text:
                categories.append({"id": value, "name": text})
        return categories

    def parse_parts_page(self, html: str, brand: str, model: str, category: str) -> List[Dict[str, Any]]:
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

    def fetch_parts(self, brand: Dict[str, str], model: Dict[str, str], category: Dict[str, str]) -> List[Dict[str, Any]]:
        page = 1
        results: List[Dict[str, Any]] = []
        while True:
            params = {
                "page": page,
                "brand": brand["id"],
                "model": model["id"],
                "category": category["id"],
            }
            response = self.get(f"{self.base_url}/en/auto-parts/search", params=params)
            if not response:
                break

            page_items = self.parse_parts_page(response.text, brand["name"], model["name"], category["name"])
            if not page_items:
                break

            results.extend(page_items)
            page += 1
        return results

    def fetch_all(self) -> List[Dict[str, Any]]:
        logger.info("Fetching data from RRR.lt")
        all_items: List[Dict[str, Any]] = []

        brands = self.fetch_brands()
        categories = self.fetch_categories()
        for brand in brands:
            models = self.fetch_models(brand)
            for model in models:
                for category in categories:
                    parts = self.fetch_parts(brand, model, category)
                    all_items.extend(parts)
        return all_items
