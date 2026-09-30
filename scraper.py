"""
===============================================================================
 AKITS Website Resource Scraper
 -------------------------------------------------------------------------------
 Scrapes ALL resources (images, videos, audio, PDFs, documents, fonts, etc.)
 from https://akits.ac.in/ and its internal pages.

 Usage:
     python scraper.py                      # Scrape with defaults
     python scraper.py --depth 3            # Crawl 3 levels deep
     python scraper.py --output my_folder   # Custom output folder
     python scraper.py --delay 1.5          # 1.5 second delay between requests
     python scraper.py --max-pages 50       # Limit to 50 pages
===============================================================================
"""

import os
import re
import sys
import json
import time
import hashlib
import logging
import argparse
import mimetypes
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# Force UTF-8 output on Windows to avoid cp1252 encoding errors
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

try:
    import requests
except ImportError:
    print("\n[!] 'requests' library not found. Installing...")
    os.system(f"{sys.executable} -m pip install requests")
    import requests

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("\n[!] 'beautifulsoup4' library not found. Installing...")
    os.system(f"{sys.executable} -m pip install beautifulsoup4")
    from bs4 import BeautifulSoup

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    print("[i] Install 'colorama' for colored output: pip install colorama")
    HAS_COLOR = False


# ─────────────────────────── Configuration ───────────────────────────

BASE_URL = "https://akits.ac.in/"

# Regex to detect WordPress auto-generated thumbnail sizes like -300x200, -1024x768
# These are resized copies of the original upload
WP_THUMBNAIL_PATTERN = re.compile(r'-\d{2,4}x\d{2,4}(?=\.[a-zA-Z]{2,5}$)')
DEFAULT_OUTPUT_DIR = "akits_scraped_resources"
DEFAULT_MAX_DEPTH = 2
DEFAULT_DELAY = 0.5  # seconds between page requests
DEFAULT_MAX_PAGES = 100
DOWNLOAD_THREADS = 5  # parallel download threads for resources

# User-Agent to mimic a regular browser
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": BASE_URL,
}

# Resource file extensions by category
RESOURCE_CATEGORIES = {
    "images": {
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp",
        ".ico", ".tiff", ".tif", ".avif", ".heic", ".heif",
    },
    "videos": {
        ".mp4", ".webm", ".avi", ".mov", ".mkv", ".flv",
        ".wmv", ".m4v", ".ogv", ".3gp",
    },
    "audio": {
        ".mp3", ".wav", ".ogg", ".flac", ".aac", ".wma", ".m4a",
    },
    "documents": {
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".txt", ".csv", ".rtf", ".odt", ".ods", ".odp",
    },
    "fonts": {
        ".woff", ".woff2", ".ttf", ".otf", ".eot",
    },
    "stylesheets": {
        ".css",
    },
    "scripts": {
        ".js",
    },
    "archives": {
        ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2",
    },
}

# Flatten all known extensions for quick lookup
ALL_RESOURCE_EXTENSIONS = set()
for exts in RESOURCE_CATEGORIES.values():
    ALL_RESOURCE_EXTENSIONS.update(exts)


# ─────────────────────────── Logging Setup ───────────────────────────

