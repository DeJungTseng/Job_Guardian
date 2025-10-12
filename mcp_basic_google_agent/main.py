import asyncio
import sys, os
import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from pydantic import BaseModel
from mcp_agent.app import MCPApp
from mcp_agent.config import (
    GoogleSettings,
    Settings,
    LoggerSettings,
    MCPSettings,
    MCPServerSettings,
)
from mcp_agent.agents.agent import Agent
from mcp_agent.workflows.llm.augmented_llm_google import GoogleAugmentedLLM

# === Data Model ===
class Essay(BaseModel):
    title: str
    body: str
    conclusion: str


# === Global Settings ===
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

settings = Settings(
    execution_engine="asyncio",
    logger=LoggerSettings(type="file", level="debug"),
    mcp=MCPSettings(
        servers={
            "job_guardian": MCPServerSettings(
                command="python",
                args=[os.path.join(BASE_DIR, "mcp_server", "server.py")],
                transport="stdio",
            ),
        }
    ),
    google=GoogleSettings(default_model="gemini-2.0-flash"),
)

# === FastAPI 初始化 ===
app = FastAPI(title="Job Guardian API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ 上線時可改成你的 render 前端網域
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Agent 狀態 ===
mcp_app = MCPApp(name="job_guardian_agent", settings=settings)
agent_state = {"ready": False, "agent": None, "llm": None, "logs": []}


# === 啟動事件 ===
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(start_agent())  # 背景啟動
    agent_state["logs"].append("🚀 Agent startup task scheduled.")


async def start_agent():
    async with mcp_app.run() as agent_app:
        job_guardian_agent = Agent(
            name="job_guardian",
            instruction=(
                "You are Job Guardian, an intelligent assistant that can use three tools:\n"
                "1️⃣ esg_hr → 查詢公司 ESG 人力發展資料（薪資、福利、女性主管比例）\n"
                "2️⃣ labor_violations → 查詢勞動部違反勞基法紀錄\n"
                "3️⃣ ge_work_equality_violations → 查詢違反性別工作平等法紀錄\n\n"
                "根據使用者輸入內容（公司名稱或自然語句）自動選擇正確的 tool 並回傳結果。"
            ),
            server_names=["job_guardian"],
        )

        async with job_guardian_agent:
            llm = await job_guardian_agent.attach_llm(GoogleAugmentedLLM)
            agent_state.update({
                "ready": True,
                "agent": job_guardian_agent,
                "llm": llm
            })
            agent_state["logs"].append("✅ Job Guardian agent initialized and ready.")

            # 保持常駐
            while True:
                await asyncio.sleep(60)


# === API ===
@app.get("/")
async def root():
    return {"status": "running", "agent_ready": agent_state["ready"]}


@app.get("/logs")
async def logs():
    """顯示 agent 狀態（給 telemetry iframe 用）"""
    return PlainTextResponse("\n".join(agent_state["logs"][-50:]))


@app.post("/query")
async def query(request: Request):
    """Assistant-UI 呼叫的主要 API"""
    if not agent_state["ready"]:
        return JSONResponse({"error": "Agent 尚未初始化完成"}, status_code=503)

    data = await request.json()
    user_query = data.get("query", "").strip()
    if not user_query:
        return JSONResponse({"error": "請輸入查詢內容"}, status_code=400)

    llm = agent_state["llm"]
    start = time.time()

    try:
        # 1️⃣ LLM 判斷應用的 tool 並查詢
        result = await llm.generate_str(
            message=f"根據輸入內容「{user_query}」，請查詢對應的公司紀錄。"
        )

        # 2️⃣ 生成結構化摘要
        structured = await llm.generate_structured(
            message=f"根據輸入內容「{user_query}」，請總結這家公司的狀況（以 Essay 格式回傳）。",
            response_model=Essay,
        )

        elapsed = time.time() - start
        msg = f"✅ 查詢完成 ({elapsed:.2f}s)：{user_query}"
        agent_state["logs"].append(msg)

        return {
            "query": user_query,
            "result": result,
            "structured": structured.model_dump(),
            "elapsed": elapsed,
        }

    except Exception as e:
        err_msg = f"❌ 查詢失敗: {e}"
        agent_state["logs"].append(err_msg)
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
