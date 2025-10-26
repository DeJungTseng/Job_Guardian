# telemetry_server.py
from flask import Flask, Response
import os
import time

app = Flask(__name__)
LOG_PATH = "telemetry/mcp-activity.log"

def stream_logs():
    """持續監看 log 檔，並以 SSE 推送新內容"""
    if not os.path.exists(LOG_PATH):
        yield "data: No telemetry data yet.\n\n"
        return

    with open(LOG_PATH, "r", encoding="utf-8") as f:
        # 移到檔案結尾，避免重播舊紀錄
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if line:
                # 使用 Server-Sent Events 格式傳送
                yield f"data: {line}\n\n"
            else:
                time.sleep(1)  # 每秒檢查一次新內容

@app.route("/telemetry/stream")
def telemetry_stream():
    """SSE 即時串流端點"""
    return Response(stream_logs(), mimetype="text/event-stream")

@app.route("/telemetry/recent")
def recent_snapshot():
    """備用靜態模式（iframe 初始載入）"""
    if not os.path.exists(LOG_PATH):
        return Response("No telemetry data yet.", mimetype="text/plain")

    with open(LOG_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return Response("".join(lines[-30:]), mimetype="text/plain")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, threaded=True)
