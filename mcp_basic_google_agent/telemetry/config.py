from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from telemetry.exporter import get_exporter


def setup_telemetry(service_name: str = "mcp_basic_google_agent"):
    """初始化 OpenTelemetry Provider 與 Exporter"""
    provider = TracerProvider()
    exporter = get_exporter()  # 可切換 Console / OTLP
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    return trace.get_tracer(service_name)
