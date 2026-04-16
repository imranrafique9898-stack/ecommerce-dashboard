"""
search_engine.py — Semantic + keyword search over scraped eBay products.
Builds an in-memory index using sentence-transformers for semantic search.
"""

import json, re, os
import numpy as np
from sentence_transformers import SentenceTransformer

DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'ebay_items_full.json')
MODEL_NAME = "all-MiniLM-L6-v2"

_products   = []
_embeddings = None
_model      = None


def _load():
    global _products, _embeddings, _model
    if _products:
        return

    print("Loading products...")
    with open(DATA_FILE, encoding="utf-8") as f:
        raw = json.load(f)

    # Only keep items with enough data
    _products = [p for p in raw if p.get("product_name") and p.get("price")]
    print(f"Loaded {len(_products)} products")

    print("Loading embedding model...")
    _model = SentenceTransformer(MODEL_NAME)

    # Build text for each product to embed
    texts = []
    for p in _products:
        specs = " ".join(f"{k} {v}" for k, v in p.get("item_specifics", {}).items())
        text  = f"{p.get('product_name','')} {p.get('category','')} {p.get('condition','')} {specs}"
        texts.append(text.lower())

    print("Building search index...")
    _embeddings = _model.encode(texts, batch_size=64, show_progress_bar=True, convert_to_numpy=True)
    print("Index ready.")


def _parse_filters(query):
    """Extract price range, condition, category hints from query."""
    filters = {}

    # Price: under $50, below $100, max $200, $20-$80
    m = re.search(r'under\s*\$?([\d,]+)', query, re.IGNORECASE)
    if m:
        filters["max_price"] = float(m.group(1).replace(",", ""))

    m = re.search(r'over\s*\$?([\d,]+)', query, re.IGNORECASE)
    if m:
        filters["min_price"] = float(m.group(1).replace(",", ""))

    m = re.search(r'\$?([\d,]+)\s*[-–to]+\s*\$?([\d,]+)', query, re.IGNORECASE)
    if m:
        filters["min_price"] = float(m.group(1).replace(",", ""))
        filters["max_price"] = float(m.group(2).replace(",", ""))

    # Condition
    if re.search(r'\bnew\b', query, re.IGNORECASE):
        filters["condition"] = "new"
    elif re.search(r'\bused\b|\bpre.?owned\b|\bsecond.?hand\b', query, re.IGNORECASE):
        filters["condition"] = "used"

    return filters


def _price_value(price_str):
    """Convert price string like '$24.99' to float."""
    m = re.search(r'[\d,]+\.?\d*', str(price_str).replace(",", ""))
    return float(m.group().replace(",", "")) if m else None


def search(query, top_k=12):
    """Search products by natural language query. Returns list of product dicts."""
    _load()

    filters = _parse_filters(query)

    # Semantic search
    q_vec = _model.encode([query.lower()], convert_to_numpy=True)
    scores = np.dot(_embeddings, q_vec.T).flatten()
    top_indices = np.argsort(scores)[::-1]

    results = []
    for idx in top_indices:
        if len(results) >= top_k:
            break
        p = _products[idx]

        # Apply price filter
        price = _price_value(p.get("price", ""))
        if price is not None:
            if "max_price" in filters and price > filters["max_price"]:
                continue
            if "min_price" in filters and price < filters["min_price"]:
                continue

        # Apply condition filter
        if "condition" in filters:
            cond = p.get("condition", "").lower()
            if filters["condition"] == "new" and "new" not in cond:
                continue
            if filters["condition"] == "used" and "new" in cond:
                continue

        results.append({
            "item_id"                : p.get("item_id", ""),
            "product_name"           : p.get("product_name", ""),
            "category"               : p.get("category", ""),
            "price"                  : p.get("price", "N/A"),
            "original_price"         : p.get("original_price", ""),
            "condition"              : p.get("condition", ""),
            "seller_name"            : p.get("seller_name", ""),
            "seller_feedback"        : p.get("seller_feedback", ""),
            "seller_feedback_percent": p.get("seller_feedback_percent", ""),
            "seller_location"        : p.get("seller_location", ""),
            "image_url"              : p.get("image_urls", [""])[0],
            "product_url"            : p.get("product_url", ""),
            "score"                  : float(scores[idx]),
        })

    return results


def summarize_results(query, results):
    """Generate a short natural language summary of search results."""
    if not results:
        return f"Sorry, I couldn't find any products matching '{query}'."
    prices = [_price_value(r["price"]) for r in results if _price_value(r["price"])]
    min_p  = min(prices) if prices else 0
    max_p  = max(prices) if prices else 0
    cats   = list({r["category"] for r in results})
    return (f"I found {len(results)} products for '{query}'. "
            f"Prices range from ${min_p:.2f} to ${max_p:.2f}. "
            f"Categories: {', '.join(cats[:3])}.")
