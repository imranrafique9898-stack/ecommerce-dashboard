"""
chatbot.py — RAG-based shopping chatbot using Qwen2-0.5B-Instruct.

RAG Flow:
  1. User sends message
  2. Search engine retrieves top-K relevant products (the "context")
  3. LLM receives: system prompt + conversation history + retrieved products + user query
  4. LLM generates a grounded, conversational response based ONLY on retrieved products
"""

import re
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

MODEL_ID = "Qwen/Qwen2-0.5B-Instruct"

_pipe      = None
_tokenizer = None

SYSTEM_PROMPT = """You are ShopBot, a friendly AI shopping assistant.
You help users find products from our eBay store.

IMPORTANT RULES:
- Answer ONLY based on the products provided in the context
- Be conversational and helpful, 2-4 sentences
- Mention specific product names, prices, and conditions from the context
- If budget is mentioned, highlight products within that budget
- If no products match, say so honestly and suggest alternatives
- Never make up products or prices
- End with a short follow-up question"""


def _load():
    global _pipe, _tokenizer
    if _pipe:
        return
    print("[Chatbot] Loading Qwen2-0.5B-Instruct...")
    _tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        dtype=torch.float32,
        device_map="cpu",
        low_cpu_mem_usage=True,
    )
    _pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=_tokenizer,
        max_new_tokens=200,
        do_sample=False,
        repetition_penalty=1.15,
    )
    print("[Chatbot] Ready.")


def _format_products_for_context(products: list) -> str:
    """Format retrieved products as readable context for the LLM."""
    if not products:
        return "No products found."
    lines = []
    for i, p in enumerate(products[:5], 1):   # top 5 for context window
        name    = p.get("product_name", "")[:70]
        price   = p.get("price", "N/A")
        cond    = p.get("condition", "")
        seller  = p.get("seller_name", "")
        rating  = p.get("seller_feedback_percent", "")
        lines.append(
            f"{i}. {name} | Price: {price} | Condition: {cond} | "
            f"Seller: {seller} {rating}"
        )
    return "\n".join(lines)


def extract_search_query(user_message: str, history: list) -> str:
    """Use LLM to extract a clean search query from the user message."""
    _load()

    # Build context from last user turn if available
    prev = ""
    for turn in reversed(history[-4:]):
        if turn.get("role") == "user":
            prev = turn.get("content", "")
            break

    prompt = f"""Extract a short eBay product search query from this message.
Return ONLY the search keywords, nothing else.
Examples:
  "I want a red jacket under $50" -> red jacket
  "show me nike sneakers size 10 new" -> nike sneakers size 10 new
  "something warm for winter under $100" -> warm winter jacket coat
  "vintage dress good condition" -> vintage dress
  "women clothing" -> womens clothing dress top blouse

Previous context: {prev}
Message: {user_message}
Search query:"""

    messages = [{"role": "user", "content": prompt}]
    out = _pipe(messages, max_new_tokens=20, do_sample=False)
    raw = out[0]["generated_text"][-1]["content"].strip()
    query = raw.splitlines()[0].strip().strip('"').strip("'")
    return query if len(query) > 2 else user_message


def chat(user_message: str, history: list, products: list) -> str:
    """
    RAG: Generate a response grounded in the retrieved products.
    products: list of product dicts from search engine
    """
    _load()

    # Format products as context
    product_context = _format_products_for_context(products)

    # Build RAG prompt
    rag_content = f"""Retrieved products from our store:
{product_context}

User question: {user_message}

Based ONLY on the products above, give a helpful, conversational response."""

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add last 3 turns of history
    for turn in history[-3:]:
        messages.append({"role": turn["role"], "content": turn["content"]})

    messages.append({"role": "user", "content": rag_content})

    out = _pipe(messages, max_new_tokens=200, do_sample=False)
    reply = out[0]["generated_text"][-1]["content"].strip()

    # Clean up — remove any incomplete trailing sentence
    sentences = re.split(r'(?<=[.!?])\s+', reply)
    # Keep complete sentences only
    complete = [s for s in sentences if s.endswith(('.', '!', '?'))]
    if complete:
        return " ".join(complete[:4])
    return reply[:400]


def is_product_query(user_message: str) -> bool:
    """Heuristic: does this message want products?"""
    keywords = [
        "show", "find", "search", "looking", "want", "need", "buy",
        "get", "recommend", "suggest", "under", "budget", "cheap",
        "affordable", "best", "top", "jacket", "dress", "shoes", "shirt",
        "pants", "bag", "watch", "jewelry", "sneakers", "boots", "coat",
        "women", "mens", "kids", "baby", "vintage", "clothing", "clothes",
        "outfit", "wear", "fashion", "style", "size", "color", "brand",
        "new", "used", "sale", "discount", "price", "cost", "how much",
    ]
    msg = user_message.lower()
    return any(k in msg for k in keywords)
