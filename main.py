from OpenAIAPIConnector import OpenAIAPIConnector
from ResponseParser import ResponseParser
from FileParser import FileReader
from RepositoryCloner import RepositoryCloner

cloner = RepositoryCloner()
repo = cloner.clone_repo("https://github.com/bradtraversy/creative-agency-website.git")
cloner.process_repo(repo, "output.txt")
print(f"Repository geklont und verarbeitet.")

# Usage        
reader = FileReader("output.txt")
try:
    content = reader.read()
    print("Dateiinhalt:\n", content)
except Exception as e:
    print(e)

#bot = DeepSeekAPIConnector(model="deepseek-chat")
#answer = bot.ask("das ist der deepseek-chat test, sag mir ob der geht")
#print(answer)

#bot = DeepSeekAPIConnector(model="deepseek-reasoner")
#answer = bot.ask("das ist der deepseek-reasoner test, sag mir ob der geht")

bot = OpenAIAPIConnector(model="gpt-4o-mini")
content = """
Stell dir vor du bist ein Test Automation Engineer und nachfolgend bekommst du ein Repository mit Code.
Anhand dieses Codes sollst du python unit tests erstellen, die das Frontend per Selenium testen
Gebe den Selenium Code zwischen -Start- und -End- ein sodass der code automatisch geparsed werden kann.
Hier der Code des Repositorys.
""" + content
answer = bot.ask(content)
parser = ResponseParser()
answer = parser.parseResponse(answer)

with open("code.txt", "w", encoding="utf-8") as file:
    file.write(answer)

