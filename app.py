import os
from difflib import SequenceMatcher

import pandas as pd
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = "ai-farmer-assistant-secret-key"


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


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.route("/")
def home():

    states = []
    soils = []

    if "state" in market_df.columns:
        states = sorted(
            market_df["state"].astype(str).unique()
        )

    if "soil_type" in soil_df.columns:
        soils = sorted(
            soil_df["soil_type"].astype(str).unique()
        )

    return render_template(
        "index.html",
        states=states,
        soils=soils
    )


# --------------------------------------------------
# DISEASE DETECTION PAGE
# --------------------------------------------------

@app.route("/disease", methods=["GET", "POST"])
def disease():

    disease_name = None
    confidence = None
    solution = None
    image = None

    if request.method == "POST":

        uploaded_file = request.files.get("image")

        if uploaded_file and uploaded_file.filename:

            filename = secure_filename(uploaded_file.filename)

            save_path = os.path.join(
                UPLOAD_DIR,
                filename
            )

            uploaded_file.save(save_path)

            image = "/static/uploads/" + filename

            # The current model is NOT connected yet.
            # This keeps the website safe while we repair
            # the model separately.

            disease_name = "Disease model needs repair"

            confidence = 0

            solution = (
                "Your image was uploaded successfully. "
                "The disease detection model is currently "
                "being repaired before predictions are enabled."
            )

    text = {
        "disease": "Plant Disease Detection",
        "disease_btn": "Detect Disease"
    }

    return render_template(
        "disease.html",
        text=text,
        disease=disease_name,
        confidence=confidence,
        image=image,
        solution=solution,
        translate=lambda value: value
    )


# --------------------------------------------------
# LANGUAGE
# --------------------------------------------------

@app.post("/set-language")
def set_language():

    language = request.form.get("lang", "en")

    session["language"] = language

    return redirect(
        request.referrer or url_for("home")
    )


# --------------------------------------------------
# MARKET API
# --------------------------------------------------

@app.get("/api/market")
def market():

    q = request.args.get(
        "q", ""
    ).lower().strip()

    state = request.args.get(
        "state", ""
    ).lower().strip()

    df = market_df.copy()

    if df.empty:
        return jsonify([])

    if state and "state" in df.columns:

        df = df[
            df["state"]
            .astype(str)
            .str.lower()
            == state
        ]

    if q:

        mask = False

        for column in [
            "commodity",
            "market",
            "district"
        ]:

            if column in df.columns:

                mask = (
                    mask
                    | df[column]
                    .astype(str)
                    .str.lower()
                    .str.contains(
                        q,
                        na=False
                    )
                )

        df = df[mask]

    return jsonify(
        records(df.head(50))
    )


# --------------------------------------------------
# SOIL API
# --------------------------------------------------

@app.get("/api/soil")
def soil():

    name = request.args.get(
        "soil", ""
    ).lower().strip()

    if (
        soil_df.empty
        or "soil_type" not in soil_df.columns
    ):
        return jsonify({})

    df = soil_df[
        soil_df["soil_type"]
        .astype(str)
        .str.lower()
        == name
    ]

    if df.empty:
        return jsonify({})

    return jsonify(
        records(df.head(1))[0]
    )


# --------------------------------------------------
# FARMING CALENDAR API
# --------------------------------------------------

@app.get("/api/calendar")
def calendar():

    state = request.args.get(
        "state", ""
    ).lower().strip()

    df = calendar_df.copy()

    if df.empty:
        return jsonify([])

    if state and "state" in df.columns:

        df = df[
            df["state"]
            .astype(str)
            .str.lower()
            == state
        ]

    return jsonify(
        records(df.head(50))
    )


# --------------------------------------------------
# FARMER AI CHAT API
# --------------------------------------------------

@app.post("/api/chat")
def chat():

    data = request.get_json(
        silent=True
    ) or {}

    question = data.get(
        "question", ""
    ).strip().lower()

    if not question or chat_df.empty:

        return jsonify({
            "answer":
                "Please ask an agriculture question."
        })

    best_answer = None
    best_score = 0

    for _, row in chat_df.iterrows():

        original = str(
            row.get("question", "")
        )

        candidate = original.lower()

        score = SequenceMatcher(
            None,
            question,
            candidate
        ).ratio()

        common_words = (
            set(question.split())
            & set(candidate.split())
        )

        score += min(
            len(common_words) * 0.05,
            0.25
        )

        if score > best_score:

            best_score = score
            best_answer = str(
                row.get("answer", "")
            )

    if best_score < 0.25:

        best_answer = (
            "I couldn't find a close answer. "
            "Try asking about crops, soil, fertilizer, "
            "irrigation, pests, diseases, or farming."
        )

    return jsonify({
        "answer": best_answer
    })

# --------------------------------------------------
# FEATURE PAGES
# --------------------------------------------------

