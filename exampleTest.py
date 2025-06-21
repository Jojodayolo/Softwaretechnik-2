import pytest
from playwright.async_api import Page


@pytest.mark.asyncio
class ExampleTest:
    async def test_submit_safe_content(self, coverage_manager):
        page: Page = await coverage_manager.new_tracked_page("submit_safe_content")
        await page.goto(f"{coverage_manager.base_url}/ai/openai-moderation")

        await page.fill('textarea[name="inputText"]', "This is a safe content.")
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(3000)

        await coverage_manager.close_tracked_page(page)

    async def test_submit_harmful_content(self, coverage_manager):
        page: Page = await coverage_manager.new_tracked_page("submit_harmful_content")
        await page.goto(f"{coverage_manager.base_url}/ai/openai-moderation")

        await page.fill('textarea[name="inputText"]', "This is a test input with harmful content.")
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(3000)

        await coverage_manager.close_tracked_page(page)

    async def test_page_load(self, coverage_manager):
        page: Page = await coverage_manager.new_tracked_page("openai_moderation_load")
        await page.goto(f"{coverage_manager.base_url}/ai/openai-moderation")
        assert "Moderation" in await page.title()
        await page.wait_for_timeout(2000)
        await coverage_manager.close_tracked_page(page)
