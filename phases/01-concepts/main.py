import asyncio

from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner

from agent import app

load_dotenv()

runner = InMemoryRunner(app=app)


async def main() -> None:
    # run_debug requires ADK Python v1.18+
    response = await runner.run_debug(
        "Hello ADK. Remember this topic: multi-agent orchestration."
    )
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
