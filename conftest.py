import pytest_asyncio
import os
from PlaywrightCoverageManager import PlaywrightCoverageManager  # ggf. anpassen

#pytest --html=report.html

@pytest_asyncio.fixture(scope="function")
async def coverage_manager():
    _file_url = "run_output/last_url.txt"
    if os.path.exists(_file_url):
        with open(_file_url, "r", encoding="utf-8") as f:
            base_url = f.read().strip()
    manager = PlaywrightCoverageManager(base_url=base_url)
    await manager.setup()
    yield manager
    await manager.teardown()
