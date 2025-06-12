import os
import re
import ast
import difflib
from OpenAIAPIConnector import OpenAIAPIConnector
from ResponseParser import ResponseParser
from FileParser import FileParser, FileReader
from RepositoryCloner import RepositoryCloner
from webscraper import RecursiveWebScraper
from pathlib import Path
import subprocess



def normalize_name(filename):
    """Normalize names for fuzzy matching, ignoring extension and common URL artifacts."""
    name = os.path.splitext(filename)[0]
    name = re.sub(r'^(http[s]?_+)?', '', name)  # Remove http_, https_, etc.
    name = name.replace(":", "_")
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    name = re.sub(r'_+', '_', name).strip('_')
    return name.lower()

def combine_requirements_with_scraped_pages(requirements_dir, scraped_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    requirement_files = [f for f in os.listdir(requirements_dir) if f.endswith(".txt")]
    scraped_files = [f for f in os.listdir(scraped_dir) if f.endswith((".txt", ".html"))]

    # Precompute normalized scraped filenames
    scraped_map = {
        normalize_name(f): f for f in scraped_files
    }

    for req_file in requirement_files:
        req_norm = normalize_name(req_file)

        best_match = difflib.get_close_matches(req_norm, scraped_map.keys(), n=1, cutoff=0.6)
        if not best_match:
            print(f"⚠️ Keine passende scraped Datei für {req_file} gefunden.")
            continue

        matched_scraped_file = scraped_map[best_match[0]]

        req_path = os.path.join(requirements_dir, req_file)
        scraped_path = os.path.join(scraped_dir, matched_scraped_file)
        output_path = os.path.join(output_dir, normalize_name(req_file) + "_combined.txt")

        try:
            with open(scraped_path, "r", encoding="utf-8") as f1, open(req_path, "r", encoding="utf-8") as f2:
                scraped_content = f1.read().strip()
                req_content = f2.read().strip()

            combined = (
                f"##### SCRAPED PAGE: {matched_scraped_file} #####\n\n"
                f"{scraped_content}\n\n"
                f"##### TEST REQUIREMENTS: {req_file} #####\n\n"
                f"{req_content}"
            )

            with open(output_path, "w", encoding="utf-8") as out_file:
                out_file.write(combined)

            print(f"✅ Kombiniert gespeichert: {output_path}")
        except Exception as e:
            print(f"❌ Fehler beim Kombinieren von {req_file} mit {matched_scraped_file}: {e}")



def process_image_folder(connector, image_folder: str):
    if not os.path.isdir(image_folder):
        raise ValueError(f"Ordner nicht gefunden: {image_folder}")

    # Create output directory beside image folder
    parent_dir = os.path.dirname(os.path.abspath(image_folder))
    output_dir = os.path.join(parent_dir, "image_requirements")
    os.makedirs(output_dir, exist_ok=True)

    image_files = [
        f for f in os.listdir(image_folder)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
    ]

    if not image_files:
        print("⚠️ Keine Bilddateien im Ordner gefunden.")
        return

    for image_file in image_files:
        image_path = os.path.join(image_folder, image_file)
        print(f"🔍 Verarbeite Bild: {image_file}")

        try:
            requirements = connector.generate_requirements_from_image(image_path)
            output_path = os.path.join(output_dir, os.path.splitext(image_file)[0] + ".txt")
            with open(output_path, "w", encoding="utf-8") as out_file:
                out_file.write(requirements)
            print(f"✅ Gespeichert: {output_path}")
        except Exception as e:
            print(f"❌ Fehler bei {image_file}: {e}")


def setup_directories(repository_name: str):
    base_path = Path(repository_name)
    for subfolder in ["scraped_pages", "tests", "test_results", "code", "images"]:
        (base_path / subfolder).mkdir(parents=True, exist_ok=True)
    return base_path

def is_syntax_valid(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        compile(source, filepath, "exec")
        return True
    except SyntaxError as e:
        print(f"❌ Syntaxfehler in {filepath}: {e}")
        return False
    


def contains_test_functions(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=filepath)
    return any(isinstance(node, ast.FunctionDef) and node.name.startswith("test_") for node in tree.body)

def is_collected_by_pytest(filepath):
    result = subprocess.run(
        ["pytest", "--collect-only", str(filepath)],
        capture_output=True,
        text=True
    )
    return "collected 0 items" not in result.stdout and result.returncode == 0

def is_test_runnable(filepath):
    return (
        is_syntax_valid(filepath)
        and contains_test_functions(filepath)
        and is_collected_by_pytest(filepath)
    )


# .\chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\\temp-chrome"

def main(reset=True):
    # Frage den Benutzer nach der URL, die gescraped werden soll
    start_url = input("Bitte gib die URL ein, die gescraped werden soll: ").strip()

    # Initialisiere OpenAI-Connector
    bot = OpenAIAPIConnector(model="gpt-4o-mini")

    if reset:
        bot.reset_state()
        print("🔁 Bot-Zustand zurückgesetzt.\n")
        bot = OpenAIAPIConnector(model="gpt-4o-mini")  # Neu instanziieren nach Reset

    #create repository folder
    base_path = setup_directories("run_output")

    # Scrape Website und speichere HTML-Dateien
    scraper = RecursiveWebScraper()
    scraper.start_scraping(start_url=start_url, locationPath=base_path)

    #Get Requirements from image
    #process_image_folder(bot, base_path / "images")
    # Kombiniere Requirements mit gescrapten Seiten
    combine_requirements_with_scraped_pages(
        requirements_dir=base_path / "image_requirements",
        scraped_dir=base_path / "scraped_pages",
        output_dir=base_path / "combined_requirements"
    )
    # Lade HTML-Dateien aus Ordner
    html_parser = FileParser(folder_path= base_path / "scraped_pages")
    html_files = html_parser.read_all_files()
    max_files = len(html_files)  # Anzahl automatisch auslesen

    for i, file_data in enumerate(html_files[:max_files]):
        html_content = file_data['html']
        filename = file_data['filename']
        url = f"/{filename}"  # relative TEST_URL

        # Speichere HTML-Inhalt und zugehörige URL in Textdatei
        input_file = base_path / "code" / f"code{i}.txt"
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
        test_output_file = base_path / "tests" / f"test_playwright_{i}.py"
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


