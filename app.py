from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")


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

        <input id="message"
               type="text"
               placeholder="Type message..."
               style="padding:12px; width:80%; max-width:400px;">

        <br><br>

        <button onclick="analyze()"
                style="padding:12px 25px;">
            ANALYZE WITH AI
        </button>

        <h3>AI Result:</h3>
        <p id="result">Waiting for message...</p>

        <script>
        async function analyze() {

            const message =
                document.getElementById("message").value;

            document.getElementById("result").innerText =
                "AI analyzing...";

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
                    document.getElementById("result").innerText =
                        "Message: " + data.message +
                        "\\nAI Intent: " + data.intent;
                }
                else {
                    document.getElementById("result").innerText =
                        "Error: " + (data.error || "Unknown error");
                }

            } catch (error) {

                document.getElementById("result").innerText =
                    "Connection error";

            }
        }
        </script>

    </body>
    </html>
    """


@app.route("/analyze", methods=["POST"])
def analyze():

    data = request.get_json(silent=True)

    if not data or not data.get("message"):
        return jsonify({
            "error": "No message received"
        }), 400

    if not GEMINI_API_KEY:
        return jsonify({
            "error": "Gemini API key not configured"
        }), 500

    message = data["message"]

    prompt = f"""
You are the intent classifier for NEURON-X,
an assistive communication device.

Analyze the user's message.

Choose ONLY ONE of these categories:

TOILET
FOOD_DRINK
HELP
EMERGENCY
NORMAL_MESSAGE

Rules:
TOILET = user wants to use or go to the toilet.
FOOD_DRINK = user wants food or a drink.
HELP = user is asking for assistance.
EMERGENCY = user explicitly communicates immediate danger or emergency.
NORMAL_MESSAGE = anything else.

Understand informal Malay, standard Malay and English.

User message:
{message}

Return ONLY the category name.
"""

    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/gemini-2.5-flash:generateContent"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }

    try:

        response = requests.post(
            url,
            headers={
                "x-goog-api-key": GEMINI_API_KEY,
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=20
        )

        if response.status_code != 200:
            return jsonify({
                "error": "Gemini API error",
                "details": response.text
            }), 500

        result = response.json()

        intent = (
            result["candidates"][0]
                  ["content"]["parts"][0]["text"]
                  .strip()
                  .upper()
        )

        allowed = [
            "TOILET",
            "FOOD_DRINK",
            "HELP",
            "EMERGENCY",
            "NORMAL_MESSAGE"
        ]

        if intent not in allowed:
            intent = "NORMAL_MESSAGE"

        return jsonify({
            "status": "success",
            "message": message,
            "intent": intent
        })

    except Exception as e:

        return jsonify({
            "error": "AI request failed",
            "details": str(e)
        }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
