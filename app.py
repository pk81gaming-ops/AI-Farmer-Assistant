import os
from difflib import SequenceMatcher

import pandas as pd
from flask import Flask, render_template, request, jsonify

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

app = Flask(__name__)


def load_csv(filename):
    path = os.path.join(DATA_DIR, filename)
    try:
        return pd.read_csv(path, on_bad_lines="skip")
    except Exception:
        return pd.DataFrame()


market_df = load_csv("market_prices.csv")
soil_df = load_csv("soil_data.csv")
calendar_df = load_csv("farming_calendar.csv")
chat_df = load_csv("agriculture_chatbot_500.csv")


def records(df):
    if df.empty:
        return []
    return df.fillna("").to_dict(orient="records")


@app.route("/")
def home():
    states = []
    soils = []

    if "state" in market_df.columns:
        states = sorted(market_df["state"].astype(str).unique())

    if "soil_type" in soil_df.columns:
        soils = sorted(soil_df["soil_type"].astype(str).unique())

    return render_template(
        "index.html",
        states=states,
        soils=soils
    )


@app.get("/api/market")
def market():
    q = request.args.get("q", "").lower().strip()
    state = request.args.get("state", "").lower().strip()

    df = market_df.copy()

    if df.empty:
        return jsonify([])

    if state and "state" in df.columns:
        df = df[df["state"].astype(str).str.lower() == state]

    if q:
        mask = False

        for column in ["commodity", "market", "district"]:
            if column in df.columns:
                mask = mask | df[column].astype(str).str.lower().str.contains(
                    q, na=False
                )

        df = df[mask]

    return jsonify(records(df.head(50)))


@app.get("/api/soil")
def soil():
    name = request.args.get("soil", "").lower().strip()

    if soil_df.empty or "soil_type" not in soil_df.columns:
        return jsonify({})

    df = soil_df[
        soil_df["soil_type"].astype(str).str.lower() == name
    ]

    if df.empty:
        return jsonify({})

    return jsonify(records(df.head(1))[0])


@app.get("/api/calendar")
def calendar():
    state = request.args.get("state", "").lower().strip()

    df = calendar_df.copy()

    if df.empty:
        return jsonify([])

    if state and "state" in df.columns:
        df = df[df["state"].astype(str).str.lower() == state]

    return jsonify(records(df.head(50)))


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip().lower()

    if not question or chat_df.empty:
        return jsonify({
            "answer": "Please ask an agriculture question."
        })

    best_answer = None
    best_score = 0

    for _, row in chat_df.iterrows():

        original = str(row.get("question", ""))
        candidate = original.lower()

        score = SequenceMatcher(
            None,
            question,
            candidate
        ).ratio()

        common_words = set(question.split()) & set(candidate.split())
        score += min(len(common_words) * 0.05, 0.25)

        if score > best_score:
            best_score = score
            best_answer = str(row.get("answer", ""))

    if best_score < 0.25:
        best_answer = (
            "I couldn't find a close answer. "
            "Try asking about crops, soil, fertilizer, irrigation, "
            "pests, diseases, or farming."
        )

    return jsonify({
        "answer": best_answer
    })


@app.get("/health")
def health():
    return "OK", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
