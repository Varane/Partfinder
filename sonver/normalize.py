from datetime import datetime
from typing import Any, Dict


def normalize_item(raw_item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize raw scraped data into a consistent structure."""

    return {
        "platform": raw_item.get("platform", "unknown"),
        "article": str(raw_item.get("article", "")).strip(),
        "brand": (raw_item.get("brand") or "").strip(),
        "model": (raw_item.get("model") or "").strip(),
        "generation": (raw_item.get("generation") or "").strip(),
        "category": (raw_item.get("category") or "").strip(),
        "description": (raw_item.get("description") or "").strip(),
        "price": float(raw_item.get("price") or 0.0),
        "currency": raw_item.get("currency", "EUR"),
        "location": (raw_item.get("location") or "").strip(),
        "url": raw_item.get("url", ""),
        "image_url": raw_item.get("image_url", ""),
        "last_seen": datetime.utcnow().isoformat(),
    }
