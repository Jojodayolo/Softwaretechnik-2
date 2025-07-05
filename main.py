import os
import re
from OpenAIAPIConnector import OpenAIAPIConnector
from webscraper import RecursiveWebScraper
from pathlib import Path
from TestUtils import setup_directories, process_image_folder, combine_requirements_with_scraped_pages, run_pytest_on_generated_tests



# .\chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\\temp-chrome"

def main(reset=True, runTest=False):
    # Ask the user for the URL to be scraped
    start_url = input("Please enter the URL to be scraped: ").strip()
    _file_url = "run_output/last_url.txt"
    if os.path.exists(_file_url):
        os.remove(_file_url)
    with open(_file_url, "w", encoding="utf-8") as f:
        f.write(start_url)
    with open(_file_url, "r", encoding="utf-8") as f:
        start_url = f.read().strip()

    # Initialize OpenAI connector
    bot = OpenAIAPIConnector(model="gpt-4o-mini")

    if reset:
        bot.reset_state()
        print("🔁 Bot state reset.\n")
        bot = OpenAIAPIConnector(model="gpt-4o-mini")  # Re-instantiate after reset

    # Create repository folder
    base_path = setup_directories("run_output")

    # Scrape website and save HTML files
    scraper = RecursiveWebScraper()
    scraper.start_scraping(start_url=start_url, locationPath=base_path)

    # Get requirements from image
    process_image_folder(bot, base_path / "images")
    # Combine requirements with scraped pages
    combine_requirements_with_scraped_pages(
        requirements_dir=base_path / "image_requirements",
        scraped_dir=base_path / "scraped_pages",
        output_dir=base_path / "combined_requirements"
    )
    # Load requirements files from folder
    requirement_files = [f for f in os.listdir(base_path / "combined_requirements") if f.endswith(".txt")]
    max_files = len(requirement_files)  # Automatically determine number

    for i, file_data in enumerate(requirement_files):

        print(f" Asking OpenAI with {file_data}...")

        try:
            response = bot.ask_with_file(base_path / "combined_requirements" / file_data)
        except Exception as e:
            print(f"❌ Error with file {file_data}: {e}")
            continue

        if not response.strip():
            print(f"⚠️ No response received for file {file_data}.")
            continue

        print(f"✅ Response received for file {file_data}.")

        # Extract Python code from code blocks
        code_blocks = re.findall(r"```python(.*?)```", response, re.DOTALL)
        test_code = "\n\n".join(cb.strip() for cb in code_blocks) if code_blocks else response.strip()

        # Save generated test code in .py file
        test_output_file = base_path / "tests" / Path(file_data).with_suffix(".py")
        with open(test_output_file, "w", encoding="utf-8") as f:
            f.write(test_code)

        print(f"💾 Test saved in: {test_output_file}\n")

    print("🎯 Processing completed.\n")

    # Only run tests if runTest=True was passed
    if runTest:
        run_pytest_on_generated_tests(base_path)

    # Optional reset at the end for cleanup
    if reset:
        bot.reset_state()
        print("🧹 Bot state reset at the end.")
    #shutil.rmtree(base_path)
    #print("🗑️ Folder 'run_output' has been deleted.")

if __name__ == "__main__":
    main(reset=True)


