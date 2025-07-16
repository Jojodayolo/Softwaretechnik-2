import os
import re
from OpenAIAPIConnector import OpenAIAPIConnector
from DeepSeekAPIConnector import DeepSeekAPIConnector
from webscraper import RecursiveWebScraper
from pathlib import Path
import datetime

# main.py
from TestUtils import (
    DirectorySetup,
    ImageRequirementProcessor,
    RequirementCombiner,
)

def main():
    
    # Ask user to choose the backend
    while True:
        choice = input("Which AI model do you want to use? [openai/deepseek]: ").strip().lower()
        if choice in ["openai", "deepseek"]:
            break
        print("Invalid input. Please type 'openai' or 'deepseek'.")

    use_openai = (choice == "openai")
    # Ask the user for the URL to be scraped
    start_url = input("Please enter the URL to be scraped: ").strip()

    if use_openai:
        bot = OpenAIAPIConnector(model="gpt-4o-mini")
    else:
        bot = DeepSeekAPIConnector(model="deepseek-chat")

    # Reset only if OpenAI is used and before calling it the first time.
    if isinstance(bot, OpenAIAPIConnector):
        bot.reset_state()
        print("🔁 OpenAI bot state reset.\n")
        bot = OpenAIAPIConnector(model="gpt-4o-mini")  # Re-instantiate after reset

    # Always reset image bot (always OpenAI)
    image_bot = OpenAIAPIConnector(model="gpt-4o-mini")
    image_bot.reset_state()
    image_bot = OpenAIAPIConnector(model="gpt-4o-mini")

    # Create unique repository folder
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_path = DirectorySetup.setup(f"run_output_{choice}_{timestamp}")
    _file_url = base_path / "last_url.txt"
    if os.path.exists(_file_url):
        os.remove(_file_url)
    with open(_file_url, "w", encoding="utf-8") as f:
        f.write(start_url)
    with open(_file_url, "r", encoding="utf-8") as f:
        start_url = f.read().strip()

    # Scrape website and save HTML files
    scraper = RecursiveWebScraper()
    scraper.start_scraping(start_url=start_url, locationPath=base_path)

    # Get requirements from image
    ImageRequirementProcessor.process(image_bot, base_path / "images")
    # Combine requirements with scraped pages
    RequirementCombiner.combine(
        requirements_dir=base_path / "image_requirements",
        scraped_dir=base_path / "scraped_pages",
        output_dir=base_path / "combined_requirements"
    )
    # Load requirements files from folder
    requirement_files = [f for f in os.listdir(base_path / "combined_requirements") if f.endswith(".txt")]

    for i, file_data in enumerate(requirement_files):

        print(f" Asking bot with {file_data}...")

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
        test_output_file = base_path / "tests" / Path(f"test_{file_data}").with_suffix(".py")
        with open(test_output_file, "w", encoding="utf-8") as f:
            f.write(test_code)

        print(f"💾 Test saved in: {test_output_file}\n")

    print("🎯 Processing completed.\n")

    # Only run tests if runTest=True was passed
    #if runTest:
    #    run_pytest_on_generated_tests(base_path)

if __name__ == "__main__":
    main()


