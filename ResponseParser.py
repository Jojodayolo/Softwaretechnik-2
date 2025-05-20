import re

class ResponseParser:
    def parseResponse(self, content):
        pattern = re.compile(r'-Start-\n(.*?)\n-Ende-', re.DOTALL)
        match = pattern.search(content)
        if match:
            return match.group(1).strip()
        return None
