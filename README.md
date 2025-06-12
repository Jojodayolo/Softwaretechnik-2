# 🧪 AI-Powered Web Test Generator

This project automates the process of scraping web pages, generating Playwright test cases using OpenAI's GPT-4o model, and running those tests using `pytest`. It is designed to streamline the testing pipeline for dynamic websites with minimal human intervention.

---

## 🚀 Features

- Recursively scrape HTML pages from a given URL
- Automatically generate test code using OpenAI
- Syntax and test validity checks before execution
- Run tests using `pytest` and store structured results
- Fully modular architecture with reset/cleanup logic

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

## 🛠️ To-Do List (Planned Improvements)

- [ ] **Command-line input**: Prompt user for repository or folder name to dynamically set up the `run_output/` path.
- [ ] **Test filtering**: Remove non-runnable test files (e.g., syntax errors, not collected by pytest).
- [ ] **Test execution**: Automatically execute tests with `pytest`, capture logs, and store results in `test_results/`.
- [ ] **Report Generation**: Create a readable summary (e.g. HTML or Markdown) of test outcomes.
- [ ] **Folder relocation**: Move the `run_output` folder to a new target directory after processing.
- [ ] **Reset behavior**: Clean up all generated files at the end of each run to allow for fresh runs.

---

## 🔧 Requirements

- Python 3.8+
- `pytest`
- `playwright`
- `openai`
- Google Chrome (for headless scraping/debugging)
- Chrome must be run with:
.\chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\temp-chrome"

Install dependencies:

```bash
pip install -r requirements.txt
```
🧪 How to Use
```bash
python main.py
```
