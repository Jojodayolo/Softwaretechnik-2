import os
import tempfile
from git import Repo

class RepositoryCloner:
    def clone_repo(self, git_url: str) -> str:
        """
        Klont das Git-Repository in ein temporäres Verzeichnis
        und gibt den Pfad zum Verzeichnis zurück.
        """
        temp_dir = tempfile.mkdtemp()
        Repo.clone_from(git_url, temp_dir)
        return temp_dir

def process_repo(self, repo_path: str, output_file: str):
    """
    Durchläuft rekursiv das Repository-Verzeichnis, liest alle .html- und .js-Dateien
    und schreibt deren relativen Pfad und Inhalt in die Ausgabedatei.
    """
    with open(output_file, 'w', encoding='utf-8') as out_file:
        for root, _, files in os.walk(repo_path):
            for file in files:
                if file.endswith('.html') or file.endswith('.js'):
                    file_path = os.path.join(root, file)
                    try:
                        relative_path = os.path.relpath(file_path, repo_path)
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        out_file.write(f"File: {relative_path}\n")
                        out_file.write(content)
                        out_file.write("\n\n")
                    except Exception as e:
                        print(f"Error processing {file_path}: {e}")
