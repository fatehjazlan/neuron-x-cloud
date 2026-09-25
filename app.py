from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

# API key diambil daripada Render Environment
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
        <meta name="viewport"
              content="width=device-width, initial-scale=1">

        <title>NEURON-X AI</title>
    </head>

    <body style="
        font-family:Arial;
        text-align:center;
        padding:40px;
    ">

        <h1>NEURON-X CLOUD AI</h1>

        <p>AI Intent Analysis</p>

        <input
            id="message"
            type="text"
            placeholder="Type message..."
            style="
                padding:12px;
                width:80%;
                max-width:400px;
            "
        >

        <br><br>

        <button
            onclick="analyze()"
            style="padding:12px 25px;"
        >
            ANALYZE WITH AI
        </button>

        <h3>AI Result:</h3>

        <p
            id="result"
            style="white-space:pre-line;"
        >
            Waiting for message...
        </p>


        <script>

        async function analyze() {

            const message =
                document.getElementById("message").value;

            if (!message.trim()) {

                document.getElementById("result").innerText =
                    "Please enter a message.";

                return;
            }

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
                        "Error: " +
                        (data.error || "Unknown error") +
                        "\\n" +
                        (data.details || "");

                }


            }

            catch (error) {

                document.getElementById("result").innerText =
                    "Connection error: " + error;

            }

        }

        </script>

    </body>

    </html>
    """


# =========================
# AI ANALYSIS
# =========================
@app.route("/analyze", methods=["POST"])
def analyze():

    try:

        # Get JSON from ESP8266 / website
        data = request.get_json(silent=True)


        if not data or not data.get("message"):

            return jsonify({
                "error": "No message received"
            }), 400


        # Check API key
        if not GEMINI_API_KEY:

            print(
                "ERROR: GEMINI_API_KEY NOT FOUND",
                flush=True
            )

            return jsonify({
                "error": "Gemini API key not configured"
            }), 500


        message = str(data["message"]).strip()


        print(
            "MESSAGE RECEIVED:",
            message,
            flush=True
        )


        # =========================
        # AI PROMPT
        # =========================

        prompt = f"""
You are the AI intent classifier for NEURON-X,
an assistive communication device for a deafblind user.

Analyze the message below.

The message may be written in:
- Malay
- informal Malay
- English
- short phrases

Classify the message into EXACTLY ONE category:

TOILET
FOOD_DRINK
HELP
EMERGENCY
NORMAL_MESSAGE

Classification rules:

TOILET:
The user wants to go to the toilet,
use the bathroom, or relieve themselves.

FOOD_DRINK:
The user wants food, water, or another drink.

HELP:
The user asks for assistance or support.

EMERGENCY:
The message explicitly indicates immediate danger,
an emergency, injury, or urgent assistance.

NORMAL_MESSAGE:
Any normal message that does not fit the categories above.

Examples:

"Saya nak pergi tandas"
TOILET

"Nak buang air"
TOILET

"Saya dahaga"
FOOD_DRINK

"Nak makan"
FOOD_DRINK

"Tolong saya"
HELP

"Saya dalam bahaya"
EMERGENCY

"Apa khabar"
NORMAL_MESSAGE

User message:
{message}

IMPORTANT:
Return ONLY the category name.

Do not explain.
Do not use markdown.
Do not add punctuation.
"""


        # =========================
        # GEMINI API
        # =========================

        url = (
            "https://generativelanguage.googleapis.com/"
            "v1beta/models/gemini-3.5-flash:generateContent"
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

            ],

            "generationConfig": {

                "temperature": 0,

                "maxOutputTokens": 20

            }

        }


        headers = {

            "Content-Type": "application/json",

            "x-goog-api-key": GEMINI_API_KEY

        }


        print(
            "SENDING MESSAGE TO GEMINI...",
            flush=True
        )


        response = requests.post(

            url,

            headers=headers,

            json=payload,

            timeout=30

        )


        print(
            "GEMINI STATUS:",
            response.status_code,
            flush=True
        )


        # =========================
        # GEMINI ERROR
        # =========================

        if response.status_code != 200:

            print(
                "GEMINI RESPONSE ERROR:",
                response.text,
                flush=True
            )

            return jsonify({

                "error": "Gemini API error",

                "details":
                    "HTTP " +
                    str(response.status_code) +
                    ": " +
                    response.text

            }), 500


        # =========================
        # READ AI RESPONSE
        # =========================

        result = response.json()


        print(
            "GEMINI RESPONSE:",
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


        # =========================
        # SAFETY CHECK
        # =========================

        allowed_intents = [

            "TOILET",

            "FOOD_DRINK",

            "HELP",

            "EMERGENCY",

            "NORMAL_MESSAGE"

        ]


        if intent not in allowed_intents:

            print(
                "UNKNOWN INTENT:",
                intent,
                flush=True
            )

            intent = "NORMAL_MESSAGE"


        # =========================
        # SUCCESS
        # =========================

        print(
            "AI INTENT:",
            intent,
            flush=True
        )


        return jsonify({

            "status": "success",

            "message": message,

            "intent": intent

        })


    # =========================
    # PYTHON ERROR
    # =========================

    except Exception as e:

        print(
            "GEMINI ERROR:",
            repr(e),
            flush=True
        )


        return jsonify({

            "error": "AI request failed",

            "details": str(e)

        }), 500


# =========================
# START SERVER
# =========================
if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )


    app.run(

        host="0.0.0.0",

        port=port

    )
