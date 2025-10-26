# telemetry/tracing.py
from functools import wraps
from opentelemetry import trace

def trace_span(span_name: str):
    """
    裝飾器：建立並記錄一個 span。
    若被裝飾的函式有回傳值或引數，將一併記入 attributes。
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(span_name) as span:
                # 記錄函式名稱與引數摘要
                span.set_attribute("function.name", func.__name__)
                if args:
                    span.set_attribute("args", str(args[:3]))  # 避免太長
                if kwargs:
                    span.set_attribute("kwargs", str({k: v for k, v in kwargs.items()}))
                try:
                    result = func(*args, **kwargs)
                    # 若是 coroutine，交由 event loop 控制
                    if hasattr(result, "__await__"):
                        async def _async_wrapper():
                            res = await result
                            span.set_attribute("result.preview", str(res)[:200])
                            return res
                        return _async_wrapper()
                    else:
                        span.set_attribute("result.preview", str(result)[:200])
                        return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_attribute("error", str(e))
                    raise
        return wrapper
    return decorator
