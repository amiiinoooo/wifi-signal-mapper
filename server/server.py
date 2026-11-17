from flask import Flask, request, jsonify

app = Flask(__name__)

# store data in memory
database = {}

# 🔥 NEW FLAG
updated = False


@app.route("/", methods=["GET"])
def home():
    return "Server is running"


@app.route("/upload", methods=["POST"])
def upload():
    global updated
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON received"}), 400

        room = data.get("room")
        networks = data.get("networks")

        if not room or not networks:
            return jsonify({"error": "Invalid data"}), 400

        # store data
        database[room] = networks

        # 🔥 MARK UPDATED
        updated = True

        print("\n--- NEW DATA RECEIVED ---")
        print(f"Room: {room}")

        for net in networks:
            print(f"{net['ssid']} → {net['rssi']} dBm")

        print("-------------------------\n")

        return jsonify({"status": "success"}), 200

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": "Server error"}), 500


@app.route("/data", methods=["GET"])
def get_data():
    return jsonify(database)


# 🔥 NEW STATUS ENDPOINT
@app.route("/status", methods=["GET"])
def status():
    return jsonify({"updated": updated})


# 🔥 RESET FLAG AFTER UI FETCH
@app.route("/reset", methods=["POST"])
def reset():
    global updated
    updated = False
    return "reset", 200


@app.route("/clear", methods=["POST"])
def clear():
    database.clear()
    return "cleared", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)