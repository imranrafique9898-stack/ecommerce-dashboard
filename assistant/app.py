"""
app.py — FastAPI web app for the AI Shopping Chatbot.
Run: python assistant/app.py
Open: http://localhost:8000
API Docs: http://localhost:8000/docs
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

from search_engine import search, summarize
from chatbot import chat, extract_search_query, is_product_query
from voice_agent import listen, speak, is_microphone_available

app = FastAPI(title="ShopBot AI", description="AI Shopping Chatbot API", version="1.0.0")

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
# Disable template caching so changes reflect immediately
templates.env.auto_reload = True


# ── SCHEMAS ───────────────────────────────────────────────────────────────────

class Message(BaseModel):
    message: str
    history: Optional[List[dict]] = []

class SearchRequest(BaseModel):
    query: str
    category: Optional[str] = None
    top_k: Optional[int] = 8


# ── ROUTES ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    from fastapi.responses import Response
    content = templates.TemplateResponse("index.html", {
        "request"      : request,
        "mic_available": is_microphone_available(),
    })
    content.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return content


@app.post("/chat")
async def chat_endpoint(body: Message):
    """
    Main chatbot endpoint.
    Accepts user message + conversation history.
    Returns LLM reply + matching product cards.
    """
    message = body.message.strip()
    history = body.history or []

    if not message:
        return JSONResponse({"error": "Empty message"}, status_code=400)

    products     = []
    search_query = ""

    if is_product_query(message):
        search_query = extract_search_query(message, history)
        products     = search(search_query, top_k=8)

    # RAG: pass retrieved products as context to LLM
    reply = chat(message, history, products=products)
    speak(reply)

    return {
        "reply"       : reply,
        "products"    : products,
        "search_query": search_query,
    }


@app.post("/search")
async def search_endpoint(body: SearchRequest):
    """
    Direct product search endpoint (no LLM).
    Useful for testing the search engine directly.
    """
    results = search(body.query, top_k=body.top_k, category_filter=body.category)
    return {
        "query"  : body.query,
        "count"  : len(results),
        "results": results,
    }


@app.post("/voice")
async def voice_endpoint():
    """Listen from microphone and return transcribed text."""
    text, error = listen(timeout=6, phrase_limit=10)
    if error:
        return JSONResponse({"error": error}, status_code=400)
    return {"text": text}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "message": "ShopBot is running"}


# ── STARTUP ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    import asyncio, concurrent.futures
    loop = asyncio.get_event_loop()
    executor = concurrent.futures.ThreadPoolExecutor()

    print("\n[Startup] Pre-loading search engine...")
    from search_engine import _load as load_search
    await loop.run_in_executor(executor, load_search)

    print("[Startup] Pre-loading chatbot model...")
    from chatbot import _load as load_chat
    await loop.run_in_executor(executor, load_chat)

    print("[Startup] All models ready.\n")


if __name__ == "__main__":
    print("=" * 55)
    print("  ShopBot — AI Shopping Chatbot (FastAPI)")
    print("  UI:      http://localhost:8000")
    print("  API Docs: http://localhost:8000/docs")
    print("=" * 55)
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
