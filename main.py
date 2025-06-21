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
import shutil  



def normalize_name(filename):
    """Normalize names for fuzzy matching, ignoring extension and common URL artifacts."""
    name = os.path.splitext(filename)[0]
    name = re.sub(r'^(http[s]?_+)?', '', name)  # Remove http_, https_, etc.
    name = name.replace(":", "_")
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    name = re.sub(r'_+', '_', name).strip('_')
    return name.lower()

def restore_url_string(safe_name: str) -> str:
    """Konvertiert einen safe_filename (z. B. http_localhost_8080_ai.html) zurück zur URL."""
    name = safe_name.rsplit('.', 1)[0]  # Entfernt z. B. '.html'

    # 1. Protokoll wiederherstellen
    if name.startswith("http_"):
        name = name.replace("http_", "http://", 1)
    elif name.startswith("https_"):
        name = name.replace("https_", "https://", 1)
    else:
        name = "http://" + name  # Fallback

    # 2. Host:Port extrahieren
    match = re.match(r"(https?://[^/_]+)_(\d+)(.*)", name)
    if match:
        base = f"{match.group(1)}:{match.group(2)}"
        rest = match.group(3).replace("_", "/")
        return base + rest

    # 3. Falls kein Port vorhanden: Ersetze ab dem Host alle _ durch /
    prefix, _, path = name.partition("://")
    parts = path.split("_")
    return f"{prefix}://{'/'.join(parts)}"

def combine_requirements_with_scraped_pages(requirements_dir, scraped_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    requirement_files = [f for f in os.listdir(requirements_dir) if f.endswith(".txt")]
    scraped_files = [f for f in os.listdir(scraped_dir) if f.endswith((".txt", ".html"))]

    exampleTest = open(f"exampleTest.txt", "r", encoding="utf-8")


    # Precompute normalized scraped filenames
    scraped_map = {
        normalize_name(f): f for f in scraped_files
    }

    for req_file in requirement_files:
        req_norm = normalize_name(req_file)
        test_url = restore_url_string(req_file)
        best_match = difflib.get_close_matches(req_norm, scraped_map.keys(), n=1, cutoff=0.6)
        if not best_match:
            print(f"⚠️ Keine passende scraped Datei für {req_file} gefunden.")
            continue

        matched_scraped_file = scraped_map[best_match[0]]

        req_path = os.path.join(requirements_dir, req_file)
        scraped_path = os.path.join(scraped_dir, matched_scraped_file)
        output_path = os.path.join(output_dir, normalize_name(req_file) + "_combined.txt")

        try:
            with open(scraped_path, "r", encoding="utf-8") as f1, open(req_path, "r", encoding="utf-8") as f2, open("exampleTest.txt", "r", encoding="utf-8") as file:
                scraped_content = f1.read().strip()
                req_content = f2.read().strip()
                content = file.read()

            combined = (
                f"##### SCRAPED PAGE #####\n\n"
                f"{scraped_content}\n\n"
                f"\n##### TEST REQUIREMENTS #####\n\n"
                f"{req_content}"
                f"\n### TEST URL ###\n\n"
                f"{test_url}"
                f"\n### Use the following test as a template\n\n"
                f"{content}\n"
                
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
        output_path = os.path.join(output_dir, os.path.splitext(image_file)[0] + ".txt")

        if os.path.exists(output_path):
            print(f"⏩ Überspringe {image_file} – Ausgabedatei existiert bereits.")
            continue

        print(f"🔍 Verarbeite Bild: {image_file}")

        try:
            requirements = connector.generate_requirements_from_image(image_path)
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
    process_image_folder(bot, base_path / "images")
    # Kombiniere Requirements mit gescrapten Seiten
    combine_requirements_with_scraped_pages(
        requirements_dir=base_path / "image_requirements",
        scraped_dir=base_path / "scraped_pages",
        output_dir=base_path / "combined_requirements"
    )
    # Lade Requirements Dateien aus Ordner
    requirement_files = [f for f in os.listdir(base_path / "combined_requirements") if f.endswith(".txt")]
    max_files = len(requirement_files)  # Anzahl automatisch auslesen

    for i, file_data in enumerate(requirement_files):

        print(f" Frage OpenAI mit {file_data}...")

        try:
            response = bot.ask_with_file(base_path / "combined_requirements" / file_data)
        except Exception as e:
            print(f"❌ Fehler bei Datei {file_data}: {e}")
            continue

        if not response.strip():
            print(f"⚠️ Keine Antwort erhalten für Datei {file_data}.")
            continue

        print(f"✅ Antwort erhalten für Datei {file_data}.")

        # Extrahiere Python-Code aus Codeblöcken
        code_blocks = re.findall(r"```python(.*?)```", response, re.DOTALL)
        test_code = "\n\n".join(cb.strip() for cb in code_blocks) if code_blocks else response.strip()

        # Speichere generierten Testcode in .py-Datei
        test_output_file = base_path / "tests" / f"test_playwright_{i}.py"
        with open(test_output_file, "w", encoding="utf-8") as f:
            f.write(test_code)

        print(f"💾 Test gespeichert in: {test_output_file}\n")

    print("🎯 Verarbeitung abgeschlossen.\n")

    # 🧪 Testdateien ausführen (ohne Coverage), Output speichern
    test_dir = base_path / "tests"
    test_files = [test_dir / f for f in os.listdir(test_dir) if f.endswith(".py")]

    runnable_tests = [str(f) for f in test_files if is_test_runnable(f)]

    if not runnable_tests:
        print("⚠️ Keine lauffähigen Testdateien gefunden.")
    else:
        print(f"🚀 Führe {len(runnable_tests)} Testdateien mit pytest aus...")

        output_log_path = base_path / "test_results" / "pytest_output.log"
        with open(output_log_path, "w", encoding="utf-8") as log_file:
            result = subprocess.run(
                ["pytest"] + runnable_tests,
                cwd=base_path,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True
            )

        if result.returncode == 0:
            print(f"✅ Alle Tests erfolgreich. Output gespeichert unter: {output_log_path}")
        else:
            print(f"❌ Einige Tests sind fehlgeschlagen. Siehe Log: {output_log_path}")

    # Optionaler Reset am Ende zur Bereinigung
    if reset:
        bot.reset_state()
        print("🧹 Bot-Zustand am Ende zurückgesetzt.")
    #shutil.rmtree(base_path)
    #print("🗑️ Ordner 'run_output' wurde gelöscht.")

if __name__ == "__main__":
    main(reset=True)


