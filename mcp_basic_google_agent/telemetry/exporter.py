import os
import json
from datetime import datetime
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

# ✅ rich 支援
from rich.console import Console
from rich.json import JSON

console = Console()


def _safe_serialize(obj):
    """將不可序列化的物件安全轉換為字串"""
    try:
        json.dumps(obj)
        return obj
    except TypeError:
        if isinstance(obj, dict):
            return {str(k): _safe_serialize(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple, set)):
            return [_safe_serialize(v) for v in obj]
        else:
            return str(obj)


class RichConsoleExporter(SpanExporter):
    """使用 rich 彩色輸出 span JSON 並同步寫入檔案"""

    def __init__(self, filepath="mcp-agent-trace.jsonl"):
        self.filepath = filepath
        # 確保目錄存在
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        console.print(f"[green][otel][/green] Writing traces to [bold]{self.filepath}[/bold]")

    def export(self, spans):
        lines = []
        for span in spans:
            data = {
                "name": span.name,
                "context": {
                    "trace_id": str(span.context.trace_id),
                    "span_id": str(span.context.span_id),
                },
                "start_time": span.start_time,
                "end_time": span.end_time,
                "status": str(span.status.status_code),
                "attributes": _safe_serialize(span.attributes),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

            # ✅ 彩色輸出
            console.print(JSON.from_data(data))

            # ✅ 寫入 JSONL
            lines.append(json.dumps(data, ensure_ascii=False))

        # 追加寫入
        with open(self.filepath, "a", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")

        return SpanExportResult.SUCCESS


def get_exporter():
    """根據環境變數決定 exporter"""
    mode = os.getenv("OTEL_EXPORT_MODE", "console").lower()

    if mode == "otlp":
        endpoint = os.getenv(
            "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/traces"
        )
        print(f"[otel] Using OTLP exporter -> {endpoint}")
        return OTLPSpanExporter(endpoint=endpoint)

    elif mode == "rich":
        print("[otel] Using Rich Console exporter + JSONL trace output")
        return RichConsoleExporter(filepath="mcp-agent-trace.jsonl")

    else:
        print("[otel] Using Plain Console exporter")
        return ConsoleSpanExporter()
