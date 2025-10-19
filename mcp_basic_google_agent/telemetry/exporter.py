import os
from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter


def get_exporter():
    """根據環境變數決定 exporter"""
    mode = os.getenv("OTEL_EXPORT_MODE", "console").lower()
    if mode == "otlp":
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/traces")
        print(f"[otel] Using OTLP exporter -> {endpoint}")
        return OTLPSpanExporter(endpoint=endpoint)
    else:
        print("[otel] Using Console exporter")
        return ConsoleSpanExporter()
