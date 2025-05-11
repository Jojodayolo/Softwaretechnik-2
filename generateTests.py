import openai
import os


# Load OpenAI API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

# File paths
requirements_file = "testRequirements.txt"
prompt_file = "genTestPrompt.txt"
output_file = "generatedTests.py"

def read_file(file_path):
    """Reads the content of a file and returns it as a string."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        print(f"Error: File not found - {file_path}")
        return None

def write_file(file_path, content):
    """Writes the given content to a file."""
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(content)

def generate_tests(requirements, extra_prompt):
    """Generates test code using GPT."""
    combined_prompt = f"{requirements}\n\n{extra_prompt}"
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",  # Use the appropriate model
            prompt=combined_prompt,
            max_tokens=1500,
            temperature=0.7
        )
        return response.choices[0].text.strip()
    except Exception as e:
        print(f"Error generating tests: {e}")
        return None

def main():
    # Read the test requirements and extra prompt
    requirements = read_file(requirements_file)
    extra_prompt = read_file(prompt_file)

    if requirements is None or extra_prompt is None:
        print("Error: Missing input files.")
        return

    # Generate the test code
    generated_code = generate_tests(requirements, extra_prompt)

    if generated_code:
        # Write the generated code to the output file
        write_file(output_file, generated_code)
        print(f"Generated tests written to {output_file}")
    else:
        print("Error: Failed to generate tests.")

if __name__ == "__main__":
    main()