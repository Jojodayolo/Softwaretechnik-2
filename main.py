import os
import re
from OpenAIAPIConnector import OpenAIAPIConnector
from ResponseParser import ResponseParser
from FileParser import FileParser, FileReader
from RepositoryCloner import RepositoryCloner
from webscraper import RecursiveWebScraper

# .\chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\\temp-chrome"

def main(reset=True):
    # TODO
    # repository name aus konsole lesen für Ordnerstruktur
    # Ordnerstruktur erstellen: scraped_pages && tests && test results erzeugen
    # wenn ordnerstruktur -> code so anpassen, dass dateien dementsprechen verarbeitet werden können

    # test_playwright_0 etc einmal drüber iterieren und nicht lauffähige tests löschen
    # nach erstellen der tests -> pytest ausführen mit entsprechendem log level -> report erzeugen und in die ordner struktur schreiben
    # nach durchführung der tests -> ordner struktur mit scraped_pages & tests & test report woanders hinkopieren über pfad
    # nach kopieren der ordnerstruktur ordnerstruktur innerhalb des repos aufräumen für den neuen run

    # Frage den Benutzer nach der URL, die gescraped werden soll
    start_url = input("Bitte gib die URL ein, die gescraped werden soll: ").strip()

    # Initialisiere OpenAI-Connector
    bot = OpenAIAPIConnector(model="gpt-4o-mini")

    if reset:
        bot.reset_state()
        print("🔁 Bot-Zustand zurückgesetzt.\n")
        bot = OpenAIAPIConnector(model="gpt-4o-mini")  # Neu instanziieren nach Reset

    # Scrape Website und speichere HTML-Dateien
    scraper = RecursiveWebScraper()
    scraper.start_scraping(start_url=start_url)

    # Lade HTML-Dateien aus Ordner
    html_parser = FileParser(folder_path="./scraped_pages")
    html_files = html_parser.read_all_files()
    max_files = len(html_files)  # Anzahl automatisch auslesen

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

    #TODO
    #Ausführen der Tests einbauen

    # Optionaler Reset am Ende zur Bereinigung
    if reset:
        bot.reset_state()
        print("🧹 Bot-Zustand am Ende zurückgesetzt.")


if __name__ == "__main__":
    main(reset=True)
