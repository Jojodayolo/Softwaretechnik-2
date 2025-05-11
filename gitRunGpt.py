import os
import tempfile
import shutil
from git import Repo

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
    
    print("Done. Temporary directory not deleted for inspection.")

if __name__ == "__main__":
    main()
