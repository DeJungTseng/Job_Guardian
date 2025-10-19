from functools import wraps
from opentelemetry import trace

def trace_span(span_name: str):
    """裝飾器：為函式建立一個 trace span"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(span_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator
