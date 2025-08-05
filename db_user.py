from src.project_context.postgres.service import test

import asyncio


async def main():
    await test()


if __name__ == "__main__":
    asyncio.run(main())
    