import asyncio
import os

from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner

from app import app

load_dotenv()

runner = InMemoryRunner(app=app)


async def main() -> None:
    prompt = os.getenv(
        "PROMPT", "Research and write a brief report on WebAssembly."
    )
    response = await runner.run_debug(prompt)
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
