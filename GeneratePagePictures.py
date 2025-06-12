from playwright.sync_api import sync_playwright
import os

def take_screenshots(urls, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for url in urls:
            try:
                page.goto(url, timeout=15000)
                # Clean the filename to avoid invalid characters
                filename = url.replace("http://", "").replace("https://", "").replace("/", "_") + ".png"
                path = os.path.join(output_dir, filename)
                page.screenshot(path=path, full_page=True)
                print(f"✅ Saved screenshot: {path}")
            except Exception as e:
                print(f"❌ Failed to load {url}: {e}")

        browser.close()
