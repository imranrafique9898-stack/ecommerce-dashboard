"""
app.py — Flask web app for the AI Shopping Assistant.
Run: python assistant/app.py
Then open: http://localhost:5000
"""

from flask import Flask, render_template, request, jsonify
from search_engine import search, summarize_results
from voice_agent import listen, speak, is_microphone_available

app = Flask(__name__)


@app.route("/")
def index():
    mic_available = is_microphone_available()
    return render_template("index.html", mic_available=mic_available)


@app.route("/search", methods=["POST"])
def search_products():
    data  = request.get_json()
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"error": "Empty query"}), 400

    results = search(query, top_k=12)
    summary = summarize_results(query, results)

    # Speak the summary
    speak(summary)

    return jsonify({"query": query, "summary": summary, "results": results})


@app.route("/voice", methods=["POST"])
def voice_input():
    """Listen from microphone and return transcribed text."""
    text, error = listen(timeout=6, phrase_limit=10)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"text": text})


if __name__ == "__main__":
    print("=" * 50)
    print("  AI Shopping Assistant")
    print("  Open: http://localhost:5000")
    print("=" * 50)
    app.run(debug=False, port=5000)
