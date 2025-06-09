from OpenAIAPIConnector import OpenAIAPIConnector
from ResponseParser import ResponseParser
from FileParser import FileParser, FileReader
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

parser = FileParser(folder_path="./scraped_pages")
html_files = parser.read_all_files()
for i, file_data in enumerate(html_files[:3]):  # nur die ersten 3 Dateien
    # Speichere den HTML-Inhalt + URL in eine Datei
    with open("code.txt", "w", encoding="utf-8") as file:
        file.write(file_data['html'] + "\n\nURL available under: " + file_data['filename'])

    # Frage das Modell mit dieser Datei
    answer = bot.ask_with_file(
        "code.txt"
    )

    print(f"Antwort für Datei {i} ({file_data['filename']}):")
    print(answer)

    # Extrahiere Python-Codeblöcke
    py_blocks = re.findall(r"```python(.*?)```", answer, re.DOTALL)
    if not py_blocks:
        py_code = answer.strip()
    else:
        py_code = "\n\n".join([b.strip() for b in py_blocks])

    # Speichere Testcode in eine eigene Datei
    output_file = f"test_playwright_{i}.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(py_code)

    print(f"Test gespeichert in {output_file}\n")

