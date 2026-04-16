"""
chatbot.py — Shopping chatbot using Qwen2-0.5B-Instruct (local, CPU).
Understands user intent, queries the search engine, replies conversationally.
"""

import re
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

# ── MODEL ─────────────────────────────────────────────────────────────────────
MODEL_ID = "Qwen/Qwen2-0.5B-Instruct"

_pipe      = None
_tokenizer = None

SYSTEM_PROMPT = """You are ShopBot, a friendly AI shopping assistant for an eBay product store.
Your job is to help users find products based on their needs and budget.

Rules:
- Keep replies SHORT (2-3 sentences max)
- If the user asks for products, extract: what they want, budget/price range, condition (new/used)
- Reply naturally and warmly
- Do NOT make up products — the system will show real products separately
- If no products found, suggest trying different keywords
- Always end with a helpful follow-up question or suggestion"""


def _load():
    global _pipe, _tokenizer
    if _pipe:
        return
    print("[Chatbot] Loading Qwen2-0.5B-Instruct...")
    _tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float32,   # CPU — use float32
        device_map="cpu",
        low_cpu_mem_usage=True,
    )
    _pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=_tokenizer,
        max_new_tokens=120,
        do_sample=False,             # deterministic — faster on CPU
        temperature=1.0,
        repetition_penalty=1.1,
    )
    print("[Chatbot] Ready.")


def extract_search_query(user_message: str, history: list) -> str:
    """
    Use the LLM to extract a clean search query from the user message.
    Returns a short keyword string suitable for the search engine.
    """
    _load()

    extract_prompt = f"""Extract a short eBay product search query from this message.
Return ONLY the search keywords, nothing else. No explanation.
Examples:
  "I want a red jacket under $50" -> red jacket
  "show me nike sneakers size 10 new" -> nike sneakers size 10 new
  "something warm for winter" -> warm winter jacket coat
  "vintage dress good condition" -> vintage dress

Message: {user_message}
Search query:"""

    messages = [{"role": "user", "content": extract_prompt}]
    out = _pipe(messages, max_new_tokens=30, do_sample=False)
    raw = out[0]["generated_text"][-1]["content"].strip()
    # Clean up — take first line only
    query = raw.splitlines()[0].strip().strip('"').strip("'")
    return query if query else user_message


def chat(user_message: str, history: list, products_found: int) -> str:
    """
    Generate a conversational reply given the user message and search results count.
    history: list of {"role": "user"/"assistant", "content": "..."}
    """
    _load()

    # Build context about what was found
    if products_found > 0:
        product_context = f"[System: Found {products_found} matching products shown below]"
    else:
        product_context = "[System: No products found for this query]"

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add last 4 turns of history for context
    for turn in history[-4:]:
        messages.append(turn)

    messages.append({"role": "user", "content": f"{user_message}\n{product_context}"})

    out = _pipe(messages, max_new_tokens=120, do_sample=False)
    reply = out[0]["generated_text"][-1]["content"].strip()

    # Safety: trim if too long
    sentences = re.split(r'(?<=[.!?])\s+', reply)
    return " ".join(sentences[:3])


def is_product_query(user_message: str) -> bool:
    """Quick heuristic check — does this message want products?"""
    keywords = [
        "show", "find", "search", "looking for", "want", "need", "buy",
        "get me", "recommend", "suggest", "under", "budget", "cheap",
        "affordable", "best", "top", "jacket", "dress", "shoes", "shirt",
        "pants", "bag", "watch", "jewelry", "sneakers", "boots", "coat",
    ]
    msg = user_message.lower()
    return any(k in msg for k in keywords)
