
import ast
import difflib
import os
from pathlib import Path
import re
import subprocess


class TestUtils:
    @staticmethod
    def normalize_name(filename):
        """Normalize names for fuzzy matching, ignoring extension and common URL artifacts."""
        name = os.path.splitext(filename)[0]
        name = re.sub(r'^(http[s]?_+)?', '', name)  # Remove http_, https_, etc.
        name = name.replace(":", "_")
        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        name = re.sub(r'_+', '_', name).strip('_')
        return name.lower()

    @staticmethod
    def restore_url_string(safe_name: str) -> str:
        """Converts a safe_filename (e.g. http_localhost_8080_ai.html) back to the URL."""
        name = safe_name.rsplit('.', 1)[0]  # Removes e.g. '.html'

        # 1. Restore protocol
        if name.startswith("http_"):
            name = name.replace("http_", "http://", 1)
        elif name.startswith("https_"):
            name = name.replace("https_", "https://", 1)
        else:
            name = "http://" + name  # Fallback

        # 2. Extract host:port
        match = re.match(r"(https?://[^/_]+)_(\d+)(.*)", name)
        if match:
            base = f"{match.group(1)}:{match.group(2)}"
            rest = match.group(3).replace("_", "/")
            return base + rest

        # 3. If no port: replace all _ after host with /
        prefix, _, path = name.partition("://")
        parts = path.split("_")
        return f"{prefix}://{'/'.join(parts)}"

    @staticmethod
    def is_syntax_valid(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
            compile(source, filepath, "exec")
            return True
        except SyntaxError as e:
            print(f"❌ Syntax error in {filepath}: {e}")
            return False
        
    @staticmethod
    def contains_test_functions(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=filepath)
        return any(isinstance(node, ast.FunctionDef) and node.name.startswith("test_") for node in tree.body)

    @staticmethod
    def is_collected_by_pytest(filepath):
        result = subprocess.run(
            ["pytest", "--collect-only", str(filepath)],
            capture_output=True,
            text=True
        )
        return "collected 0 items" not in result.stdout and result.returncode == 0

    @staticmethod
    def is_test_runnable(filepath):
        return (
            TestUtils.is_syntax_valid(filepath)
            and TestUtils.contains_test_functions(filepath)
            and TestUtils.is_collected_by_pytest(filepath)
        )

class RequirementCombiner:
    
    def combine(requirements_dir, scraped_dir, output_dir):
        os.makedirs(output_dir, exist_ok=True)

        requirement_files = [f for f in os.listdir(requirements_dir) if f.endswith(".txt")]
        scraped_files = [f for f in os.listdir(scraped_dir) if f.endswith((".txt", ".html"))]

        exampleTest = open(f"exampleTest.txt", "r", encoding="utf-8")

        # Precompute normalized scraped filenames
        scraped_map = {
            TestUtils.normalize_name(f): f for f in scraped_files
        }

        for req_file in requirement_files:
            req_norm = TestUtils.normalize_name(req_file)
            test_url = TestUtils.restore_url_string(req_file)
            best_match = difflib.get_close_matches(req_norm, scraped_map.keys(), n=1, cutoff=0.6)
            if not best_match:
                print(f"⚠️ No matching scraped file found for {req_file}.")
                continue

            matched_scraped_file = scraped_map[best_match[0]]

            req_path = os.path.join(requirements_dir, req_file)
            scraped_path = os.path.join(scraped_dir, matched_scraped_file)
            output_path = os.path.join(output_dir, TestUtils.normalize_name(req_file) + "_combined.txt")

            try:
                with open(scraped_path, "r", encoding="utf-8") as f1, open(req_path, "r", encoding="utf-8") as f2, open("exampleTest.txt", "r", encoding="utf-8") as file:
                    scraped_content = f1.read().strip()
                    req_content = f2.read().strip()
                    content = file.read()

                combined = (
                    f"##### SCRAPED PAGE #####\n\n"
                    f"{scraped_content}\n\n"
                    f"\n##### TEST REQUIREMENTS #####\n\n"
                    f"{req_content}"
                    f"\n### TEST URL ###\n\n"
                    f"{test_url}"
                    f"\n### Use the following test as a template\n\n"
                    f"{content}\n"
                    
                )

                with open(output_path, "w", encoding="utf-8") as out_file:
                    out_file.write(combined)

                print(f"✅ Combined and saved: {output_path}")
            except Exception as e:
                print(f"❌ Error combining {req_file} with {matched_scraped_file}: {e}")

class ImageRequirementProcessor:
    @staticmethod
    def process(connector, image_folder: str):
        if not os.path.isdir(image_folder):
            raise ValueError(f"Folder not found: {image_folder}")

        # Create output directory beside image folder
        parent_dir = os.path.dirname(os.path.abspath(image_folder))
        output_dir = os.path.join(parent_dir, "image_requirements")
        os.makedirs(output_dir, exist_ok=True)

        image_files = [
            f for f in os.listdir(image_folder)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
        ]

        if not image_files:
            print("⚠️ No image files found in folder.")
            return

        for image_file in image_files:
            image_path = os.path.join(image_folder, image_file)
            output_path = os.path.join(output_dir, os.path.splitext(image_file)[0] + ".txt")

            if os.path.exists(output_path):
                print(f"⏩ Skipping {image_file} – Output file already exists.")
                continue

            print(f"🔍 Processing image: {image_file}")

            try:
                requirements = connector.generate_requirements_from_image(image_path)
                with open(output_path, "w", encoding="utf-8") as out_file:
                    out_file.write(requirements)
                print(f"✅ Saved: {output_path}")
            except Exception as e:
                print(f"❌ Error with {image_file}: {e}")

class DirectorySetup:
    @staticmethod
    def setup(repository_name: str):
        base_path = Path(repository_name)
        for subfolder in ["scraped_pages", "tests", "test_results", "code", "images"]:
            (base_path / subfolder).mkdir(parents=True, exist_ok=True)
        return base_path