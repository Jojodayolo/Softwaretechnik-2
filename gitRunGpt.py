import os
import tempfile
from git import Repo
from openai import OpenAI
import time


# Load the prompt from an external file
def load_prompt():
    prompt_path = "prompt.txt"
    if not os.path.exists(prompt_path):
        print(f"The prompt file '{prompt_path}' was not found. Creating a default prompt file.")
        with open(prompt_path, "w", encoding="utf-8") as file:
            file.write("Default prompt content: {content}")
        return "Default prompt content: {content}"
    with open(prompt_path, "r", encoding="utf-8") as file:
        return file.read()

# Clone the repository to a temporary directory
def clone_repo(git_url):
    temp_dir = tempfile.mkdtemp()
    Repo.clone_from(git_url, temp_dir)
    return temp_dir

# Process the repository and include all files and their folder structure
def process_repo(repo_path, output_file):
    with open(output_file, 'w', encoding='utf-8') as out_file:
        for root, _, files in os.walk(repo_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    # Calculate the relative path from the base directory
                    relative_path = os.path.relpath(file_path, repo_path)
                    
                    # Read the file content
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # Write the relative file path and content to the output file
                    out_file.write(f"File: {relative_path}\n")
                    out_file.write(content)
                    out_file.write("\n\n")
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")

def upload_to_gpt(output_file_path, prompt_template, response_output_path="gpt_response.txt"):
    client = OpenAI()
    
    # Load OpenAI API key from environment variable
    OpenAI.api_key = os.getenv("OPENAI_API_KEY")

    # 1. Datei hochladen
    with open(output_file_path, "rb") as f:
        uploaded_file = client.files.create(
            file=f,
            purpose="assistants"
        )

    print(f"Datei hochgeladen. file_id: {uploaded_file.id}")

    # 2. Assistant erstellen (oder existierenden verwenden)
    assistant = client.beta.assistants.create(
        name="Repo Analyzer",
        instructions=prompt_template,
        tools=[{"type": "code_interpreter"}],
        model="gpt-4"
    )

    # 3. Thread erstellen
    thread = client.beta.threads.create()

    # 4. Message mit Datei senden
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=" Hier ist der Inhalt des Repositories:",
        file_ids=[uploaded_file.id]
    )

    # 5. Run starten
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id
    )

    print("Warte auf Antwort...")

    # 6. Auf Antwort warten (Polling)
    while True:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run_status.status == "completed":
            break
        elif run_status.status in ["failed", "cancelled", "expired"]:
            print(f"Run fehlgeschlagen mit Status: {run_status.status}")
            return
        time.sleep(2)

    # 7. Antwort abholen und in Datei schreiben
    messages = client.beta.threads.messages.list(thread_id=thread.id)

    with open(response_output_path, "w", encoding="utf-8") as out_file:
        for message in reversed(messages.data):  # Neueste oben
            for content in message.content:
                if content.type == "text":
                    out_file.write(content.text.value + "\n\n")


# Main function
def main():
    # Request the Git repository URL
    git_url = input("Enter the Git repository URL: ")
    
    # Clone the repository
    print("Cloning repository...")
    repo_path = clone_repo(git_url)
    
    # Load the prompt
    print("Loading prompt...")
    prompt_template = load_prompt()
    
    # Process the repository
    output_file = "output.txt"
    print(f"Processing repository and saving to {output_file}...")
    process_repo(repo_path, output_file)
    
    upload_to_gpt(output_file, prompt_template)
    
    print("Done. Temporary directory not deleted for inspection.")

if __name__ == "__main__":
    main()
