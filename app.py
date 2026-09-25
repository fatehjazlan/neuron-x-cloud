from flask import Flask, request, jsonify
import os
import requests
import time

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# =========================
# WEBSITE
# =========================

@app.route("/")
def home():
    return """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>NEURON-X AI</title>
</head>

<body style="font-family:Arial; text-align:center; padding:40px;">

    <h1>NEURON-X CLOUD AI</h1>
    <p>AI Intent Analysis</p>

    <input
        id="message"
        type="text"
        placeholder="Type message..."
        style="padding:12px; width:80%; max-width:400px;"
    >

    <br><br>

    <button
        id="analyzeButton"
        onclick="analyze()"
        style="padding:12px 25px;"
    >
        ANALYZE WITH AI
    </button>

    <h3>AI Result:</h3>

    <p id="result" style="white-space:pre-line;">
        Waiting for message...
    </p>


<script>

async function analyze() {

    const message = document.getElementById("message").value;
    const result = document.getElementById("result");
    const button = document.getElementById("analyzeButton");

    if (!message.trim()) {
        result.innerText = "Please enter a message.";
        return;
    }

    result.innerText = "AI analyzing...";
    button.disabled = true;

    try {

        const response = await fetch("/analyze", {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                message: message
            })
        });

        const data = await response.json();

        if (data.intent) {

            result.innerText =
                "Message: " + data.message +
                "\\nAI Intent: " + data.intent;

        } else {

            result.innerText =
                "Error: " + (data.error || "Unknown error") +
                "\\n" + (data.details || "");
        }

    } catch (error) {

        result.innerText =
            "Connection error: " + error;

    } finally {

        button.disabled = false;
    }
}

</script>

</body>
</html>
"""


# =========================
# GEMINI FUNCTION
# =========================

def ask_gemini(message):

    prompt = f"""
You are the AI intent classifier for NEURON-X,
an assistive communication device for a deafblind user.

Understand Malay, informal Malay, and English.

Classify the user's message into EXACTLY ONE category:

TOILET
FOOD_DRINK
HELP
EMERGENCY
NORMAL_MESSAGE

Rules:

TOILET:
User wants to go to the toilet, bathroom,
or relieve themselves.

FOOD_DRINK:
User wants food, water, or another drink,
or says they are hungry or thirsty.

HELP:
User asks for assistance.

EMERGENCY:
User explicitly indicates immediate danger,
injury, emergency, or urgent assistance.

NORMAL_MESSAGE:
Anything else.

Examples:

Saya nak pergi tandas
TOILET

Nak buang air
TOILET

Saya dahaga
FOOD_DRINK

Saya lapar
FOOD_DRINK

Tolong saya
HELP

Saya dalam bahaya
EMERGENCY

Apa khabar
NORMAL_MESSAGE

User message:
{message}

Return ONLY the category name.
Do not explain.
Do not use markdown.
Do not add punctuation.
"""

    # Gemini API
    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/gemini-3.5-flash-lite:generateContent"
    )

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "maxOutputTokens": 20
        }
    }

    # =========================
    # AUTOMATIC RETRY
    # =========================

    max_attempts = 4

    for attempt in range(max_attempts):

        try:

            print(
                f"Gemini attempt {attempt + 1}/{max_attempts}",
                flush=True
            )

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=60
            )

            print(
                "Gemini HTTP status:",
                response.status_code,
                flush=True
            )

            # Success
            if response.status_code == 200:
                return response

            # Temporary error
            if response.status_code in [408, 429, 500, 502, 503, 504]:

                print(
                    "Temporary Gemini error:",
                    response.text,
                    flush=True
                )

                if attempt < max_attempts - 1:

                    # Retry delay:
                    # 2 sec -> 4 sec -> 8 sec
                    delay = 2 ** (attempt + 1)

                    print(
                        f"Retrying in {delay} seconds...",
                        flush=True
                    )

                    time.sleep(delay)
                    continue

            # Other error
            return response

        except requests.exceptions.RequestException as error:

            print(
                "Gemini connection error:",
                repr(error),
                flush=True
            )

            if attempt < max_attempts - 1:

                delay = 2 ** (attempt + 1)

                print(
                    f"Retrying in {delay} seconds...",
                    flush=True
                )

                time.sleep(delay)
                continue

            raise

    return None


# =========================
# ANALYZE ENDPOINT
# =========================

@app.route("/analyze", methods=["POST"])
def analyze():

    try:

        data = request.get_json(silent=True)

        if not data or not data.get("message"):

            return jsonify({
                "error": "No message received"
            }), 400


        if not GEMINI_API_KEY:

            print(
                "ERROR: GEMINI_API_KEY not found",
                flush=True
            )

            return jsonify({
                "error": "Gemini API key not configured"
            }), 500


        message = str(data["message"]).strip()

        print(
            "Message received:",
            message,
            flush=True
        )


        # Send message to Gemini
        response = ask_gemini(message)


        if response is None:

            return jsonify({
                "error": "Gemini did not respond"
            }), 503


        # =========================
        # API ERROR
        # =========================

        if response.status_code != 200:

            print(
                "Gemini API error:",
                response.text,
                flush=True
            )

            if response.status_code == 503:

                return jsonify({
                    "error": "Gemini is temporarily busy",
                    "details": "Please try again in a moment."
                }), 503

            return jsonify({
                "error": "Gemini API error",
                "details":
                    "HTTP " +
                    str(response.status_code) +
                    ": " +
                    response.text
            }), 500


        # =========================
        # READ GEMINI RESPONSE
        # =========================

        result = response.json()

        print(
            "Gemini response:",
            result,
            flush=True
        )


        intent = (
            result["candidates"][0]
            ["content"]
            ["parts"][0]
            ["text"]
            .strip()
            .upper()
        )


        # Clean output
        intent = (
            intent
            .replace(".", "")
            .replace("`", "")
            .strip()
        )


        allowed_intents = [
            "TOILET",
            "FOOD_DRINK",
            "HELP",
            "EMERGENCY",
            "NORMAL_MESSAGE"
        ]


        if intent not in allowed_intents:

            print(
                "Unknown intent:",
                intent,
                flush=True
            )

            intent = "NORMAL_MESSAGE"


        print(
            "FINAL AI INTENT:",
            intent,
            flush=True
        )


        # =========================
        # SUCCESS
        # =========================

        return jsonify({
            "status": "success",
            "message": message,
            "intent": intent
        })


    except Exception as error:

        print(
            "NEURON-X ERROR:",
            repr(error),
            flush=True
        )

        return jsonify({
            "error": "AI request failed",
            "details": str(error)
        }), 500


# =========================
# START SERVER
# =========================

if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 10000)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
