from statistics import median
from typing import Any, Dict, List, Optional

import sqlite3
from fastapi import FastAPI, Query

from .db import get_connection, init_db

app = FastAPI(title="SONVER Search API")


@app.on_event("startup")
def startup() -> None:
    init_db()


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def compute_sonver_price(article: str) -> Optional[float]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT price FROM parts WHERE article LIKE ? AND price > 0", (f"%{article}%",))
    prices = [r[0] for r in cur.fetchall() if r[0] is not None]
    conn.close()
    if not prices:
        return None
    return round(median(prices) * 1.35, 2)


def fetch_offers_by_article(article: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM parts WHERE article LIKE ? ORDER BY price ASC", (f"%{article}%",))
    rows = cur.fetchall()
    conn.close()
    return [row_to_dict(row) for row in rows]


def build_tree() -> Dict[str, Dict[str, Dict[str, List[str]]]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT brand, model, generation, category FROM parts")
    tree: Dict[str, Dict[str, Dict[str, List[str]]]] = {}
    for brand, model, generation, category in cur.fetchall():
        brand_node = tree.setdefault(brand or "Unknown", {})
        model_node = brand_node.setdefault(model or "Unknown", {})
        gen_key = generation or "Unknown"
        categories = model_node.setdefault(gen_key, [])
        cat_value = category or "Misc"
        if cat_value not in categories:
            categories.append(cat_value)
    conn.close()
    return tree


def search_tree(brand: str, model: str, generation: str, category: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM parts
        WHERE brand = ? AND model = ? AND generation = ? AND category LIKE ?
        ORDER BY price ASC
        """,
        (brand, model, generation, f"%{category}%"),
    )
    rows = cur.fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


@app.get("/search")
def search(article: str = Query(..., description="Part number to search")) -> Dict[str, Any]:
    offers = fetch_offers_by_article(article)
    recommended = compute_sonver_price(article)
    best_offer = None
    if offers:
        best_offer = min(offers, key=lambda x: x.get("price") or float("inf"))

    return {
        "recommended_price": recommended,
        "offers": offers,
        "best_offer": best_offer,
    }


@app.get("/tree")
def tree() -> Dict[str, Dict[str, Dict[str, List[str]]]]:
    return build_tree()


@app.get("/tree/search")
def tree_search(
    brand: str = Query(...),
    model: str = Query(...),
    generation: str = Query(...),
    category: str = Query(""),
) -> Dict[str, Any]:
    offers = search_tree(brand, model, generation, category)
    return {"offers": offers}
