import json
from pathlib import Path
from playwright.async_api import async_playwright, Page


class PlaywrightCoverageManager:
    def __init__(self, base_url="http://localhost:8080", coverage_dir="coverage_steps"):
        self.base_url = base_url
        self.coverage_dir = Path(coverage_dir)
        self.coverage_dir.mkdir(exist_ok=True)
        self.playwright = None
        self.browser = None
        self.context = None

    async def setup(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()

    async def new_tracked_page(self, name: str) -> Page:
        page = await self.context.new_page()
        cdp = await self.context.new_cdp_session(page)

        await cdp.send("Profiler.enable")
        await cdp.send("Debugger.enable")
        await cdp.send("Profiler.startPreciseCoverage", {
            "callCount": True,
            "detailed": True
        })

        page._coverage_cdp = cdp
        page._coverage_name = name
        return page

    async def close_tracked_page(self, page: Page):
        cdp = getattr(page, "_coverage_cdp", None)
        name = getattr(page, "_coverage_name", "unnamed")

        if cdp:
            result = await cdp.send("Profiler.takePreciseCoverage")
            filtered = [entry for entry in result["result"] if entry.get("url") and entry["functions"]]

            with open(self.coverage_dir / f"{name}.json", "w", encoding="utf-8") as f:
                json.dump(filtered, f, indent=2)

            await cdp.send("Profiler.stopPreciseCoverage")
            await cdp.send("Profiler.disable")

        await page.close()

    async def teardown(self):
        await self.browser.close()
        await self.playwright.stop()
