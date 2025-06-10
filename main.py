import os
import re
from OpenAIAPIConnector import OpenAIAPIConnector
from ResponseParser import ResponseParser
from FileParser import FileParser, FileReader
from RepositoryCloner import RepositoryCloner
from webscraper import RecursiveWebScraper

def main(reset=True, max_files=38):
    # Initialisiere OpenAI-Connector
    bot = OpenAIAPIConnector(model="gpt-4o-mini")
    
    if reset:
        bot.reset_state()
        print("🔁 Bot-Zustand zurückgesetzt.\n")
        bot = OpenAIAPIConnector(model="gpt-4o-mini")  # Neu instanziieren nach Reset

    # Klone Repository und speichere gesammelten Code
    #cloner = RepositoryCloner()
    #repo_path = cloner.clone_repo("https://github.com/saucelabs/the-internet.git")
    #cloner.process_repo(repo_path, "repository.txt")
    #print("📁 Repository geklont und verarbeitet.\n")
    scraper = RecursiveWebScraper()
    #scraper.start_scraping(start_url="")


    # Lade HTML-Dateien aus Ordner
    html_parser = FileParser(folder_path="./scraped_pages")
    html_files = html_parser.read_all_files()

    for i, file_data in enumerate(html_files[:max_files]):
        html_content = file_data['html']
        filename = file_data['filename']
        url = f"/{filename}"  # relative TEST_URL

        # Speichere HTML-Inhalt und zugehörige URL in Textdatei
        input_file = f"code{i}.txt"
        with open(input_file, "w", encoding="utf-8") as f:
            f.write(html_content + f"\n\nTEST_URL={url}")

        print(f"[{i}] Frage OpenAI mit {filename}...")

        try:
            response = bot.ask_with_file(input_file)
        except Exception as e:
            print(f"❌ Fehler bei Datei {filename}: {e}")
            continue

        if not response.strip():
            print(f"⚠️ Keine Antwort erhalten für Datei {filename}.")
            continue

        print(f"✅ Antwort erhalten für Datei {filename}.")

        # Extrahiere Python-Code aus Codeblöcken
        code_blocks = re.findall(r"```python(.*?)```", response, re.DOTALL)
        test_code = "\n\n".join(cb.strip() for cb in code_blocks) if code_blocks else response.strip()

        # Speichere generierten Testcode in .py-Datei
        test_output_file = f"test_playwright_{i}.py"
        with open(test_output_file, "w", encoding="utf-8") as f:
            f.write(test_code)

        print(f"💾 Test gespeichert in: {test_output_file}\n")

    print("🎯 Verarbeitung abgeschlossen.\n")

    # Optionaler Reset am Ende zur Bereinigung
    if reset:
        bot.reset_state()
        print("🧹 Bot-Zustand am Ende zurückgesetzt.")


if __name__ == "__main__":
    main(reset=True, max_files=4)
