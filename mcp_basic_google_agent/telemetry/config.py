from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from telemetry.exporter import get_exporter


def setup_telemetry(service_name: str = "mcp_basic_google_agent"):
    """初始化 OpenTelemetry Provider 與 Exporter"""
    # 建立 provider
    provider = TracerProvider()
    
    # 使用我們的 get_exporter() 取得正確輸出端
    exporter = get_exporter()
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)

    # 設定全域 tracer provider
    trace.set_tracer_provider(provider)

    # 回傳 Tracer
    return trace.get_tracer(service_name)
