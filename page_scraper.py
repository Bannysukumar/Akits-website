"""
===============================================================================
 AKITS Full Page Source Code Scraper
 -------------------------------------------------------------------------------
 Downloads the COMPLETE HTML source code of every page on https://akits.ac.in/
 Including: navigation bar, header, footer, all content, image/video paths,
 inline styles, scripts — the entire page as the browser sees it.

 Usage:
     python page_scraper.py                        # Scrape with defaults
     python page_scraper.py --depth 3              # Crawl 3 levels deep
     python page_scraper.py --max-pages 200        # Scrape up to 200 pages
     python page_scraper.py --output my_pages      # Custom output folder
===============================================================================
"""

import os
import re
import sys
import json
import time
import logging
import argparse
from urllib.parse import urljoin, urlparse, unquote, quote
from collections import defaultdict

# Force UTF-8 output on Windows
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
    HAS_COLOR = False


# ----------------------------- Configuration ---------------------------------

BASE_URL = "https://akits.ac.in/"
DEFAULT_OUTPUT_DIR = "akits_pages_source"
DEFAULT_MAX_DEPTH = 2
DEFAULT_DELAY = 0.5
DEFAULT_MAX_PAGES = 200

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


# ----------------------------- Helpers ---------------------------------------

def colorize(text, color):
    if not HAS_COLOR:
        return text
    colors = {
        "green": Fore.GREEN, "red": Fore.RED, "yellow": Fore.YELLOW,
        "cyan": Fore.CYAN, "magenta": Fore.MAGENTA, "blue": Fore.BLUE,
    }
    return f"{colors.get(color, '')}{text}{Style.RESET_ALL}"