PAGE_TEXT = {
    "schemes": "Government Schemes",
    "central_schemes": "Central Government Schemes",
    "official_site": "Official Website",
    "pmkisan_title": "PM-KISAN",
    "pmkisan_desc": "Financial support for eligible farmers.",
    "pmfby_title": "PM Fasal Bima Yojana",
    "pmfby_desc": "Crop insurance support for farmers.",
    "soilhealth_title": "Soil Health Card",
    "soilhealth_desc": "Information about soil health and management.",
    "select_state": "Select State",

    "market": "Nearby Agricultural Markets",
    "market_desc": "Find agricultural markets near you.",

    "prices": "Market Prices",
    "search_crop": "Search Crop",
    "crop_not_found": "Crop not found",
    "price": "Price",

    "weather_dashboard": "Weather Dashboard",
    "enter_place": "Enter Place",
    "add_place": "Add Place",
    "my_location": "My Location",
    "condition": "Condition",
    "temp": "Temperature",
    "humidity": "Humidity",
    "rain": "Rain",
    "wind": "Wind",
    "place_not_found": "Place not found",
    "enter_valid_place": "Please enter a valid place",
    "latest_weather_news": "Latest Weather News",

    "soil": "Soil Information",
    "soil_title": "Soil Information",
    "advantages": "Advantages",
    "limitations": "Limitations",
    "best_crops": "Best Crops",
    "fertilizer_tips": "Fertilizer Tips",
    "pest_management": "Pest Management",
    "loading_soil": "Loading soil information...",
    "error_loading_soil": "Error loading soil information",

    "calendar": "Farming Calendar",
    "sowing": "Sowing",
    "planting": "Planting",
    "harvest": "Harvest",
    "loading_calendar": "Loading calendar...",
    "error_loading_calendar": "Error loading calendar",

    "disease": "Plant Disease Detection",
    "disease_btn": "Detect Disease"
}


@app.route("/dashboard")
def dashboard():
    return render_template(
        "dashboard.html",
        text=PAGE_TEXT
    )


@app.route("/schemes")
def schemes():
    return render_template(
        "schemes.html",
        text=PAGE_TEXT
    )


@app.route("/market")
def market_page():
    return render_template(
        "market.html",
        text=PAGE_TEXT
    )


@app.route("/prices")
def prices():
    return render_template(
        "prices.html",
        text=PAGE_TEXT
    )


@app.route("/weather")
def weather():
    return render_template(
        "weather.html",
        text=PAGE_TEXT
    )


@app.route("/soil")
def soil_page():
    return render_template(
        "soil.html",
        text=PAGE_TEXT
    )


@app.route("/calendar")
def calendar_page():
    return render_template(
        "calendar.html",
        text=PAGE_TEXT
    )


@app.route("/farmer-ai")
def farmer_ai():
    return render_template(
        "farmer_ai.html"
    )


# --------------------------------------------------
# OLD TEMPLATE API ROUTES
# --------------------------------------------------

@app.get("/get-price")
def get_price():

    crop = request.args.get(
        "crop", ""
    ).strip().lower()

    if market_df.empty:
        return jsonify({
            "error": "No market data available"
        })

    df = market_df.copy()

    if "commodity" not in df.columns:
        return jsonify({
            "error": "Commodity data unavailable"
        })

    matches = df[
        df["commodity"]
        .astype(str)
        .str.lower()
        .str.contains(crop, na=False)
    ]

    if matches.empty:
        return jsonify({
            "error": "Crop not found"
        })

    row = matches.iloc[0]

    return jsonify({
        "crop": str(row.get("commodity", "")),
        "price": str(row.get("modal_price", "")),
        "market": str(row.get("market", "")),
        "district": str(row.get("district", ""))
    })


@app.get("/get-soil")
def get_soil():

    name = request.args.get(
        "soil", ""
    ).lower().strip()

    if soil_df.empty:
        return jsonify({
            "error": "Soil data unavailable"
        })

    df = soil_df[
        soil_df["soil_type"]
        .astype(str)
        .str.lower()
        == name
    ]

    if df.empty:
        return jsonify({
            "error": "Soil type not found"
        })

    return jsonify(
        records(df.head(1))[0]
    )


@app.get("/get-calendar")
def get_calendar():

    state = request.args.get(
        "state", ""
    ).lower().strip()

    df = calendar_df.copy()

    if df.empty:
        return jsonify({
            "error": "Calendar data unavailable"
        })

    if state and "state" in df.columns:
        df = df[
            df["state"]
            .astype(str)
            .str.lower()
            == state
        ]

    return jsonify(
        records(df.head(50))
    )


@app.post("/chat")
def old_chat():

    data = request.get_json(
        silent=True
    ) or {}

    question = data.get(
        "message", ""
    ).strip().lower()

    if not question or chat_df.empty:
        return jsonify({
            "reply": "Please ask an agriculture question."
        })

    best_answer = None
    best_score = 0

    for _, row in chat_df.iterrows():

        candidate = str(
            row.get("question", "")
        ).lower()

        score = SequenceMatcher(
            None,
            question,
            candidate
        ).ratio()

        common_words = (
            set(question.split())
            & set(candidate.split())
        )

        score += min(
            len(common_words) * 0.05,
            0.25
        )

        if score > best_score:
            best_score = score
            best_answer = str(
                row.get("answer", "")
            )

    if best_score < 0.25:
        best_answer = (
            "I couldn't find a close answer. "
            "Try asking about crops, soil, fertilizer, "
            "irrigation, pests, diseases, or farming."
        )

    return jsonify({
        "reply": best_answer
    })
# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/health")
def health():

    return "OK", 200


# --------------------------------------------------
# LOCAL RUN
# --------------------------------------------------

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
