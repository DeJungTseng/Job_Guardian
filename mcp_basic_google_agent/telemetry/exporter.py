import os
import json
from datetime import datetime
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from rich.console import Console
from rich.syntax import Syntax

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


class MCPActivityExporter(SpanExporter):
    """
    專為 Job Guardian 設計的 Telemetry Exporter：
    - 只輸出與 MCP 工具互動相關的 spans
    - 簡化時間欄位（不輸出 start_time / end_time）
    - 美化顯示格式類似 log stream
    - 可在 Render 部署環境保持 Rich 高亮輸出
    """

    def __init__(self, filepath="mcp-activity.log"):
        self.filepath = filepath
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        console.print(f"[green][otel][/green] Logging MCP activities to [bold]{self.filepath}[/bold]")

    def export(self, spans):
        log_lines = []
        for span in spans:
            name = span.name.lower()

            # 🧩 僅關心 MCP 過程（過濾掉初始化、load_servers 等）
            if not any(key in name for key in [
                "receive_prompt",
                "tool_call",
                "send_request",
                "execute_llm_generation",
                "format_response",
                "mcpaggregator",
                "mcp_agentclientsession"
            ]):
                continue

            # 提取基本欄位
            attrs = _safe_serialize(span.attributes)
            ctx = span.context

            # 🧠 Level 判定
            if "error" in name:
                level = "ERROR"
            elif "receive" in name:
                level = "INFO"
            elif "call" in name or "send" in name:
                level = "DEBUG"
            else:
                level = "INFO"

            # 📦 組出 log prefix
            prefix = f"[{level}] {datetime.utcnow().isoformat(timespec='seconds')} {span.name}"

            # 🧾 美化 attributes
            pretty_json = json.dumps(
                {"data": attrs},
                indent=2,
                ensure_ascii=False
            )
            syntax = Syntax(pretty_json, "json", theme="ansi_dark", word_wrap=True)

            # ✅ 終端輸出（Render log 也支援 Rich）
            console.print(prefix)
            console.print(syntax)

            # ✅ 寫入檔案（純文字方便 iframe 讀取）
            log_entry = f"{prefix}\n{pretty_json}\n"
            log_lines.append(log_entry)

        # 附加寫入檔案
        if log_lines:
            with open(self.filepath, "a", encoding="utf-8") as f:
                for line in log_lines:
                    f.write(line + "\n")

        return SpanExportResult.SUCCESS


def get_exporter():
    """使用自訂的 MCPActivityExporter"""
    print("[otel] Using MCP Activity Exporter (human-readable logs)")
    return MCPActivityExporter(filepath="telemetry/mcp-activity.log")