def setup_logging(output_dir):
    log_file = os.path.join(output_dir, "page_scraper.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def url_to_filepath(url, base_domain):
    """Convert a URL into a safe local file path that mirrors the site structure.
    
    Examples:
        https://akits.ac.in/                     -> index.html
        https://akits.ac.in/about                -> about/index.html
        https://akits.ac.in/academics/regulations -> academics/regulations/index.html
    """
    parsed = urlparse(url)
    path = unquote(parsed.path).strip("/")

    if not path:
        return "index.html"

    # Clean up path segments
    segments = [re.sub(r'[<>:"|?*]', '_', seg) for seg in path.split("/") if seg]

    # If the last segment already has an extension, keep it
    if segments and "." in segments[-1]:
        return os.path.join(*segments)

    # Otherwise treat it as a directory and add index.html
    segments.append("index.html")
    return os.path.join(*segments)


def normalize_url(url):
    """Normalize URL by removing fragments and trailing slashes."""
    parsed = urlparse(url)
    normalized = parsed._replace(fragment="")
    result = normalized.geturl()
    if result.endswith("/") and result.count("/") > 3:
        result = result.rstrip("/")
    return result


def is_same_domain(url, base_domain):
    parsed = urlparse(url)
    return parsed.netloc == "" or parsed.netloc == base_domain


# ----------------------------- Scraper Class ---------------------------------

class FullPageScraper:
    """
    Scrapes the complete HTML source code of every page on a website.
    Saves full page HTML including header, navigation, footer, and all content.
    """

    def __init__(self, base_url, output_dir, max_depth, delay, max_pages):
        self.base_url = base_url.rstrip("/") + "/"
        self.base_domain = urlparse(base_url).netloc
        self.output_dir = output_dir
        self.max_depth = max_depth
        self.delay = delay
        self.max_pages = max_pages

        self.session = requests.Session()
        self.session.headers.update(HEADERS)

        self.visited_pages = set()
        self.pages_to_visit = [(self.base_url, 0)]
        self.saved_pages = {}       # url -> local filepath
        self.page_metadata = {}     # url -> {title, description, resources}
        self.failed_pages = []

        self.stats = defaultdict(int)

        os.makedirs(output_dir, exist_ok=True)

    def fetch_page(self, url):
        """Fetch a page and return (html, final_url) after redirects."""
        try:
            response = self.session.get(url, timeout=30, allow_redirects=True)
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                return None, url
            # Handle encoding properly
            response.encoding = response.apparent_encoding or 'utf-8'
            return response.text, response.url
        except requests.RequestException as e:
            logging.warning(f"  Failed to fetch: {url} - {e}")
            self.failed_pages.append({"url": url, "error": str(e)})
            return None, url

    def extract_page_info(self, html, page_url):
        """Extract metadata and resource counts from a page."""
        soup = BeautifulSoup(html, "html.parser")
        info = {
            "title": "",
            "meta_description": "",
            "images": 0,
            "videos": 0,
            "iframes": 0,
            "links": 0,
            "scripts": 0,
            "stylesheets": 0,
            "forms": 0,
        }

        # Title
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            info["title"] = title_tag.string.strip()

        # Meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            info["meta_description"] = meta_desc.get("content", "")

        # Count resources
        info["images"] = len(soup.find_all("img"))
        info["videos"] = len(soup.find_all("video"))
        info["iframes"] = len(soup.find_all("iframe"))
        info["links"] = len(soup.find_all("a", href=True))
        info["scripts"] = len(soup.find_all("script"))
        info["stylesheets"] = len(soup.find_all("link", rel=lambda x: x and "stylesheet" in x))
        info["forms"] = len(soup.find_all("form"))

        return info

    def extract_all_resource_paths(self, html, page_url):
        """Extract and list all resource paths found in the page."""
        soup = BeautifulSoup(html, "html.parser")
        resources = {
            "images": [],
            "videos": [],
            "audio": [],
            "iframes": [],
            "stylesheets": [],
            "scripts": [],
            "documents": [],
            "other_links": [],
        }

        # Images
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if src:
                resources["images"].append(urljoin(page_url, src))

        # Videos
        for video in soup.find_all("video"):
            src = video.get("src") or video.get("data-src")
            if src:
                resources["videos"].append(urljoin(page_url, src))
            for source in video.find_all("source"):
                src = source.get("src")
                if src:
                    resources["videos"].append(urljoin(page_url, src))

        # Audio
        for audio in soup.find_all("audio"):
            src = audio.get("src")
            if src:
                resources["audio"].append(urljoin(page_url, src))

        # Iframes (YouTube, Vimeo, etc.)
        for iframe in soup.find_all("iframe"):
            src = iframe.get("src") or iframe.get("data-src")
            if src:
                resources["iframes"].append(urljoin(page_url, src))

        # Stylesheets
        for link in soup.find_all("link", rel=True):
            if "stylesheet" in " ".join(link.get("rel", [])):
                href = link.get("href")
                if href:
                    resources["stylesheets"].append(urljoin(page_url, href))

        # Scripts
        for script in soup.find_all("script", src=True):
            resources["scripts"].append(urljoin(page_url, script["src"]))

        # Document links (PDFs, docs, etc.)
        doc_extensions = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".csv", ".txt"}
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            full_url = urljoin(page_url, href)
            ext = os.path.splitext(urlparse(full_url).path.lower())[1]
            if ext in doc_extensions:
                resources["documents"].append(full_url)

        return resources

    def extract_internal_links(self, html, page_url):
        """Extract all internal navigation links for crawling."""
        soup = BeautifulSoup(html, "html.parser")
        links = []

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            full_url = urljoin(page_url, href)
            full_url = normalize_url(full_url)

            if not is_same_domain(full_url, self.base_domain):
                continue
            if any(href.startswith(p) for p in ["#", "mailto:", "tel:", "javascript:"]):
                continue

            # Skip non-HTML resources
            ext = os.path.splitext(urlparse(full_url).path.lower())[1]
            skip_exts = {
                ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
                ".mp4", ".mp3", ".pdf", ".doc", ".docx", ".xls", ".xlsx",
                ".zip", ".rar", ".css", ".js", ".woff", ".woff2", ".ttf",
                ".ppt", ".pptx", ".csv", ".bmp", ".tiff",
            }
            if ext in skip_exts:
                continue

            if full_url not in self.visited_pages:
                links.append(full_url)

        return list(set(links))  # deduplicate

    def save_page(self, url, html):
        """Save the complete HTML source code to a local file."""
        rel_path = url_to_filepath(url, self.base_domain)
        full_path = os.path.join(self.output_dir, rel_path)

        # Create parent directories
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # Add a comment header to the HTML with the source URL and timestamp
        header_comment = (
            f"<!-- \n"
            f"  SOURCE URL: {url}\n"
            f"  SCRAPED AT: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"  This is the complete HTML source code of the page.\n"
            f"-->\n"
        )

        with open(full_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(header_comment + html)

        self.saved_pages[url] = rel_path
        file_size = os.path.getsize(full_path)
        self.stats["total_bytes"] += file_size
        self.stats["pages_saved"] += 1

        return rel_path, file_size

    def save_resource_map(self, url, resources, rel_path):
        """Save a JSON file with all resource paths found on a page."""
        json_path = os.path.splitext(
            os.path.join(self.output_dir, rel_path)
        )[0] + "_resources.json"

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({
                "source_url": url,
                "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "resources": resources,
            }, f, indent=2, ensure_ascii=False)

    @staticmethod
    def _format_size(size_bytes):
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def crawl_and_save(self):
        """Main crawling loop - discovers and saves all pages."""
        print(f"\n{'=' * 70}")
        print(f"  {colorize('AKITS FULL PAGE SOURCE CODE SCRAPER', 'cyan')}")
        print(f"  Target: {colorize(self.base_url, 'yellow')}")
        print(f"  Depth:  {self.max_depth} | Max Pages: {self.max_pages}")
        print(f"  Output: {colorize(os.path.abspath(self.output_dir), 'green')}")
        print(f"{'=' * 70}\n")

        logging.info("Starting full page crawl...\n")

        while self.pages_to_visit and len(self.visited_pages) < self.max_pages:
            url, depth = self.pages_to_visit.pop(0)

            if url in self.visited_pages:
                continue
            if depth > self.max_depth:
                continue

            self.visited_pages.add(url)
            page_num = len(self.visited_pages)

            logging.info(
                f"{'-' * 60}\n"
                f"  {colorize(f'Page [{page_num}/{self.max_pages}]', 'magenta')} "
                f"(depth={depth})\n"
                f"  URL: {colorize(url, 'yellow')}"
            )

            # Fetch the complete page HTML
            html, final_url = self.fetch_page(url)
            if not html:
                logging.warning(f"  Skipped (no HTML content)")
                continue

            # If redirected, track the final URL too
            if final_url != url:
                self.visited_pages.add(normalize_url(final_url))

            # Extract page metadata
            page_info = self.extract_page_info(html, final_url)
            self.page_metadata[url] = page_info

            title = page_info["title"][:60] if page_info["title"] else "(No title)"
            logging.info(f"  Title: {colorize(title, 'cyan')}")
            logging.info(
                f"  Content: {page_info['images']} images, "
                f"{page_info['videos']} videos, "
                f"{page_info['iframes']} iframes, "
                f"{page_info['links']} links, "
                f"{page_info['forms']} forms"
            )

            # Save the complete HTML source code
            rel_path, file_size = self.save_page(url, html)
            logging.info(
                f"  {colorize('[SAVED]', 'green')} -> {colorize(rel_path, 'cyan')} "
                f"({self._format_size(file_size)})"
            )

            # Extract and save all resource paths
            resources = self.extract_all_resource_paths(html, final_url)
            resource_count = sum(len(v) for v in resources.values())
            if resource_count > 0:
                self.save_resource_map(url, resources, rel_path)
                logging.info(
                    f"  Resources: {resource_count} paths saved to _resources.json"
                )

            # Extract internal links for further crawling
            if depth < self.max_depth:
                new_links = self.extract_internal_links(html, final_url)
                queued = 0
                for link in new_links:
                    if link not in self.visited_pages:
                        self.pages_to_visit.append((link, depth + 1))
                        queued += 1
                if queued > 0:
                    logging.info(
                        f"  Queued {colorize(str(queued), 'blue')} new internal links"
                    )

            # Be polite
            time.sleep(self.delay)

        logging.info(
            f"\n{'=' * 60}\n"
            f"  Crawling complete!\n"
            f"  Pages saved: {colorize(str(self.stats['pages_saved']), 'green')}\n"
            f"{'=' * 60}"
        )

    def save_sitemap(self):
        """Save a complete sitemap/index of all scraped pages."""
        sitemap = {
            "target_url": self.base_url,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_pages": self.stats["pages_saved"],
            "total_size": self._format_size(self.stats.get("total_bytes", 0)),
            "failed_pages": len(self.failed_pages),
            "pages": [],
        }

        for url in sorted(self.saved_pages.keys()):
            rel_path = self.saved_pages[url]
            meta = self.page_metadata.get(url, {})
            sitemap["pages"].append({
                "url": url,
                "local_path": rel_path,
                "title": meta.get("title", ""),
                "description": meta.get("meta_description", ""),
                "images": meta.get("images", 0),
                "videos": meta.get("videos", 0),
                "iframes": meta.get("iframes", 0),
                "links": meta.get("links", 0),
            })

        if self.failed_pages:
            sitemap["failed"] = self.failed_pages

        # Save JSON sitemap
        sitemap_path = os.path.join(self.output_dir, "sitemap.json")
        with open(sitemap_path, "w", encoding="utf-8") as f:
            json.dump(sitemap, f, indent=2, ensure_ascii=False)

        # Save a human-readable HTML index page
        self._save_html_index(sitemap)

        logging.info(f"\n  Sitemap saved to: {colorize(sitemap_path, 'cyan')}")
        logging.info(f"  HTML index saved to: {colorize('_index.html', 'cyan')}")

    def _save_html_index(self, sitemap):
        """Generate a beautiful HTML index page listing all scraped pages."""
        pages_html = ""
        for i, page in enumerate(sitemap["pages"], 1):
            title = page["title"] or "(Untitled)"
            desc = page["description"][:120] + "..." if len(page.get("description", "")) > 120 else page.get("description", "")
            pages_html += f"""
            <tr>
                <td>{i}</td>
                <td>
                    <a href="{page['local_path']}" class="page-link">{title}</a>
                    <div class="url">{page['url']}</div>
                    {"<div class='desc'>" + desc + "</div>" if desc else ""}
                </td>
                <td><a href="{page['local_path']}" class="file-link">{page['local_path']}</a></td>
                <td>{page['images']}</td>
                <td>{page['videos']}</td>
                <td>{page['links']}</td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AKITS Website - Scraped Pages Index</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            padding: 2rem;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{
            font-size: 2rem;
            background: linear-gradient(135deg, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}
        .subtitle {{ color: #94a3b8; margin-bottom: 2rem; }}
        .stats {{
            display: flex; gap: 1.5rem; margin-bottom: 2rem; flex-wrap: wrap;
        }}
        .stat {{
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 1rem 1.5rem;
            min-width: 160px;
        }}
        .stat-value {{
            font-size: 1.8rem; font-weight: 700;
            background: linear-gradient(135deg, #38bdf8, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .stat-label {{ color: #94a3b8; font-size: 0.85rem; margin-top: 4px; }}
        table {{
            width: 100%; border-collapse: collapse;
            background: #1e293b; border-radius: 12px; overflow: hidden;
        }}
        th {{
            background: #334155; padding: 12px 16px; text-align: left;
            font-weight: 600; font-size: 0.85rem; text-transform: uppercase;
            letter-spacing: 0.05em; color: #94a3b8;
        }}
        td {{ padding: 12px 16px; border-bottom: 1px solid #334155; vertical-align: top; }}
        tr:hover td {{ background: #263548; }}
        a {{ color: #38bdf8; text-decoration: none; }}
        a:hover {{ text-decoration: underline; color: #7dd3fc; }}
        .page-link {{ font-weight: 600; font-size: 1rem; }}
        .url {{ font-size: 0.78rem; color: #64748b; margin-top: 4px; word-break: break-all; }}
        .desc {{ font-size: 0.82rem; color: #94a3b8; margin-top: 4px; }}
        .file-link {{ font-size: 0.82rem; color: #a78bfa; font-family: monospace; }}
        .search-box {{
            width: 100%; padding: 12px 16px; margin-bottom: 1.5rem;
            background: #1e293b; border: 1px solid #334155; border-radius: 8px;
            color: #e2e8f0; font-size: 1rem; outline: none;
        }}
        .search-box:focus {{ border-color: #38bdf8; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>AKITS Website - Scraped Pages</h1>
        <p class="subtitle">
            Complete HTML source code of {sitemap['total_pages']} pages from
            <a href="{self.base_url}">{self.base_url}</a>
            | Scraped on {sitemap['timestamp']}
        </p>

        <div class="stats">
            <div class="stat">
                <div class="stat-value">{sitemap['total_pages']}</div>
                <div class="stat-label">Pages Saved</div>
            </div>
            <div class="stat">
                <div class="stat-value">{sitemap['total_size']}</div>
                <div class="stat-label">Total Size</div>
            </div>
            <div class="stat">
                <div class="stat-value">{sitemap['failed_pages']}</div>
                <div class="stat-label">Failed</div>
            </div>
        </div>

        <input type="text" class="search-box" id="search"
               placeholder="Search pages by title, URL, or path..."
               oninput="filterTable()">

        <table id="pages-table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Page Title / URL</th>
                    <th>Local File</th>
                    <th>Images</th>
                    <th>Videos</th>
                    <th>Links</th>
                </tr>
            </thead>
            <tbody>
                {pages_html}
            </tbody>
        </table>
    </div>

    <script>
        function filterTable() {{
            const query = document.getElementById('search').value.toLowerCase();
            const rows = document.querySelectorAll('#pages-table tbody tr');
            rows.forEach(row => {{
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(query) ? '' : 'none';
            }});
        }}
    </script>
</body>
</html>"""

        index_path = os.path.join(self.output_dir, "_index.html")
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(html)

    def print_final_stats(self):
        """Print final statistics."""
        print(f"\n{'=' * 70}")
        print(f"  {colorize('FINAL STATISTICS', 'cyan')}")
        print(f"{'-' * 70}")
        print(f"  Pages crawled      : {colorize(str(len(self.visited_pages)), 'yellow')}")
        print(f"  Pages saved        : {colorize(str(self.stats['pages_saved']), 'green')}")
        print(f"  Failed             : {colorize(str(len(self.failed_pages)), 'red')}")
        print(f"  Total HTML size    : {colorize(self._format_size(self.stats.get('total_bytes', 0)), 'magenta')}")
        print(f"{'-' * 70}")
        print(f"  Output directory   : {colorize(os.path.abspath(self.output_dir), 'green')}")
        print(f"  HTML index         : {colorize('_index.html', 'cyan')}")
        print(f"  Sitemap            : {colorize('sitemap.json', 'cyan')}")
        print(f"{'=' * 70}\n")

    def run(self):
        """Run the complete page scraping pipeline."""
        try:
            self.crawl_and_save()
            self.save_sitemap()
            self.print_final_stats()
        except KeyboardInterrupt:
            print(f"\n\n{colorize('[!] Scraping interrupted by user!', 'yellow')}")
            print("Saving partial results...\n")
            self.save_sitemap()
            self.print_final_stats()
        except Exception as e:
            logging.error(f"Unexpected error: {e}", exc_info=True)
            self.save_sitemap()
            raise


# ----------------------------- Main ------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="AKITS Full Page Source Code Scraper - Download complete HTML of every page",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python page_scraper.py                            # Default scrape
  python page_scraper.py --depth 3 --max-pages 200  # Deep crawl
  python page_scraper.py --output ./my_pages         # Custom output
        """,
    )
    parser.add_argument("--url", default=BASE_URL, help=f"Target URL (default: {BASE_URL})")
    parser.add_argument("--output", "-o", default=DEFAULT_OUTPUT_DIR, help=f"Output dir (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--depth", "-d", type=int, default=DEFAULT_MAX_DEPTH, help=f"Max depth (default: {DEFAULT_MAX_DEPTH})")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help=f"Delay in seconds (default: {DEFAULT_DELAY})")
    parser.add_argument("--max-pages", "-m", type=int, default=DEFAULT_MAX_PAGES, help=f"Max pages (default: {DEFAULT_MAX_PAGES})")

    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    setup_logging(args.output)

    scraper = FullPageScraper(
        base_url=args.url,
        output_dir=args.output,
        max_depth=args.depth,
        delay=args.delay,
        max_pages=args.max_pages,
    )
    scraper.run()


if __name__ == "__main__":
    main()
