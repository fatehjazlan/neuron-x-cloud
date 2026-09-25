from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return "NEURON-X CLOUD ONLINE"

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()

    if not data or "message" not in data:
        return jsonify({"error": "No message received"}), 400

    message = data["message"]

    return jsonify({
        "status": "success",
        "message_received": message
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
