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
                transport="stdio"
            ),
        }
    ),
    google=GoogleSettings(default_model="gemini-2.0-flash"),
)

# Settings can either be specified programmatically,
# or loaded from mcp_agent.config.yaml/mcp_agent.secrets.yaml
app = MCPApp(
    name="mcp_basic_agent",
    settings=settings
)


async def example_usage():
    async with app.run() as agent_app:
        logger = agent_app.logger
        context = agent_app.context

        logger.info("Current config:", data=context.config.model_dump())

        job_guardian_agent = Agent(
            name="job_guardian",
            instruction="""You are an agent with the ability to fetch URLs. Your job is to identify 
            the closest match to a user's request, make the appropriate tool calls, 
            and return the URI and CONTENTS of the closest match.""",
            server_names=["job_guardian"],
        )

        async with job_guardian_agent:
            logger.info("job_guardian: Connected to server, calling list_tools...")
            result = await job_guardian_agent.list_tools()
            logger.info("Tools available:", data=result.model_dump())

            llm = await job_guardian_agent.attach_llm(GoogleAugmentedLLM)

            result = await llm.generate_str(
                message="Print the first 2 paragraphs of https://modelcontextprotocol.io/introduction",
            )
            logger.info(f"First 2 paragraphs of Model Context Protocol docs: {result}")

            result = await llm.generate_structured(
                message="Create a short essay using the first 2 paragraphs.",
                response_model=Essay,
            )
            logger.info(f"Structured paragraphs: {result}")


if __name__ == "__main__":
    start = time.time()
    asyncio.run(example_usage())
    end = time.time()
    t = end - start

    print(f"Total run time: {t:.2f}s")
