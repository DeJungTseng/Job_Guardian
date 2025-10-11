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
                "根據使用者輸入內容（公司名稱或自然語句）自動選擇正確的 tool 並回傳結果。\n"
                "若查詢公司資料，優先使用 esg_hr。\n"
                "若提到『違法』、『罰鍰』、『違反勞基法』等字眼，使用 labor_violations。\n"
                "若提到『性別平等』、『性騷擾』、『平權』等字眼，使用 ge_work_equality_violations。\n"
                "若同時提到「違法」與「性別」，請優先使用 ge_work_equality_violations。\n"
                "若句子中僅有公司名稱，請使用 esg_hr。"
            ),
            server_names=["job_guardian"],
        )

        async with job_guardian_agent:
            llm = await job_guardian_agent.attach_llm(GoogleAugmentedLLM)

            print("🧭 Job Guardian 啟動成功！輸入公司名稱或查詢句子（Ctrl+C 或輸入 exit 離開）\n")

            # 🔁 多輪查詢迴圈
            while True:
                try:
                    user_query = input("請輸入查詢內容: ").strip()
                except KeyboardInterrupt:
                    print("\n👋 偵測到 Ctrl+C，中止查詢並結束程式。")
                    break

                if user_query.lower() in {"exit", "quit", "q"}:
                    print("👋 結束查詢，感謝使用 Job Guardian！")
                    break

                start = time.time()
                try:
                    result = await llm.generate_str(
                        message=f"根據輸入內容「{user_query}」，請查詢對應的公司紀錄。"
                    )

                    print("\n🪄 LLM 自動推理結果：")
                    print(result)

                    structured = await llm.generate_structured(
                        message=f"根據輸入內容「{user_query}」，請總結這家公司的狀況（以 Essay 格式回傳）。",
                        response_model=Essay,
                    )

                    print("\n📄 結構化輸出：")
                    print(structured)

                except KeyboardInterrupt:
                    print("\n⚠️ 偵測到 Ctrl+C，中止本輪查詢。\n")
                    continue
                except Exception as e:
                    logger.error(f"查詢失敗：{e}")
                    print(f"⚠️ 查詢時發生錯誤：{e}")

                end = time.time()
                print(f"\n⏱️ 本次查詢耗時：{end - start:.2f}s\n{'-'*60}\n")


if __name__ == "__main__":
    try:
        asyncio.run(example_usage())
    except KeyboardInterrupt:
        print("\n👋 程式已安全中止，再見！")
