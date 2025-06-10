import os
import re
from bs4 import BeautifulSoup
from bs4 import XMLParsedAsHTMLWarning
import warnings



class FileParser:
    def __init__(self, folder_path):
        self.folder_path = folder_path

    def parse_html(self, html_content):
        """Extrahiere Informationen aus HTML – anpassbar."""
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
        soup = BeautifulSoup(html_content, "html.parser")
        title = soup.title.string if soup.title else "Kein Titel"
        return {
            "title": title,
            "html": html_content
        }

    def read_all_files(self):

        """Liest alle HTML-Dateien und gibt sie als Liste von Dictionaries zurück."""
        parsed_files = []

        for filename in os.listdir(self.folder_path):
            if filename.endswith(".html"):
                file_path = os.path.join(self.folder_path, filename)
                
                with open(file_path, 'r', encoding='utf-8') as file:
                    html_content = file.read()

                data = self.parse_html(html_content)
                data["filename"] = self.restore_url_string(filename)
                parsed_files.append(data)

        return parsed_files
    

    def restore_url_string(self,safe_name: str) -> str:
        """Konvertiert einen safe_filename (z. B. http_localhost_8080_ai.html) zurück zur URL."""
        name = safe_name.rsplit('.', 1)[0]  # Entfernt z. B. '.html'

        # 1. Protokoll wiederherstellen
        if name.startswith("http_"):
            name = name.replace("http_", "http://", 1)
        elif name.startswith("https_"):
            name = name.replace("https_", "https://", 1)

        # 2. Hostname mit Port finden – z. B. localhost:8080 oder 127.0.0.1:8000
        # Ersetze das erste '_' nach Host und Port mit ':'
        name = re.sub(r'(?<=http://)([^/_]+)_(\d+)', r'\1:\2', name)
        name = re.sub(r'(?<=https://)([^/_]+)_(\d+)', r'\1:\2', name)

        # 3. Alle weiteren Unterstriche zu Slashes (/) machen
        # z. B. http://localhost:8080_ai_foo → http://localhost:8080/ai/foo
        name = name.replace("_", "/")

        return name


class FileReader:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def exists(self) -> bool:
        """Überprüft, ob die Datei existiert."""
        return os.path.isfile(self.file_path)

    def read(self, encoding: str = 'utf-8') -> str:
        """Liest den Inhalt der Datei und gibt ihn als String zurück."""
        if not self.exists():
            raise FileNotFoundError(f"Datei nicht gefunden: {self.file_path}")

        try:
            with open(self.file_path, 'r', encoding=encoding, errors='ignore') as f:
                return f.read()
        except Exception as e:
            raise IOError(f"Fehler beim Lesen der Datei: {e}")

# Usage        
#reader = FileReader("example.txt")
#try:
#    content = reader.read()
#    print("Dateiinhalt:\n", content)
#except Exception as e:
#    print(e)