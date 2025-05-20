import os

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