# telemetry_server.py
from flask import Flask, Response
import os

app = Flask(__name__)

@app.route("/telemetry/recent")
def recent_trace():
    """回傳最近的 MCP 活動紀錄（給 iframe 使用）"""
    path = "telemetry/mcp-activity.log"
    if not os.path.exists(path):
        return Response("No telemetry data yet.", mimetype="text/plain")

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 取最新 30 行
    content = "".join(lines[-30:])
    return Response(content, mimetype="text/plain")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
