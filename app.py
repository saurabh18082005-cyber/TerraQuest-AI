
import base64
import json
import math
import os
import sqlite3
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

DB_PATH = Path(__file__).with_name("terraquest.db")

# OpenRouter vision model configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = (
    os.getenv("OPENROUTER_MODEL", "openrouter/free").strip()
    or "openrouter/free"
)
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


# -------------------- DATABASE --------------------

def get_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS explorers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                points INTEGER NOT NULL DEFAULT 0,
                discoveries INTEGER NOT NULL DEFAULT 0,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


def distance_km(lat1, lon1, lat2, lon2):
    radius = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)

    a = (
        math.sin(dp / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    )

    return radius * 2 * math.atan2(
        math.sqrt(a), math.sqrt(max(0.0, 1 - a))
    )


init_db()


# -------------------- MISSION GENERATION --------------------

DISCOVERY_TARGETS = [
    (10, 3, 1),
    (20, 5, 2),
    (30, 7, 3),
    (45, 10, 4),
    (60, 12, 5),
]


def get_discovery_targets(duration):
    for minutes, plants, insects in DISCOVERY_TARGETS:
        if duration <= minutes:
            return plants, insects

    extra_blocks = min((duration - 60) // 15 + 1, 4)
    return 12 + extra_blocks * 2, 5 + extra_blocks


def generate_mission(activity, duration, difficulty, interests):
    plants, insects = get_discovery_targets(duration)

    activity_details = {
        "nature": {
            "title": "Nature Detective",
            "plant_label": "plants or trees",
            "intro": (
                "Explore your surroundings and notice local biodiversity."
            ),
        },
        "gardening": {
            "title": "Garden Explorer",
            "plant_label": "garden plants or trees",
            "intro": "Explore a garden and observe how plants grow.",
        },
        "walking": {
            "title": "Mindful Trail Explorer",
            "plant_label": "plants or trees",
            "intro": (
                "Take a safe walk and discover the nature along your route."
            ),
        },
    }

    details = activity_details[activity]

    steps = [
        f"Find and observe {plants} different "
        f"{details['plant_label']}.",
        f"Look for {insects} different insect"
        f"{'s' if insects != 1 else ''} from a respectful distance.",
        (
            "Notice differences in leaf shape, colour, size, "
            "or other visible features."
        ),
        (
            "Record your observations and photograph discoveries "
            "without disturbing living things."
        ),
    ]

    if difficulty == "intermediate":
        steps.append(
            "Compare two observations and note one similarity "
            "and one difference."
        )
    elif difficulty == "challenging":
        steps.append(
            "Try to identify your discoveries using visible evidence "
            "and reliable reference material. Mark uncertain "
            "identifications as unknown."
        )

    if interests:
        steps.append(f"Pay special attention to your interest: {interests}.")

    return {
        "title": details["title"],
        "duration": duration,
        "difficulty": difficulty,
        "description": (
            f"{details['intro']} You have {duration} minutes. "
            f"Your targets are {plants} plants or trees and "
            f"{insects} insects. These are goals, not requirements: "
            "complete the mission safely even if some organisms "
            "are not present."
        ),
        "targets": {"plants": plants, "insects": insects},
        "steps": steps,
        "interests": interests,
        "ai_powered": False,
    }


# -------------------- WEBSITE --------------------

@app.route("/")
def home():
    return render_template("index.html")


# -------------------- MISSION API --------------------

@app.route("/api/mission", methods=["POST"])
def create_mission():
    data = request.get_json(silent=True) or {}

    activity = data.get("activity", "nature")
    difficulty = data.get("difficulty", "beginner")
    interests = data.get("interests", "")

    if activity not in {"nature", "gardening", "walking"}:
        return jsonify({
            "error": "Please select a valid activity."
        }), 400

    if difficulty not in {"beginner", "intermediate", "challenging"}:
        return jsonify({
            "error": "Please select a valid difficulty."
        }), 400

    try:
        duration = int(data.get("duration", 20))
    except (TypeError, ValueError):
        return jsonify({
            "error": "Duration must be a number."
        }), 400

    if not 5 <= duration <= 120:
        return jsonify({
            "error": "Choose a duration from 5 to 120 minutes."
        }), 400

    if not isinstance(interests, str) or len(interests) > 200:
        return jsonify({
            "error": "Interests must be text with at most 200 characters."
        }), 400

    return jsonify(
        generate_mission(
            activity,
            duration,
            difficulty,
            interests.strip(),
        )
    )


# -------------------- EXPLORER PROFILE API --------------------

@app.route("/api/profile", methods=["POST"])
def create_explorer_profile():
    data = request.get_json(silent=True) or {}

    name = data.get("name", "Nature Explorer")

    try:
        lat = float(data.get("lat"))
        lon = float(data.get("lon"))
    except (TypeError, ValueError):
        return jsonify({
            "error": "Location coordinates are required."
        }), 400

    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 30:
        return jsonify({
            "error": "Name must be 1–30 characters."
        }), 400

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return jsonify({
            "error": "Invalid coordinates."
        }), 400

    # Store approximate coordinates, not precise location.
    lat, lon = round(lat, 2), round(lon, 2)

    with get_db() as db:
        existing = db.execute(
            "SELECT id FROM explorers WHERE name = ?",
            (name.strip(),),
        ).fetchone()

        if existing:
            db.execute(
                """
                UPDATE explorers
                SET latitude = ?, longitude = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (lat, lon, existing["id"]),
            )
        else:
            db.execute(
                """
                INSERT INTO explorers(name, latitude, longitude)
                VALUES (?, ?, ?)
                """,
                (name.strip(), lat, lon),
            )

    return jsonify({
        "ok": True,
        "message": (
            "Explorer profile saved. Points are awarded only by "
            "verified discovery processing."
        ),
    })


# -------------------- LEADERBOARD API --------------------

@app.route("/api/leaderboard", methods=["GET"])
def nearby_leaderboard():
    try:
        lat = float(request.args.get("lat", ""))
        lon = float(request.args.get("lon", ""))
    except (TypeError, ValueError):
        return jsonify({
            "error": (
                "Press the location button to share your "
                "approximate coordinates."
            )
        }), 400

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return jsonify({"error": "Invalid coordinates."}), 400

    lat_delta = 25 / 111.0
    lon_delta = 25 / max(
        20.0, 111.0 * math.cos(math.radians(lat))
    )

    with get_db() as db:
        rows = db.execute(
            """
            SELECT name, points, discoveries, latitude, longitude
            FROM explorers
            WHERE latitude BETWEEN ? AND ?
              AND longitude BETWEEN ? AND ?
            """,
            (
                lat - lat_delta,
                lat + lat_delta,
                lon - lon_delta,
                lon + lon_delta,
            ),
        ).fetchall()

    nearby = []

    for row in rows:
        distance = distance_km(
            lat, lon, row["latitude"], row["longitude"]
        )

        if distance <= 25:
            nearby.append({
                "name": row["name"],
                "points": row["points"],
                "discoveries": row["discoveries"],
                "distance": distance,
            })

    nearby.sort(
        key=lambda item: (
            -item["points"],
            -item["discoveries"],
            item["distance"],
            item["name"].lower(),
        )
    )

    top = [
        {
            "rank": index,
            "name": entry["name"],
            "points": entry["points"],
            "discoveries": entry["discoveries"],
            "area": "Within 25 km",
        }
        for index, entry in enumerate(nearby[:10], start=1)
    ]

    return jsonify({
        "explorers": top,
        "radius_km": 25,
        "count": len(top),
    })


# -------------------- VISION IDENTIFICATION HELPERS --------------------

def extract_json_object(text):
    """Parse model JSON, with a safe fallback for plain-text vision replies."""
    import re

    cleaned = (text or "").strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(cleaned[start:end + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    # Some free vision models ignore JSON-only instructions. Preserve their
    # text as an explicitly unverified observation instead of failing the UI
    # or pretending we received structured scientific metadata.
    if not cleaned:
        raise ValueError("The vision model returned an empty response.")

    species = "Uncertain identification"
    patterns = [
        r"\b(?:likely|probably|appears to be|looks like|identified as|this is|it is)\s+(?:a|an|the)?\s*([A-Za-z][A-Za-z -]{1,70})",
    ]
    for pattern in patterns:
        match = re.search(pattern, cleaned, flags=re.IGNORECASE)
        if match:
            candidate = match.group(1).strip(" .,:;\n\t")
            candidate = re.split(r"\b(?:which|that|with|on|in|because|based)\b", candidate, maxsplit=1, flags=re.IGNORECASE)[0].strip()
            if candidate:
                species = candidate[:120]
            break

    return {
        "species": species,
        "scientific_name": "",
        "group": "unknown",
        "visual_evidence": cleaned[:700],
        "alternatives": [],
        "limitations": "The model replied in plain text, so the identification remains unverified.",
    }


# -------------------- OPENROUTER IMAGE IDENTIFICATION API --------------------

@app.route("/api/identify", methods=["POST"])
def identify_discovery():
    if not OPENROUTER_API_KEY:
        return jsonify({
            "error": (
                "OpenRouter is not configured. Add OPENROUTER_API_KEY "
                "to your local .env file and restart Flask."
            )
        }), 503

    if "image" not in request.files or not request.files["image"].filename:
        return jsonify({
            "error": "Upload or capture an image first."
        }), 400

    image = request.files["image"]

    allowed_types = {
        "image/jpeg",
        "image/png",
        "image/webp",
    }

    if image.mimetype not in allowed_types:
        return jsonify({
            "error": "Use a JPG, PNG, or WEBP image."
        }), 400

    image_bytes = image.read()

    if not image_bytes:
        return jsonify({
            "error": "The uploaded image is empty."
        }), 400

    if len(image_bytes) > 10 * 1024 * 1024:
        return jsonify({
            "error": "Image must be 10 MB or smaller."
        }), 413

    prompt = (
        "You are a cautious biodiversity field assistant. Examine the "
        "supplied image and identify the most visible organism, if one "
        "is clearly visible. Do not invent details. If identification "
        "is uncertain, use species='Uncertain identification' and an "
        "empty scientific_name. Return ONLY one JSON object with these "
        "keys: species (common name or uncertain), scientific_name "
        "(string or empty), group (one of plant, tree, flower, insect, "
        "animal, other, unknown), visual_evidence (short observations "
        "visible in the image), alternatives (array of up to 3 plausible "
        "alternatives), limitations (short caveat). Do not determine "
        "geographic rarity, conservation status, or award points. Do not "
        "claim calibrated numerical confidence. This is an AI suggestion "
        "that needs independent verification."
    )

    try:
        encoded_image = base64.b64encode(image_bytes).decode("ascii")
        image_data_url = f"data:{image.mimetype};base64,{encoded_image}"

        api_response = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5000",
                "X-Title": "TerraQuest AI",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_data_url}},
                    ],
                }],
                "temperature": 0.1,
                "max_tokens": 450,
            },
            timeout=60,
        )

        if not api_response.ok:
            # Log status and a bounded response body, never request headers/secrets.
            app.logger.warning(
                "OpenRouter vision request returned HTTP %s: %s",
                api_response.status_code,
                api_response.text[:1000],
            )
            if api_response.status_code == 401:
                return jsonify({"error": "OpenRouter rejected the API key. Check OPENROUTER_API_KEY in your local .env file."}), 502
            if api_response.status_code == 402:
                return jsonify({"error": "OpenRouter reports insufficient credits for this model. Choose a model marked free and confirm your account's access."}), 502
            if api_response.status_code == 429:
                return jsonify({"error": "OpenRouter rate limit reached. Wait briefly and try again."}), 502
            return jsonify({"error": f"OpenRouter could not identify this image (HTTP {api_response.status_code}). Check the terminal for details."}), 502

        payload = api_response.json()
        choices = payload.get("choices") or []
        if not choices:
            raise ValueError("The model returned no choices.")
        message_content = choices[0].get("message", {}).get("content", "")
        if isinstance(message_content, list):
            model_text = "\n".join(
                str(part.get("text", "")) for part in message_content
                if isinstance(part, dict)
            )
        else:
            model_text = str(message_content or "")
        if not model_text.strip():
            app.logger.warning(
                "OpenRouter returned no message text. Finish reason: %s; response keys: %s",
                choices[0].get("finish_reason", "unknown"),
                ",".join(sorted(payload.keys())),
            )
        result = extract_json_object(model_text)

    except requests.Timeout:
        app.logger.warning("OpenRouter vision request timed out.")
        return jsonify({"error": "The vision model took too long to respond. Try again."}), 502
    except Exception as exc:
        # Log diagnostics without logging the API key or request headers.
        app.logger.warning(
            "OpenRouter vision request failed (%s): %s",
            type(exc).__name__,
            str(exc)[:1000],
        )
        return jsonify({"error": "OpenRouter image identification failed. Check the model setting and terminal error, then try again."}), 502

    species = str(
        result.get("species", "Uncertain identification")
    )[:120]

    scientific_name = str(
        result.get("scientific_name", "")
    )[:160]

    group = str(result.get("group", "unknown"))[:30]

    evidence = str(
        result.get("visual_evidence", "")
    )[:700]

    limitations = str(
        result.get("limitations", "")
    )[:400]

    alternatives = result.get("alternatives", [])

    if not isinstance(alternatives, list):
        alternatives = []

    alternatives = [
        str(item)[:120] for item in alternatives[:3]
    ]

    explanation_parts = [
        "AI-generated suggestion only; not independently verified."
    ]

    if evidence:
        explanation_parts.append(
            "Visible evidence: " + evidence
        )

    if alternatives:
        explanation_parts.append(
            "Possible alternatives: " + ", ".join(alternatives)
        )

    if limitations:
        explanation_parts.append(
            "Limitations: " + limitations
        )

    # Never award points or assert rarity based only on AI output.
    return jsonify({
        "species": species,
        "scientific_name": scientific_name,
        "group": group,
        "rarity": "Unverified",
        "points": 0,
        "verification": "AI suggestion — unverified",
        "explanation": " ".join(explanation_parts),
        "model": OPENROUTER_MODEL,
    })


# -------------------- ERROR HANDLING --------------------

@app.errorhandler(413)
def request_too_large(_error):
    return jsonify({
        "error": "Image must be 10 MB or smaller."
    }), 413


# -------------------- START SERVER --------------------

if __name__ == "__main__":
    app.run(debug=True, port=5000)
