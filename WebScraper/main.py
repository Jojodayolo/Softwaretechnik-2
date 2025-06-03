import os
import time
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup
from typing import Set, List
import re


def merge_files_with_filenames(directory: str, output_file: str):
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for filename in sorted(os.listdir(directory)):
            filepath = os.path.join(directory, filename)
            if os.path.isfile(filepath):
                outfile.write(f"=== {filename} ===\n")  # Dateiname als Überschrift
                with open(filepath, 'r', encoding='utf-8') as infile:
                    outfile.write(infile.read())
                outfile.write('\n\n')  # Abstand zwischen Dateien


def restore_url_string(safe_name: str) -> str:
    """Konvertiert einen safe_filename (z. B. http_localhost_8080_ai.html) zurück zur URL."""
    name = safe_name.rsplit('.', 1)[0]  # Entfernt Dateiendung wie .html

    # Ersetze Protokoll
    if name.startswith("http_"):
        name = name.replace("http_", "http://", 1)
    elif name.startswith("https_"):
        name = name.replace("https_", "https://", 1)

    # localhost_ → localhost:
    name = name.replace("localhost_", "localhost:", 1)

    # Alle weiteren Unterstriche nach dem Port durch / ersetzen
    match = re.search(r'localhost:\d+', name)
    if match:
        end = match.end()
        prefix = name[:end]
        rest = name[end:].replace("_", "/")
        name = prefix + rest
    else:
        # Fallback für andere Hosts
        name = name.replace("_", "/")

    return name

def process_file(filepath: str, output_path: str = None):
    """Liest eine Datei ein, ersetzt alle safe-Filenames durch rekonstruierte URLs."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Finde alle safe-Filenames wie http_localhost_8080_ai.html
    matches = re.findall(r'\bhttps?_[\w\-_.]+\.html\b', content)

    for match in matches:
        restored = restore_url_string(match)
        print(f"{match} → {restored}")
        content = content.replace(match, restored)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"\nErgebnis gespeichert in: {output_path}")
    else:
        print("\nErsetzter Inhalt:\n")
        print(content)


def get_all_links(soup: BeautifulSoup, current_url: str, base_domain: str) -> Set[str]:
    """Extract all internal links from a BeautifulSoup object."""
    links = set()
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        full_url = urljoin(current_url, href)  # Resolve relative URLs
        parsed_url = urlparse(full_url)
        # Only add links that are internal and use http/https
        if parsed_url.netloc == base_domain and full_url.startswith(('http://', 'https://')):
            links.add(full_url)
    return links

def safe_filename(url: str) -> str:
    """Convert a URL into a safe filename by replacing special characters."""
    return url.replace("://", "_").replace("/", "_").replace(":", "_")

def fetch_html(url: str) -> str:
    """
    Fetch HTML content from a URL.
    Retries up to 5 times if a 429 Too Many Requests error is encountered, with exponential backoff.
    """
    max_retries = 5
    for attempt in range(max_retries):
        response = requests.get(url)
        if response.status_code == 429:
            print(f"429 Too Many Requests for {url}, sleeping before retry ({attempt+1}/{max_retries})...")
            time.sleep(5 * (attempt + 1))  # Exponential backoff
            continue
        response.raise_for_status()
        return response.text
    raise Exception(f"Failed to fetch {url} after {max_retries} attempts due to rate limiting.")

def save_html(html: str, filename: str) -> None:
    """Save HTML content to a file, creating directories as needed."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)

def extract_page_info(html: str, url: str) -> dict:
    """
    Extract relevant information from HTML content.
    Raises an error if critical info (title or text) is missing.
    """
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    meta_desc = ""
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        meta_desc = meta["content"].strip()
    # Extract all headings (h1, h2, h3)
    headings = {tag: [h.get_text(strip=True) for h in soup.find_all(tag)] for tag in ["h1", "h2", "h3"]}
    # Extract all links
    links = [a['href'] for a in soup.find_all('a', href=True)]
    # Extract all images with src and alt
    images = [{"src": img.get("src"), "alt": img.get("alt", "")} for img in soup.find_all("img")]
    # Extract all visible text
    text = soup.get_text(separator=" ", strip=True)

    # Throw error if critical info is missing
    if not title or not text:
        raise ValueError(f"Critical information missing for {url}: title or text not found.")

    return {
        "url": url,
        "title": title,
        "meta_description": meta_desc,
        "headings": headings,
        "links": links,
        "images": images,
        "text": text
    }

def scrape_site_recursive(
    url: str,
    base_domain: str,
    visited: Set[str],
    output_dir: str,
    sleep_time: float = 0.5,
    fetch_func=fetch_html,
    save_func=save_html
) -> None:
    """
    Recursively scrape a website starting from the given URL.
    Saves only the HTML for each page.
    """
    filename = os.path.join(output_dir, f"{safe_filename(url)}.html")
    # Skip if already visited or file exists
    if url in visited or os.path.exists(filename):
        return
    try:
        html = fetch_func(url)
        save_func(html, filename)
        # Optionally, still extract info to validate content
        extract_page_info(html, url)
        soup = BeautifulSoup(html, 'html.parser')
        links = get_all_links(soup, url, base_domain)
        visited.add(url)
        time.sleep(sleep_time)
        # Recursively scrape all found links
        for link in links:
            scrape_site_recursive(link, base_domain, visited, output_dir, sleep_time, fetch_func, save_func)
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")

def list_scraped_files(output_dir: str) -> List[str]:
    """List all scraped HTML files in the output directory."""
    if not os.path.exists(output_dir):
        return []
    return [f for f in os.listdir(output_dir) if f.endswith(".html")]

def main(start_url: str, output_dir: str = "scraped_pages", sleep_time: float = 0.5) -> None:
    """
    Main entry point for the scraper.
    Starts the recursive scraping process and prints the result summary.
    """
    base_domain = urlparse(start_url).netloc
    visited = set()
    scrape_site_recursive(start_url, base_domain, visited, output_dir, sleep_time)
    scraped_files = list_scraped_files(output_dir)
    print(f"Scraped {len(scraped_files)} pages. Files are in '{output_dir}/'.")

if __name__ == "__main__":
    import sys
    # Allow URL to be passed as a command-line argument, otherwise prompt the user
    if len(sys.argv) > 1:
        start_url = sys.argv[1]
    else:
        start_url = input("Enter the URL of the website to scrape: ").strip()
    main(start_url)
    # Beispielnutzung
    merge_files_with_filenames("G:\\uni\\Softwaretechnik-2\\scraped_pages", "zusammengefuegt.txt")
    process_file("G:\\uni\\Softwaretechnik-2\\zusammengefuegt.txt", output_path="G:\\uni\\Softwaretechnik-2\\zusammengefuegtresult.txt")
