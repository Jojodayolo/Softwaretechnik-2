# conftest.py
import pytest_asyncio
from PlaywrightCoverageManager import PlaywrightCoverageManager  # ggf. anpassen


@pytest_asyncio.fixture(scope="function")
async def coverage_manager():
    manager = PlaywrightCoverageManager()
    await manager.setup()
    yield manager
    await manager.teardown()
