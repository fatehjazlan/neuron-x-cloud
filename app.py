from flask import Flask, request, jsonify
import os
import requests
import time
import random

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Gemini model
MODEL = "gemini-3.5-flash-lite"


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
        id="analyzeButton"
        onclick="analyze()"
        style="padding:12px 25px;"
    >
        ANALYZE WITH AI
    </button>

    <h3>AI Result:</h3>

    <p id="result"
       style="white-space:pre-line;">
        Waiting for message...
    </p>


<script>

async function analyze() {

    const message =
        document.getElementById("message").value;

    const result =
        document.getElementById("result");

    const button =
        document.getElementById("analyzeButton");


    if (!message.trim()) {

        result.innerText =
            "Please enter a message.";

        return;
    }


    result.innerText =
        "AI analyzing...";

    button.disabled = true;


    try {

        const response =
            await fetch("/analyze", {

                method: "POST",

                headers: {
                    "Content-Type":
                    "application/json"
                },

                body: JSON.stringify({
                    message: message
                })

            });


        const data =
            await response.json();


        if (data.intent) {

            result.innerText =
                "Message: " + data.message +
                "\\nAI Intent: " + data.intent;

        }

        else {

            result.innerText =
                "Error: " +
                (data.error || "Unknown error") +
                "\\n" +
                (data.details || "");

        }

    }

    catch (error) {

        result.innerText =
            "Connection error: " + error;

    }

    finally {

        button.disabled = false;

    }
}

</script>

</body>
</html>
"""


# =========================
# GEMINI REQUEST
# =========================
def ask_gemini(message):

    prompt = f"""
You are the AI intent classifier for NEURON-X,
an assistive communication device for a deafblind user.

Understand Malay, informal Malay and English.

Classify the user's message into EXACTLY ONE
of these categories:

TOILET
FOOD_DRINK
HELP
EMERGENCY
NORMAL_MESSAGE

Rules:

TOILET:
The user wants to go to the toilet,
use the bathroom or relieve themselves.

FOOD_DRINK:
The user wants food, water or another drink,
or says that they are hungry or thirsty.

HELP:
The user asks for assistance.

EMERGENCY:
The user explicitly indicates immediate danger,
injury, emergency or urgent assistance.

NORMAL_MESSAGE:
Anything else.

Examples:

Saya nak pergi tandas
TOILET

Nak buang air
TOILET

Saya dahaga
FOOD_DRINK

Nak air
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


    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{MODEL}:generateContent"
    )


    headers = {

        "Content-Type":
            "application/json",

        "x-goog-api-key":
            GEMINI_API_KEY

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
                f"GEMINI ATTEMPT {attempt + 1}/{max_attempts}",
                flush=True
            )


            response = requests.post(

                url,

                headers=headers,

                json=payload,

                timeout=60

            )


            print(
                "GEMINI STATUS:",
                response.status_code,
                flush=True
            )


            # SUCCESS
            if response.status_code == 200:

                return response


            # Temporary errors
            if response.status_code in [
                408,
                429,
                500,
                502,
                503,
                504
            ]:

                if attempt < max_attempts - 1:

                    # 2 sec → 4 sec → 8 sec
                    delay = (2 ** (attempt + 1))

                    # Small random jitter
                    delay += random.uniform(0, 1)


                    print(
                        f"Temporary Gemini error. "
                        f"Retrying in {delay:.1f}s...",
                        flush=True
                    )


                    time.sleep(delay)

                    continue


            # Non-retryable error
            return response


        except requests.exceptions.RequestException as e:

            print(
                "NETWORK ERROR:",
                repr(e),
                flush=True
            )


            if attempt < max_attempts - 1:

                delay = (2 ** (attempt + 1))

                delay += random.uniform(0, 1)

                time.sleep(delay)

                continue


            raise e


    return None


# =========================
# ANALYZE ENDPOINT
# =========================
@app.route("/analyze", methods=["POST"])
def analyze():

    try:

        data =
            request.get_json(silent=True)


        if not data or not data.get("message"):

            return jsonify({

                "error":
                    "No message received"

            }), 400


        if not GEMINI_API_KEY:

            print(
                "GEMINI_API_KEY NOT FOUND",
                flush=True
            )

            return jsonify({

                "error":
                    "Gemini API key not configured"

            }), 500


        message =
            str(data["message"]).strip()


        print(
            "MESSAGE RECEIVED:",
            message,
            flush=True
        )


        # =========================
        # SEND TO GEMINI
        # =========================

        response =
            ask_gemini(message)


        if response is None:

            return jsonify({

                "error":
                    "Gemini did not respond"

            }), 503


        # =========================
        # GEMINI ERROR
        # =========================

        if response.status_code != 200:

            print(
                "GEMINI ERROR RESPONSE:",
                response.text,
                flush=True
            )


            # Friendly message for busy server
            if response.status_code == 503:

                return jsonify({

                    "error":
                        "Gemini is temporarily busy",

                    "details":
                        "Please try again in a moment."

                }), 503


            return jsonify({

                "error":
                    "Gemini API error",

                "details":
                    "HTTP " +
                    str(response.status_code) +
                    ": " +
                    response.text

            }), 500


        # =========================
        # READ GEMINI RESULT
        # =========================

        result =
            response.json()


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


        # Remove accidental punctuation
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
                "UNKNOWN AI INTENT:",
                intent,
                flush=True
            )

            intent =
                "NORMAL_MESSAGE"


        print(
            "AI INTENT:",
            intent,
            flush=True
        )


        # =========================
        # SEND RESULT BACK
        # =========================

        return jsonify({

            "status":
                "success",

            "message":
                message,

            "intent":
                intent

        })


    except Exception as e:

        print(
            "NEURON-X ERROR:",
            repr(e),
            flush=True
        )


        return jsonify({

            "error":
                "AI request failed",

            "details":
                str(e)

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
