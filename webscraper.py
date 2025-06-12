import os
import time
import re
from urllib.parse import urlparse, urljoin
from typing import Set, List
import requests
from bs4 import BeautifulSoup

from GeneratePagePictures import take_screenshots


class RecursiveWebScraper:
    def __init__(self, output_dir: str = "scraped_pages", sleep_time: float = 0.5):
        self.output_dir = output_dir
        self.sleep_time = sleep_time

    def safe_filename(self, url: str) -> str:
        return url.replace("://", "_").replace("/", "_").replace(":", "_")

    def restore_url_string(self, safe_name: str) -> str:
        name = safe_name.rsplit('.', 1)[0]
        if name.startswith("http_"):
            name = name.replace("http_", "http://", 1)
        elif name.startswith("https_"):
            name = name.replace("https_", "https://", 1)
        name = name.replace("localhost_", "localhost:", 1)
        match = re.search(r'localhost:\d+', name)
        if match:
            end = match.end()
            prefix = name[:end]
            rest = name[end:].replace("_", "/")
            name = prefix + rest
        else:
            name = name.replace("_", "/")
        return name

    def fetch_html(self, url: str) -> str:
        max_retries = 5
        for attempt in range(max_retries):
            response = requests.get(url)
            if response.status_code == 429:
                print(f"429 Too Many Requests for {url}, sleeping before retry ({attempt+1}/{max_retries})...")
                time.sleep(5 * (attempt + 1))
                continue
            response.raise_for_status()
            return response.text
        raise Exception(f"Failed to fetch {url} after {max_retries} attempts due to rate limiting.")

    def save_html(self, html: str, filename: str) -> None:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)

    def extract_page_info(self, html: str, url: str) -> dict:
        soup = BeautifulSoup(html, 'html.parser')
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        meta_desc = ""
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            meta_desc = meta["content"].strip()
        headings = {tag: [h.get_text(strip=True) for h in soup.find_all(tag)] for tag in ["h1", "h2", "h3"]}
        links = [a['href'] for a in soup.find_all('a', href=True)]
        images = [{"src": img.get("src"), "alt": img.get("alt", "")} for img in soup.find_all("img")]
        text = soup.get_text(separator=" ", strip=True)
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

    def get_all_links(self, soup: BeautifulSoup, current_url: str, base_domain: str) -> Set[str]:
        links = set()
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            full_url = urljoin(current_url, href)
            parsed_url = urlparse(full_url)
            if parsed_url.netloc == base_domain and full_url.startswith(('http://', 'https://')):
                links.add(full_url)
        return links

    def scrape_site_recursive(self, url: str, base_domain: str, visited: Set[str], locationPath: str) -> None:
        filename = os.path.join(locationPath / "scraped_pages", f"{self.safe_filename(url)}.html")
        if url in visited or os.path.exists(filename):
            return
        try:
            html = self.fetch_html(url)
            self.save_html(html, filename)
            self.extract_page_info(html, url)
            soup = BeautifulSoup(html, 'html.parser')
            take_screenshots([url], locationPath / "images")
            links = self.get_all_links(soup, url, base_domain)
            visited.add(url)
            time.sleep(self.sleep_time)
            for link in links:
                self.scrape_site_recursive(link, base_domain, visited, locationPath=locationPath)
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")

    def list_scraped_files(self) -> List[str]:
        if not os.path.exists(self.output_dir):
            return []
        return [f for f in os.listdir(self.output_dir) if f.endswith(".html")]

    def merge_files_with_filenames(self, output_file: str):
        with open(output_file, 'w', encoding='utf-8') as outfile:
            for filename in sorted(os.listdir(self.output_dir)):
                filepath = os.path.join(self.output_dir, filename)
                if os.path.isfile(filepath):
                    outfile.write(f"=== {filename} ===\n")
                    with open(filepath, 'r', encoding='utf-8') as infile:
                        outfile.write(infile.read())
                    outfile.write('\n\n')

    def process_file(self, filepath: str, output_path: str = None):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        matches = re.findall(r'\bhttps?_[\w\-_.]+\.html\b', content)
        for match in matches:
            restored = self.restore_url_string(match)
            print(f"{match} → {restored}")
            content = content.replace(match, restored)
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"\nErgebnis gespeichert in: {output_path}")
        else:
            print("\nErsetzter Inhalt:\n")
            print(content)

    def start_scraping(self, start_url: str, locationPath: str = ""):
        base_domain = urlparse(start_url).netloc
        visited = set()
        self.scrape_site_recursive(start_url, base_domain, visited,locationPath= locationPath)
        scraped_files = self.list_scraped_files()
        print(f"Scraped {len(scraped_files)} pages. Files are in '{self.output_dir}/'.")
