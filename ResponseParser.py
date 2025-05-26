import re

class ResponseParser:
    def parseResponse(self, code):
        lines = code.strip().split('\n')

        # Entferne erste Zeile, wenn sie nicht mit "from" beginnt
        if lines and not lines[0].strip().startswith("from"):
            lines.pop(0)

        # Entferne letzte Zeile, wenn sie nur aus ``` besteht
        if lines and lines[-1].strip() == "```":
            lines.pop()

        # Setze den Code wieder zusammen
        cleaned_code = '\n'.join(lines)
        return cleaned_code
    
    def parseContent(self, code):
        # Entferne mehrzeilige JS-Kommentare (/* ... */)
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)

        # Entferne vollständige Kommentarzeilen mit # oder //
        code = re.sub(r'^\s*(#|//).*$', '', code, flags=re.MULTILINE)

        # Entferne Inline-Kommentare mit // oder #
        code = re.sub(r'(.*?)\s*(//|#).*$', r'\1', code, flags=re.MULTILINE)

        # Entferne überflüssige Leerzeilen
        code = re.sub(r'\n\s*\n', '\n', code)

        # Optional: Entferne führende/trailing Leerzeichen je Zeile
        code = '\n'.join(line.rstrip() for line in code.splitlines())

        return code.strip()
