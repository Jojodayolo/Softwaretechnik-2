from OpenAIAPIConnector import OpenAIAPIConnector
from ResponseParser import ResponseParser
from FileParser import FileReader
from RepositoryCloner import RepositoryCloner
import subprocess
import os
import re

parser = ResponseParser()
cloner = RepositoryCloner()
repo = cloner.clone_repo("https://github.com/saucelabs/the-internet.git")
cloner.process_repo(repo, "repository.txt")
print(f"Repository geklont und verarbeitet.")

# Usage        
#reader = FileReader("output.txt")
#try:
#    content = reader.read()
#    print("Dateiinhalt:\n", content)
#except Exception as e:
#    print(e)

#bot = DeepSeekAPIConnector(model="deepseek-chat")
#answer = bot.ask("das ist der deepseek-chat test, sag mir ob der geht")
#print(answer)

#bot = DeepSeekAPIConnector(model="deepseek-reasoner")
#answer = bot.ask("das ist der deepseek-reasoner test, sag mir ob der geht")

with open("output.txt", "r", encoding="utf-8") as f:
    repo_code = f.read()

bot = OpenAIAPIConnector(model="gpt-4o-mini")
content = """
Stell dir vor du bist ein Test Automation Engineer und du enthält Code aus einem Repository.
Anhand dieses Codes sollst du python unit tests erstellen, die das Repository per Playwright testen
Versuche eine hohe Anzahl an Test zu generieren 
Überlege dir anhand des Quellcodes Tests die ausgeführt werden können und gib mir den entsprechenden Code
Versuche alle vorhandenen Methoden zu testen die du im Code findest damit du eine hohe code coverage hast
Gebe mir nur den Code zurück und sonst nichts, damit ich den Code parsen kann.
Nutze für die Ausführung den testrunner CsvTestRunner, diesen kannst du aus from csv_test_runner import CsvTestRunner importieren
Die Website ist erreichbar unter http://localhost:8080
Erstelle nur Tests die auch mit der entsprechenden Datei matchen
Messe dazu noch die Javascript Coverage im Chrome browser über die Devtools mit Playwright als testframework schreibe einfach normal unittest 
Nehmen folgendes Gerüst um die Coverage mit Playwright zu scannen:
import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # CDP-Session aufbauen
        client = await context.new_cdp_session(page)

        # Profiler & Debugger aktivieren
        await client.send("Profiler.enable")
        await client.send("Debugger.enable")

        # JS Coverage starten
        await client.send("Profiler.startPreciseCoverage", {"callCount": False, "detailed": True})

        await page.goto("https://www.google.com")

        try:
            await page.click("#W0wltc", timeout=3000)
        except:
            print("Cookie-Hinweis nicht sichtbar oder schon akzeptiert.")

        await page.fill("#APjFqb", "hallo")
        await page.wait_for_timeout(3000)

        # Coverage holen und stoppen
        result = await client.send("Profiler.takePreciseCoverage")
        await client.send("Profiler.stopPreciseCoverage")
        await client.send("Profiler.disable")
        await client.send("Debugger.disable")

        # Coverage auswerten
        coverage_report = []
        for script in result["result"]:
            url = script.get("url", "")
            functions = script.get("functions", [])
            used = 0
            total = 0
            for fn in functions:
                for r in fn.get("ranges", []):
                    length = r["endOffset"] - r["startOffset"]
                    total += length
                    if r["count"] > 0:
                        used += length
            percent = (used / total * 100) if total else 0
            coverage_report.append(f"{url}\n  Genutzter JS-Code: {used}/{total} Bytes ({percent:.2f}%)\n")

        # Ergebnis ausgeben
        print("\nJavaScript-Coverage-Report:\n")
        print("".join(coverage_report))

        # In Datei speichern
        with open("coverage_report.txt", "w", encoding="utf-8") as f:
            f.writelines(coverage_report)

        await browser.close()

asyncio.run(run())

Erstelle Tests für das nachfolgende Repository und baue es in das oben gegebene Gerüst ein um die Coverage zu messen

Hier der Code des Repositorys
"""  + parser.parseContent(repo_code)

#print(content)
#answer = bot.ask(content)
content= """
1. Analysiere die gesamte Datei.
2. Liste zuerst ALLE testbaren Features (auch Buttons, Links, Menüs, Alerts, Validierungen, dynamische Listen, etc.) als Bullet-Points auf.
3. Schreibe dann für jedes Feature mindestens einen Playwright-Test.
4. Falls die Antwort zu lang wird, schreibe am Ende “FORTSETZUNG” und fahre beim nächsten Prompt fort.

"""
answer = bot.ask_with_file("repository.txt")
print(answer)

# Extrahiere den Python-Code (zwischen ```python ... ```)
py_blocks = re.findall(r"```python(.*?)```", answer, re.DOTALL)

if not py_blocks:
    # Fallback: Falls kein Markdown-Block, schreibe gesamte Antwort in Datei
    py_code = answer.strip()
else:
    # Nimm alle gefundenen Blöcke (falls mehrere) und füge sie zusammen
    py_code = "\n\n".join([b.strip() for b in py_blocks])

# Speichere als pytest-Datei
output_file = "test_playwright_assistant.py"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(py_code)

print(f"Alle generierten Playwright-Python-Tests wurden in {output_file} gespeichert!")

#answer = parser.parseResponse(answer)
#print(answer)
#if answer:    
#    with open("codetest.py", "w", encoding="utf-8") as file:
#        file.write(answer)
#    try:
#        venv_python = os.path.join(".venv", "Scripts", "python.exe") if os.name == "nt" else "venv/bin/python"
#        result = subprocess.run([venv_python, "codetest.py"], capture_output=True, text=True, check=True)
#        print("Testausgabe:\n", result.stdout)
#    except subprocess.CalledProcessError as e:
#        print("Fehler bei der Ausführung von codetest.py:")
#        print(e.stderr)

