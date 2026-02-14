import asyncio

from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner

from app import app

load_dotenv()

runner = InMemoryRunner(app=app)


async def main() -> None:
    response = await runner.run_debug("Hello from skeleton phase.")
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
