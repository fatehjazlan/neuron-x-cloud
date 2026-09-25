from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>NEURON-X Cloud</title>
    </head>

    <body style="font-family:Arial; text-align:center; padding:40px;">

        <h1>NEURON-X CLOUD</h1>
        <p>Cloud Analysis Test</p>

        <input id="message"
               type="text"
               placeholder="Type message..."
               style="padding:12px; width:80%; max-width:400px;">

        <br><br>

        <button onclick="analyze()"
                style="padding:12px 25px;">
            ANALYZE
        </button>

        <h3>Cloud Result:</h3>
        <p id="result">Waiting for message...</p>

        <script>
        async function analyze() {

            const message =
                document.getElementById("message").value;

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

            document.getElementById("result").innerText =
                "Received: " + data.message_received;
        }
        </script>

    </body>
    </html>
    """


@app.route("/analyze", methods=["POST"])
def analyze():

    data = request.get_json()

    if not data or "message" not in data:
        return jsonify({
            "error": "No message received"
        }), 400

    message = data["message"]

    return jsonify({
        "status": "success",
        "message_received": message
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
