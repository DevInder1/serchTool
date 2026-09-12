import asyncio

import store
from watcher import check_all


async def main() -> None:
    store.init()
    checked = await check_all()
    print(f"Checked {checked} watch(es).")


if __name__ == "__main__":
    asyncio.run(main())
