# 🧪 AI-Powered Web Test Generator

This project automates the process of scraping web pages, generating Playwright test cases using OpenAI's GPT-4o model and others, and running those tests with `pytest`. It is designed to streamline the testing pipeline for dynamic websites with minimal human intervention.

---

## 🚀 Features

- **Recursive Web Scraping:** Automatically downloads all HTML pages from a given website.
- **AI Test Generation:** Uses OpenAI GPT-4o to generate Playwright-based Python test cases from requirements and scraped content.
- **Image-to-Requirement Extraction:** Extracts requirements from screenshots or images using AI.
- **Test Validation:** Checks syntax and test validity before running.
- **Automated Test Execution:** Runs generated tests with `pytest` and stores results.
- **Modular & Extensible:** Clean, class-based architecture for easy extension and maintenance.
- **Reset & Cleanup Logic:** Optional state reset and output cleanup for reproducible runs.

---

## 📂 Folder Structure

```
run_output/
├── scraped_pages/ # Contains HTML files scraped from the website
├── tests/ # Contains generated test files (e.g. test_playwright_0.py)
├── test_results/ # Stores output and reports from pytest runs
└── code/ # Intermediate code prompt files used to query OpenAI
└── images/ #image of each scraped page
```

---

## 🛠️ Planned Improvements

- [ ] **Report Generation:** Create a readable summary (HTML/Markdown) of test outcomes.
- [ ] **Folder Relocation:** Move the `run_output` folder to a new target directory after processing.
- [ ] **Better Error Handling:** More robust error and retry logic for scraping and AI calls.
- [ ] **Parallel Test Execution:** Speed up test runs for large sites.

---

## 🔧 Requirements

- Python 3.8+
- `pytest`
- `playwright`
- `openai`
- Google Chrome (for headless scraping/debugging)

**Chrome must be run with:**
```sh
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\temp-chrome"
```

**Install dependencies:**
```sh
pip install -r requirements.txt
```

---

## 🧪 How to Use

1. **Start Chrome in remote debugging mode** (see above).
2. **Run the main script:**
    ```sh
    python main.py
    ```
3. **Follow the prompts** to enter the URL to be scraped.
4. **Generated tests and results** will appear in the `run_output/` folder.

---

## 🤖 Architecture Overview

- **TestUtils:** Utilities for test validation and filename normalization.
- **RequirementCombiner:** Combines requirements and scraped HTML for AI prompts.
- **ImageRequirementProcessor:** Extracts requirements from images/screenshots.
- **DirectorySetup:** Handles output folder creation.
- **RecursiveWebScraper:** Handles recursive scraping of the target website.
- **OpenAIAPIConnector:** Handles communication with the OpenAI API.

---

## 📣 Contributing

Contributions, issues, and feature requests are welcome! Please open an issue or submit a pull request.

---


