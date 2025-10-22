import os
import json
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
    """使用 rich 彩色輸出 span JSON"""

    def export(self, spans):
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
                # ✅ 安全轉換 attributes
                "attributes": _safe_serialize(span.attributes),
            }
            console.print(JSON.from_data(data))
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
        print("[otel] Using Rich Console exporter")
        return RichConsoleExporter()

    else:
        print("[otel] Using Plain Console exporter")
        return ConsoleSpanExporter()
