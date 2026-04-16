"""
search_engine.py — Hybrid retrieval (BM25 + Semantic) for eBay product search.

Strategy:
  - ONE chunk per product: structured text combining all key fields
  - Embedding model: BAAI/bge-small-en-v1.5 (best for retrieval tasks)
  - BM25 for exact keyword matches (brand names, sizes, specific terms)
  - Semantic search for natural language queries
  - Hybrid score = 0.4 * BM25 + 0.6 * Semantic
  - Hard filters: price range, condition, category (applied post-retrieval)
  - Embeddings saved to disk — built once, reused on every restart
"""

import json, os, re, pickle
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

# ── PATHS ─────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_FILE   = os.path.join(BASE_DIR, '..', 'ebay_items_full.json')
INDEX_FILE  = os.path.join(BASE_DIR, 'search_index.pkl')

# ── MODEL ─────────────────────────────────────────────────────────────────────
# BAAI/bge-small-en-v1.5:
#   - Specifically trained for retrieval/search tasks
#   - Outperforms all-MiniLM on product search benchmarks
#   - Fast: 33M params, 384-dim embeddings
#   - Requires prepending "Represent this sentence for searching relevant passages: "
#     to QUERIES only (not documents)
EMBED_MODEL   = "BAAI/bge-small-en-v1.5"
QUERY_PREFIX  = "Represent this sentence for searching relevant passages: "

# Hybrid weights
BM25_WEIGHT   = 0.35
SEM_WEIGHT    = 0.65

# ── STATE ─────────────────────────────────────────────────────────────────────
_products   = []
_chunks     = []       # one text chunk per product
_embeddings = None     # numpy array (N, 384)
_bm25       = None
_model      = None
_ready      = False


# ── CHUNK BUILDER ─────────────────────────────────────────────────────────────

def _build_chunk(p):
    """
    Build ONE structured text chunk per product.
    Prioritises the most searchable fields:
    name > category > condition > key specifics > seller info
    """
    parts = []

    name = p.get("product_name", "").strip()
    if name:
        parts.append(name)

    cat = p.get("category", "").strip()
    if cat:
        parts.append(cat)

    cond = p.get("condition", "").strip()
    if cond:
        parts.append(cond)

    # Key item specifics — most valuable for search
    priority_keys = [
        "Brand", "Type", "Style", "Color", "Colour", "Size", "Material",
        "Department", "Gender", "Age Group", "Pattern", "Occasion",
        "Features", "Shoe Width", "Heel Height", "Closure", "Fabric Type",
    ]
    specs = p.get("item_specifics", {})
    for key in priority_keys:
        val = specs.get(key, "")
        if val:
            parts.append(f"{key}: {val}")

    # Any remaining specifics not in priority list
    for k, v in specs.items():
        if k not in priority_keys and v and len(str(v)) < 60:
            parts.append(f"{k}: {v}")

    # Seller description — clean and truncate to most useful part
    desc = p.get("seller_description", "").strip()
    if desc:
        # Remove repetitive spec lines already captured above
        desc_lines = [l.strip() for l in desc.splitlines() if len(l.strip()) > 20]
        desc_clean = " ".join(desc_lines[:8])  # first 8 meaningful lines
        if desc_clean:
            parts.append(desc_clean[:400])  # cap at 400 chars

    # Seller info
    seller = p.get("seller_name", "").strip()
    if seller:
        parts.append(f"Seller: {seller}")

    loc = p.get("seller_location", "").strip()
    if loc:
        parts.append(f"Location: {loc}")

    return " | ".join(parts).lower()


# ── INDEX BUILD / LOAD ────────────────────────────────────────────────────────

def _build_index(products):
    global _chunks, _embeddings, _bm25, _model

    print(f"  Building chunks for {len(products)} products...")
    _chunks = [_build_chunk(p) for p in products]

    # BM25
    print("  Building BM25 index...")
    tokenized = [c.split() for c in _chunks]
    _bm25 = BM25Okapi(tokenized)

    # Semantic embeddings
    print(f"  Loading embedding model: {EMBED_MODEL}")
    _model = SentenceTransformer(EMBED_MODEL)

    print("  Computing embeddings (this runs once, then cached)...")
    _embeddings = _model.encode(
        _chunks,
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True,   # cosine similarity via dot product
        convert_to_numpy=True,
    )

    # Save index to disk
    print(f"  Saving index to {INDEX_FILE}...")
    with open(INDEX_FILE, "wb") as f:
        pickle.dump({
            "chunks"    : _chunks,
            "embeddings": _embeddings,
            "item_ids"  : [p.get("item_id") for p in products],
        }, f)
    print("  Index saved.")


