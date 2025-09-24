import json
import server   # 直接 import 你寫的 server.py，裡面的 @mcp.tool 會被註冊到 server.mcp

def run_tool(name, *args, **kwargs):
    tool_func = server.mcp.tool.get(name)
    if not tool_func:
        print(f"❌ Tool {name} not found")
        return
    # call_sync 直接呼叫 tool
    result = server.mcp.call_sync(name, *args, **kwargs)
    print(f"=== {name} ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print()

if __name__ == "__main__":
    # 測試三個工具
    run_tool("esg_hr", company="台灣積體電路製造股份有限公司", year=2023)
    run_tool("labor_violations", company="台灣積體電路製造股份有限公司", since_year=2022)
    run_tool("ge_work_equality_violations", company="台灣積體電路製造股份有限公司", since_year=2022)