def setup_logging(output_dir: str):
    """Configure logging to both console and file."""
    log_file = os.path.join(output_dir, "scraper.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


# ─────────────────────────── Helper Functions ───────────────────────────

def colorize(text: str, color: str) -> str:
    """Apply color to text if colorama is available."""
    if not HAS_COLOR:
        return text
    color_map = {
        "green": Fore.GREEN,
        "red": Fore.RED,
        "yellow": Fore.YELLOW,
        "cyan": Fore.CYAN,
        "magenta": Fore.MAGENTA,
        "blue": Fore.BLUE,
        "white": Fore.WHITE,
    }
    return f"{color_map.get(color, '')}{text}{Style.RESET_ALL}"


def get_category(url: str) -> str:
    """Determine which category a resource URL belongs to."""
    parsed = urlparse(url)
    path = parsed.path.lower()
    ext = os.path.splitext(path)[1]

    for category, extensions in RESOURCE_CATEGORIES.items():
        if ext in extensions:
            return category

    # Check content-type based guesses
    if "wp-content/uploads" in path:
        return "images"  # Most WP uploads are images
    return "other"


def sanitize_filename(url: str, max_length: int = 200) -> str:
    """Create a safe filename from a URL."""
    parsed = urlparse(url)
    path = unquote(parsed.path)
    filename = os.path.basename(path) or "index"

    # Remove query parameters from filename but keep extension
    if "?" in filename:
        filename = filename.split("?")[0]

    # Clean up special characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)

    # If filename is too long, hash it
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        name_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        filename = f"{name[:max_length - 20]}_{name_hash}{ext}"

    # If no extension, try to guess one
    if not os.path.splitext(filename)[1]:
        ext = mimetypes.guess_extension(mimetypes.guess_type(url)[0] or "") or ""
        filename += ext

    return filename


def is_same_domain(url: str, base_domain: str) -> bool:
    """Check if URL belongs to the same domain."""
    parsed = urlparse(url)
    return parsed.netloc == "" or parsed.netloc == base_domain


def normalize_url(url: str) -> str:
    """Normalize a URL by removing fragments and trailing slashes."""
    parsed = urlparse(url)
    # Remove fragment
    normalized = parsed._replace(fragment="")
    result = normalized.geturl()
    # Remove trailing slash for consistency (except root)
    if result.endswith("/") and result.count("/") > 3:
        result = result.rstrip("/")
    return result


def normalize_resource_url(url: str) -> str:
    """Normalize a resource URL by removing query params, fragments, and trailing slashes.
    This prevents downloading the same file with different ?ver= or ?v= params."""
    parsed = urlparse(url)
    # Remove query string and fragment for resource files
    normalized = parsed._replace(query="", fragment="")
    result = normalized.geturl()
    if result.endswith("/") and result.count("/") > 3:
        result = result.rstrip("/")
    return result


def is_wp_thumbnail(url: str) -> bool:
    """Check if a URL is a WordPress auto-generated thumbnail (e.g., image-300x200.jpg).
    Returns True for resized copies, False for originals."""
    parsed = urlparse(url)
    path = unquote(parsed.path)
    return bool(WP_THUMBNAIL_PATTERN.search(path))


def get_wp_original_url(url: str) -> str:
    """Convert a WordPress thumbnail URL back to its original full-size URL.
    e.g., https://site.com/image-300x200.jpg -> https://site.com/image.jpg"""
    parsed = urlparse(url)
    path = unquote(parsed.path)
    original_path = WP_THUMBNAIL_PATTERN.sub('', path)
    return parsed._replace(path=original_path, query="", fragment="").geturl()


# ─────────────────────────── Scraper Class ───────────────────────────

class WebsiteScraper:
    """
    Comprehensive website resource scraper.
    Crawls pages and extracts all downloadable resources.
    """

    def __init__(
        self,
        base_url: str,
        output_dir: str,
        max_depth: int = DEFAULT_MAX_DEPTH,
        delay: float = DEFAULT_DELAY,
        max_pages: int = DEFAULT_MAX_PAGES,
    ):
        self.base_url = base_url.rstrip("/") + "/"
        self.base_domain = urlparse(base_url).netloc
        self.output_dir = output_dir
        self.max_depth = max_depth
        self.delay = delay
        self.max_pages = max_pages

        self.session = requests.Session()
        self.session.headers.update(HEADERS)

        # Tracking sets
        self.visited_pages: set = set()
        self.found_resources: dict = {}  # url -> category
        self.downloaded_files: set = set()
        self.failed_downloads: list = []
        self.pages_to_visit: list = [(self.base_url, 0)]  # (url, depth)
        self.content_hashes: dict = {}  # hash -> filepath (for content dedup)
        self.skipped_duplicates: int = 0
        self.skipped_thumbnails: int = 0

        # Statistics
        self.stats = defaultdict(int)

        # Create output directories
        self._create_directories()

    def _create_directories(self):
        """Create organized output directory structure."""
        os.makedirs(self.output_dir, exist_ok=True)
        for category in list(RESOURCE_CATEGORIES.keys()) + ["other"]:
            os.makedirs(os.path.join(self.output_dir, category), exist_ok=True)

    def fetch_page(self, url: str) -> str | None:
        """Fetch a web page and return its HTML content."""
        try:
            response = self.session.get(url, timeout=30, allow_redirects=True)
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type and "text/xml" not in content_type:
                return None
            return response.text
        except requests.RequestException as e:
            logging.warning(f"Failed to fetch {url}: {e}")
            return None

    def extract_resources(self, html: str, page_url: str):
        """Extract all resource URLs from HTML content."""
        soup = BeautifulSoup(html, "html.parser")
        resources = set()

        # ── Images ──
        # <img src="..."> and data-src (lazy loading)
        for img in soup.find_all("img"):
            for attr in ["src", "data-src", "data-lazy-src", "data-original",
                         "data-srcset", "srcset"]:
                val = img.get(attr)
                if val:
                    if attr in ("srcset", "data-srcset"):
                        # Parse srcset: "url1 1x, url2 2x"
                        for part in val.split(","):
                            src = part.strip().split()[0]
                            if src:
                                resources.add(urljoin(page_url, src))
                    else:
                        resources.add(urljoin(page_url, val))

        # <picture><source srcset="...">
        for source in soup.find_all("source"):
            for attr in ["src", "srcset", "data-srcset"]:
                val = source.get(attr)
                if val:
                    if attr in ("srcset", "data-srcset"):
                        for part in val.split(","):
                            src = part.strip().split()[0]
                            if src:
                                resources.add(urljoin(page_url, src))
                    else:
                        resources.add(urljoin(page_url, val))

        # ── Videos ──
        for video in soup.find_all("video"):
            src = video.get("src") or video.get("data-src")
            if src:
                resources.add(urljoin(page_url, src))
            poster = video.get("poster")
            if poster:
                resources.add(urljoin(page_url, poster))

        # <video><source src="...">
        for source in soup.find_all("source"):
            src = source.get("src")
            if src:
                resources.add(urljoin(page_url, src))

        # Embedded YouTube / Vimeo iframes
        for iframe in soup.find_all("iframe"):
            src = iframe.get("src") or iframe.get("data-src")
            if src:
                resources.add(urljoin(page_url, src))

        # ── Audio ──
        for audio in soup.find_all("audio"):
            src = audio.get("src")
            if src:
                resources.add(urljoin(page_url, src))

        # ── Documents & Links ──
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            full_url = urljoin(page_url, href)
            ext = os.path.splitext(urlparse(full_url).path.lower())[1]
            if ext in ALL_RESOURCE_EXTENSIONS:
                resources.add(full_url)

        # ── Stylesheets ──
        for link in soup.find_all("link", rel=True):
            href = link.get("href")
            if href:
                full_url = urljoin(page_url, href)
                rel = " ".join(link.get("rel", []))
                if "stylesheet" in rel or full_url.endswith(".css"):
                    resources.add(full_url)
                elif "icon" in rel:
                    resources.add(full_url)

        # ── Scripts ──
        for script in soup.find_all("script", src=True):
            resources.add(urljoin(page_url, script["src"]))

        # ── Background images in inline styles ──
        style_pattern = re.compile(r'url\(["\']?(.*?)["\']?\)')
        for tag in soup.find_all(style=True):
            style = tag["style"]
            for match in style_pattern.findall(style):
                if match and not match.startswith("data:"):
                    resources.add(urljoin(page_url, match))

        # ── Style blocks ──
        for style_tag in soup.find_all("style"):
            if style_tag.string:
                for match in style_pattern.findall(style_tag.string):
                    if match and not match.startswith("data:"):
                        resources.add(urljoin(page_url, match))

        # ── Meta tags (og:image, twitter:image, etc.) ──
        for meta in soup.find_all("meta"):
            content = meta.get("content", "")
            prop = meta.get("property", "") or meta.get("name", "")
            if any(k in prop.lower() for k in ["image", "video", "audio"]):
                if content and (content.startswith("http") or content.startswith("/")):
                    resources.add(urljoin(page_url, content))

        # ── JSON-LD schema images ──
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                self._extract_json_urls(data, page_url, resources)
            except (json.JSONDecodeError, TypeError):
                pass

        # ── Smart Slider / Elementor data attributes ──
        for tag in soup.find_all(attrs={"data-bg": True}):
            resources.add(urljoin(page_url, tag["data-bg"]))
        for tag in soup.find_all(attrs={"data-background-image": True}):
            resources.add(urljoin(page_url, tag["data-background-image"]))
        for tag in soup.find_all(attrs={"data-thumb": True}):
            resources.add(urljoin(page_url, tag["data-thumb"]))

        # Categorize and store (with URL normalization)
        for url in resources:
            if url and not url.startswith("data:") and not url.startswith("javascript:"):
                # Normalize the resource URL (strip query params, fragments)
                url = normalize_resource_url(url)
                if url not in self.found_resources:
                    category = get_category(url)
                    self.found_resources[url] = category

    def _extract_json_urls(self, data, page_url: str, resources: set):
        """Recursively extract URLs from JSON-LD data."""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str) and (
                    value.startswith("http") or value.startswith("/")
                ):
                    ext = os.path.splitext(urlparse(value).path.lower())[1]
                    if ext in ALL_RESOURCE_EXTENSIONS or "image" in key.lower():
                        resources.add(urljoin(page_url, value))
                else:
                    self._extract_json_urls(value, page_url, resources)
        elif isinstance(data, list):
            for item in data:
                self._extract_json_urls(item, page_url, resources)

    def extract_links(self, html: str, page_url: str) -> list:
        """Extract internal page links for crawling."""
        soup = BeautifulSoup(html, "html.parser")
        links = []

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            full_url = urljoin(page_url, href)
            full_url = normalize_url(full_url)

            # Only follow internal links
            if not is_same_domain(full_url, self.base_domain):
                continue

            # Skip anchors, mailto, tel, javascript
            if any(href.startswith(p) for p in ["#", "mailto:", "tel:", "javascript:"]):
                continue

            # Skip resource files
            ext = os.path.splitext(urlparse(full_url).path.lower())[1]
            if ext in ALL_RESOURCE_EXTENSIONS:
                continue

            if full_url not in self.visited_pages:
                links.append(full_url)

        return links

    def deduplicate_resources(self):
        """Remove duplicate resources before downloading.
        
        Deduplication strategy:
        1. WordPress thumbnails: Keep only the original full-size image,
           skip resized variants like image-300x200.jpg, image-1024x768.jpg
        2. URL normalization already handled during extraction (query params stripped)
        """
        original_count = len(self.found_resources)
        cleaned = {}
        wp_originals_seen = set()  # track original URLs we've already kept

        # First pass: identify all originals and their thumbnails
        for url, category in list(self.found_resources.items()):
            if category == "images" and is_wp_thumbnail(url):
                # This is a thumbnail — check if we have/can get the original
                original_url = get_wp_original_url(url)
                wp_originals_seen.add(original_url)
                # Skip this thumbnail; we'll keep the original instead
                self.skipped_thumbnails += 1
                continue
            cleaned[url] = category

        # Second pass: ensure originals for detected thumbnails are included
        for original_url in wp_originals_seen:
            if original_url not in cleaned:
                category = get_category(original_url)
                cleaned[original_url] = category

        self.found_resources = cleaned
        removed = original_count - len(self.found_resources)

        if removed > 0:
            logging.info(
                f"  Deduplication: removed {colorize(str(removed), 'yellow')} duplicate/thumbnail URLs "
                f"({colorize(str(self.skipped_thumbnails), 'yellow')} WP thumbnails skipped)"
            )
            logging.info(
                f"  Unique resources to download: {colorize(str(len(self.found_resources)), 'green')}"
            )

    def download_resource(self, url: str, category: str) -> bool:
        """Download a single resource file with content-hash deduplication."""
        if url in self.downloaded_files:
            return True

        try:
            filename = sanitize_filename(url)

            # Handle duplicate filenames by adding a hash
            filepath = os.path.join(self.output_dir, category, filename)
            if os.path.exists(filepath):
                name, ext = os.path.splitext(filename)
                url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                filename = f"{name}_{url_hash}{ext}"
                filepath = os.path.join(self.output_dir, category, filename)

            response = self.session.get(url, timeout=30, stream=True)
            response.raise_for_status()

            # Download to memory first for hashing
            content_chunks = []
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    content_chunks.append(chunk)
            file_content = b"".join(content_chunks)

            # Content-hash deduplication: skip if identical content already downloaded
            content_hash = hashlib.md5(file_content).hexdigest()
            if content_hash in self.content_hashes:
                self.skipped_duplicates += 1
                self.downloaded_files.add(url)
                logging.info(
                    f"  {colorize('[SKIP]', 'yellow')} [{category:12s}] "
                    f"{colorize(filename[:50], 'cyan')} (duplicate of {os.path.basename(self.content_hashes[content_hash])})"
                )
                return True

            # Write file
            with open(filepath, "wb") as f:
                f.write(file_content)

            actual_size = len(file_content)
            self.content_hashes[content_hash] = filepath
            self.downloaded_files.add(url)
            self.stats[category] += 1
            self.stats["total_bytes"] += actual_size

            size_str = self._format_size(actual_size)
            logging.info(
                f"  {colorize('[OK]', 'green')} [{category:12s}] "
                f"{colorize(filename[:60], 'cyan')} ({size_str})"
            )
            return True

        except requests.RequestException as e:
            self.failed_downloads.append({"url": url, "error": str(e)})
            logging.warning(
                f"  {colorize('[FAIL]', 'red')} [{category:12s}] "
                f"Failed: {url[:80]} - {e}"
            )
            return False

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format bytes into a human-readable string."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def crawl(self):
        """Main crawling loop — discovers pages and extracts resources."""
        print(f"\n{'=' * 70}")
        print(f"  {colorize('AKITS WEBSITE RESOURCE SCRAPER', 'cyan')}")
        print(f"  Target: {colorize(self.base_url, 'yellow')}")
        print(f"  Depth:  {self.max_depth} | Max Pages: {self.max_pages}")
        print(f"  Output: {colorize(os.path.abspath(self.output_dir), 'green')}")
        print(f"{'=' * 70}\n")

        logging.info("Starting crawl...")

        while self.pages_to_visit and len(self.visited_pages) < self.max_pages:
            url, depth = self.pages_to_visit.pop(0)

            if url in self.visited_pages:
                continue
            if depth > self.max_depth:
                continue

            self.visited_pages.add(url)
            page_num = len(self.visited_pages)

            logging.info(
                f"\n{'-' * 60}\n"
                f"  {colorize(f'Page [{page_num}/{self.max_pages}]', 'magenta')} "
                f"(depth={depth}) → {colorize(url, 'yellow')}"
            )

            # Fetch page
            html = self.fetch_page(url)
            if not html:
                continue

            # Extract resources from this page
            prev_count = len(self.found_resources)
            self.extract_resources(html, url)
            new_count = len(self.found_resources) - prev_count
            logging.info(
                f"  Found {colorize(str(new_count), 'green')} new resources on this page"
            )

            # Extract links for further crawling
            if depth < self.max_depth:
                new_links = self.extract_links(html, url)
                for link in new_links:
                    if link not in self.visited_pages:
                        self.pages_to_visit.append((link, depth + 1))
                logging.info(
                    f"  Queued {colorize(str(len(new_links)), 'blue')} new internal links"
                )

            # Be polite — wait between page requests
            time.sleep(self.delay)

        logging.info(
            f"\n{'=' * 60}\n"
            f"  Crawling complete! Visited {len(self.visited_pages)} pages.\n"
            f"  Total resources found: {colorize(str(len(self.found_resources)), 'green')}\n"
            f"{'=' * 60}"
        )

        # Deduplicate before downloading
        logging.info("\n  Running deduplication...")
        self.deduplicate_resources()

    def download_all(self):
        """Download all discovered resources using parallel threads."""
        if not self.found_resources:
            logging.warning("No resources found to download.")
            return

        # Group resources by category for display
        category_counts = defaultdict(int)
        for url, cat in self.found_resources.items():
            category_counts[cat] += 1

        print(f"\n{'=' * 60}")
        print(f"  {colorize('DOWNLOAD SUMMARY', 'cyan')}")
        print(f"{'-' * 60}")
        for cat, count in sorted(category_counts.items()):
            print(f"  {cat:15s} : {colorize(str(count), 'yellow')} files")
        print(f"{'-' * 60}")
        print(f"  {'Total':15s} : {colorize(str(len(self.found_resources)), 'green')} files")
        print(f"{'=' * 60}\n")

        logging.info(f"Starting downloads with {DOWNLOAD_THREADS} threads...\n")

        # Download using thread pool for speed
        with ThreadPoolExecutor(max_workers=DOWNLOAD_THREADS) as executor:
            futures = {}
            for url, category in self.found_resources.items():
                if url not in self.downloaded_files:
                    future = executor.submit(self.download_resource, url, category)
                    futures[future] = (url, category)

            completed = 0
            total = len(futures)
            for future in as_completed(futures):
                completed += 1
                if completed % 25 == 0:
                    logging.info(
                        f"  Progress: {colorize(f'{completed}/{total}', 'magenta')} downloads completed"
                    )

    def save_report(self):
        """Save a detailed JSON report of all scraped resources."""
        report = {
            "target_url": self.base_url,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "pages_visited": len(self.visited_pages),
            "total_resources_found": len(self.found_resources),
            "total_downloaded": len(self.downloaded_files),
            "total_failed": len(self.failed_downloads),
            "total_size": self._format_size(self.stats.get("total_bytes", 0)),
            "resources_by_category": {},
            "visited_pages": sorted(self.visited_pages),
            "failed_downloads": self.failed_downloads,
        }

        # Group resources by category
        by_category = defaultdict(list)
        for url, cat in self.found_resources.items():
            by_category[cat].append(url)

        for cat in sorted(by_category):
            report["resources_by_category"][cat] = {
                "count": len(by_category[cat]),
                "urls": sorted(by_category[cat]),
            }

        report_path = os.path.join(self.output_dir, "scrape_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        # Also save a simple URL list
        urls_path = os.path.join(self.output_dir, "all_resource_urls.txt")
        with open(urls_path, "w", encoding="utf-8") as f:
            for cat in sorted(by_category):
                f.write(f"\n{'=' * 60}\n")
                f.write(f"  {cat.upper()} ({len(by_category[cat])} files)\n")
                f.write(f"{'=' * 60}\n")
                for url in sorted(by_category[cat]):
                    f.write(f"  {url}\n")

        logging.info(f"\n  Report saved to: {colorize(report_path, 'cyan')}")
        logging.info(f"  URL list saved to: {colorize(urls_path, 'cyan')}")

    def print_final_stats(self):
        """Print final statistics."""
        print(f"\n{'=' * 70}")
        print(f"  {colorize('FINAL STATISTICS', 'cyan')}")
        print(f"{'-' * 70}")
        print(f"  Pages crawled      : {colorize(str(len(self.visited_pages)), 'yellow')}")
        print(f"  Unique resources   : {colorize(str(len(self.found_resources)), 'yellow')}")
        print(f"  Downloaded         : {colorize(str(len(self.downloaded_files)), 'green')}")
        print(f"  Content duplicates : {colorize(str(self.skipped_duplicates), 'yellow')} skipped")
        print(f"  WP thumbnails      : {colorize(str(self.skipped_thumbnails), 'yellow')} skipped")
        print(f"  Failed             : {colorize(str(len(self.failed_downloads)), 'red')}")
        print(f"  Total size         : {colorize(self._format_size(self.stats.get('total_bytes', 0)), 'magenta')}")
        print(f"{'-' * 70}")
        print(f"  Downloads by category:")
        for cat in sorted(RESOURCE_CATEGORIES.keys()):
            count = self.stats.get(cat, 0)
            if count > 0:
                print(f"    {cat:15s} : {colorize(str(count), 'green')} files")
        other_count = self.stats.get("other", 0)
        if other_count > 0:
            print(f"    {'other':15s} : {colorize(str(other_count), 'green')} files")
        print(f"{'-' * 70}")
        print(f"  Output directory   : {colorize(os.path.abspath(self.output_dir), 'green')}")
        print(f"{'=' * 70}\n")

    def run(self):
        """Run the complete scraping pipeline."""
        try:
            # Phase 1: Crawl pages and discover resources
            self.crawl()

            # Phase 2: Download all discovered resources
            self.download_all()

            # Phase 3: Save report
            self.save_report()

            # Phase 4: Print stats
            self.print_final_stats()

        except KeyboardInterrupt:
            print(f"\n\n{colorize('[!] Scraping interrupted by user!', 'yellow')}")
            print("Saving partial results...\n")
            self.save_report()
            self.print_final_stats()

        except Exception as e:
            logging.error(f"Unexpected error: {e}", exc_info=True)
            self.save_report()
            raise


# ─────────────────────────── Main Entry Point ───────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="🕸️  AKITS Website Resource Scraper — Download all images, videos, and files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scraper.py                          # Default scrape
  python scraper.py --depth 3 --max-pages 200   # Deep crawl
  python scraper.py --output ./downloads     # Custom output folder
  python scraper.py --delay 2                # Slower, polite crawl
        """,
    )
    parser.add_argument(
        "--url", default=BASE_URL,
        help=f"Target website URL (default: {BASE_URL})"
    )
    parser.add_argument(
        "--output", "-o", default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "--depth", "-d", type=int, default=DEFAULT_MAX_DEPTH,
        help=f"Maximum crawl depth (default: {DEFAULT_MAX_DEPTH})"
    )
    parser.add_argument(
        "--delay", type=float, default=DEFAULT_DELAY,
        help=f"Delay between page requests in seconds (default: {DEFAULT_DELAY})"
    )
    parser.add_argument(
        "--max-pages", "-m", type=int, default=DEFAULT_MAX_PAGES,
        help=f"Maximum pages to crawl (default: {DEFAULT_MAX_PAGES})"
    )

    args = parser.parse_args()

    # Create output dir and setup logging
    os.makedirs(args.output, exist_ok=True)
    setup_logging(args.output)

    # Run scraper
    scraper = WebsiteScraper(
        base_url=args.url,
        output_dir=args.output,
        max_depth=args.depth,
        delay=args.delay,
        max_pages=args.max_pages,
    )
    scraper.run()


if __name__ == "__main__":
    main()