def _load():
    global _products, _chunks, _embeddings, _bm25, _model, _ready

    if _ready:
        return

    print("\n[Search Engine] Initialising...")

    # Load products
    with open(DATA_FILE, encoding="utf-8") as f:
        raw = json.load(f)
    _products = [p for p in raw if p.get("product_name") and p.get("price")]
    print(f"  Loaded {len(_products)} products")

    # Check if cached index exists and matches current data
    if os.path.exists(INDEX_FILE):
        print("  Loading cached index...")
        with open(INDEX_FILE, "rb") as f:
            cached = pickle.load(f)

        if len(cached["chunks"]) == len(_products):
            _chunks     = cached["chunks"]
            _embeddings = cached["embeddings"]

            # Rebuild BM25 from chunks (fast)
            print("  Rebuilding BM25 from cache...")
            _bm25 = BM25Okapi([c.split() for c in _chunks])

            # Load model for query encoding
            print(f"  Loading model: {EMBED_MODEL}")
            _model = SentenceTransformer(EMBED_MODEL)
            print("  Ready (from cache).")
            _ready = True
            return
        else:
            print(f"  Cache mismatch ({len(cached['chunks'])} vs {len(_products)}) — rebuilding...")

    _build_index(_products)
    # Rebuild BM25 after build
    _bm25 = BM25Okapi([c.split() for c in _chunks])
    _ready = True
    print("[Search Engine] Ready.\n")


# ── FILTERS ───────────────────────────────────────────────────────────────────

def _parse_filters(query):
    filters = {}

    # Price: under $50, below $100, max $200, $20-$80, between $20 and $80
    m = re.search(r'(?:under|below|max|less than|up to)\s*\$?([\d,]+)', query, re.IGNORECASE)
    if m:
        filters["max_price"] = float(m.group(1).replace(",", ""))

    m = re.search(r'(?:over|above|min|more than|at least)\s*\$?([\d,]+)', query, re.IGNORECASE)
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


def _price_val(price_str):
    m = re.search(r'[\d]+\.?\d*', str(price_str).replace(",", ""))
    return float(m.group()) if m else None


def _passes_filters(product, filters):
    price = _price_val(product.get("price", ""))
    if price is not None:
        if "max_price" in filters and price > filters["max_price"]:
            return False
        if "min_price" in filters and price < filters["min_price"]:
            return False
    if "condition" in filters:
        cond = product.get("condition", "").lower()
        if filters["condition"] == "new" and "new" not in cond:
            return False
        if filters["condition"] == "used" and "new" in cond:
            return False
    return True


# ── HYBRID SEARCH ─────────────────────────────────────────────────────────────

def search(query, top_k=12, category_filter=None):
    """
    Hybrid BM25 + Semantic search.
    Returns list of product dicts ranked by relevance.
    """
    _load()

    filters = _parse_filters(query)

    # ── BM25 scores ──────────────────────────────────────────────────────────
    tokens    = query.lower().split()
    bm25_raw  = np.array(_bm25.get_scores(tokens))
    bm25_max  = bm25_raw.max()
    bm25_norm = bm25_raw / bm25_max if bm25_max > 0 else bm25_raw

    # ── Semantic scores ───────────────────────────────────────────────────────
    # BGE requires query prefix for retrieval
    q_text  = QUERY_PREFIX + query
    q_vec   = _model.encode([q_text], normalize_embeddings=True, convert_to_numpy=True)
    sem_scores = np.dot(_embeddings, q_vec.T).flatten()  # cosine via dot (normalized)

    # ── Hybrid score ──────────────────────────────────────────────────────────
    hybrid = BM25_WEIGHT * bm25_norm + SEM_WEIGHT * sem_scores

    # ── Rank and filter ───────────────────────────────────────────────────────
    ranked_indices = np.argsort(hybrid)[::-1]

    results = []
    for idx in ranked_indices:
        if len(results) >= top_k:
            break

        p = _products[idx]

        # Category filter
        if category_filter and p.get("category") != category_filter:
            continue

        # Price / condition filters
        if not _passes_filters(p, filters):
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
            "image_url"              : (p.get("image_urls") or [""])[0],
            "product_url"            : p.get("product_url", ""),
            "score"                  : float(hybrid[idx]),
        })

    return results


# ── SUMMARY ───────────────────────────────────────────────────────────────────

def summarize(query, results):
    if not results:
        return f"Sorry, I couldn't find any products matching '{query}'. Try different keywords."
    prices = [_price_val(r["price"]) for r in results if _price_val(r["price"])]
    min_p  = min(prices) if prices else 0
    max_p  = max(prices) if prices else 0
    cats   = list({r["category"] for r in results})
    return (
        f"Found {len(results)} products for '{query}'. "
        f"Prices from ${min_p:.2f} to ${max_p:.2f}. "
        f"Categories: {', '.join(cats[:3])}."
    )


# ── CLI TEST ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Building/loading index...")
    _load()
    while True:
        q = input("\nSearch: ").strip()
        if not q:
            break
        results = search(q, top_k=5)
        print(f"\n{summarize(q, results)}")
        for r in results:
            print(f"  [{r['score']:.3f}] {r['product_name'][:60]} — {r['price']} | {r['condition']}")
