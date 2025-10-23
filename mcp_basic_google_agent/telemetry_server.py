# telemetry_server.py
from flask import Flask, jsonify
import json, os

app = Flask(__name__)

@app.route("/telemetry/recent")
def recent_trace():
    path = "mcp-agent-trace.jsonl"
    if not os.path.exists(path):
        return jsonify({"message": "No traces yet."})

    with open(path, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]

    # 取最新 10 條
    return jsonify(lines[-10:])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
