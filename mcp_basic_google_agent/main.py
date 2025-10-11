import asyncio
import time
import sys, os
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


class Essay(BaseModel):
    title: str
    body: str
    conclusion: str


# 回到專案根目錄
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

app = MCPApp(name="mcp_basic_agent", settings=settings)


async def example_usage():
    async with app.run() as agent_app:
        logger = agent_app.logger
        context = agent_app.context

        job_guardian_agent = Agent(
            name="job_guardian",
            instruction=(
                "You are Job Guardian, an intelligent assistant that can use three tools:\n"
                "1️⃣ esg_hr → 查詢公司 ESG 人力發展資料（薪資、福利、女性主管比例）\n"
                "2️⃣ labor_violations → 查詢勞動部違反勞基法紀錄\n"
                "3️⃣ ge_work_equality_violations → 查詢違反性別工作平等法紀錄\n\n"
                "當使用者輸入公司名稱或自然語句時，根據需求自動選擇正確的 tool 並回傳對應結果。\n"
                "若查詢公司資料，優先使用 esg_hr。\n"
                "若提到『違法』、『罰鍰』、『違反勞基法』等字眼，使用 labor_violations。\n"
                "若提到『性別平等』、『性騷擾』、『平權』等字眼，使用 ge_work_equality_violations。\n"
                "若查詢句中同時提到「違法」與「性別」，請優先使用 ge_work_equality_violations。\n"
                "若句子中僅有公司名稱，請使用 esg_hr。\n"

            ),
            server_names=["job_guardian"],
        )

        async with job_guardian_agent:
            llm = await job_guardian_agent.attach_llm(GoogleAugmentedLLM)

            # 🧠 讓使用者輸入查詢
            user_query = input("請輸入查詢內容（公司名稱或自然語句）: ")

            # 💬 交給 LLM 自動決策呼叫 tool
            result = await llm.generate_str(
                message=f"根據輸入內容「{user_query}」，請查詢對應的公司紀錄。"
            )

            print("\n🪄 LLM 自動推理結果：")
            print(result)

            # 💡 也可結構化輸出 (optional)
            structured = await llm.generate_structured(
                message=f"根據輸入內容「{user_query}」，請總結這家公司的狀況（以 Essay 格式回傳）。",
                response_model=Essay,
            )

            print("\n📄 結構化輸出：")
            print(structured)


if __name__ == "__main__":
    start = time.time()
    asyncio.run(example_usage())
    end = time.time()
    print(f"\nTotal run time: {end - start:.2f}s")
