"""
app.py — Flask web app for the AI Shopping Chatbot.
Run: python assistant/app.py
Open: http://localhost:5000
"""

from flask import Flask, render_template, request, jsonify, session
from search_engine import search, summarize
from chatbot import chat, extract_search_query, is_product_query
from voice_agent import listen, speak, is_microphone_available
import uuid

app = Flask(__name__)
app.secret_key = "shopbot-secret-key-2024"


@app.route("/")
def index():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return render_template("index.html", mic_available=is_microphone_available())


@app.route("/chat", methods=["POST"])
def chat_endpoint():
    data    = request.get_json()
    message = (data.get("message") or "").strip()
    history = data.get("history", [])   # [{role, content}, ...]

    if not message:
        return jsonify({"error": "Empty message"}), 400

    products = []
    search_query = ""

    # Decide if we should search for products
    if is_product_query(message):
        # Extract clean search query using LLM
        search_query = extract_search_query(message, history)
        products     = search(search_query, top_k=8)

    # Generate conversational reply
    reply = chat(message, history, products_found=len(products))

    # Speak the reply
    speak(reply)

    return jsonify({
        "reply"        : reply,
        "products"     : products,
        "search_query" : search_query,
    })


@app.route("/voice", methods=["POST"])
def voice_input():
    text, error = listen(timeout=6, phrase_limit=10)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"text": text})


if __name__ == "__main__":
    print("=" * 50)
    print("  ShopBot — AI Shopping Chatbot")
    print("  Open: http://localhost:5000")
    print("=" * 50)
    # Pre-load models on startup
    from search_engine import _load as load_search
    from chatbot import _load as load_chat
    print("Pre-loading search engine...")
    load_search()
    print("Pre-loading chatbot model...")
    load_chat()
    print("All models ready. Starting server...")
    app.run(debug=False, port=5000)
