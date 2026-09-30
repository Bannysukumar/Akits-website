"""
===============================================================================
 AKITS Content Extractor
 -------------------------------------------------------------------------------
 Parses all scraped HTML pages and extracts structured content into JSON:
 - Navigation menu structure (with dropdowns)
 - Footer content (address, phone, social links)
 - Per-page content: headings, paragraphs, images, tables, lists, videos
 - Site-wide metadata (titles, descriptions, breadcrumbs)

 Usage:
     python extract_content.py
     python extract_content.py --input akits_pages_source --output extracted_data
===============================================================================
"""

import os
import re
import sys
import json
import html
import argparse
from urllib.parse import urlparse, unquote
from collections import OrderedDict

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

try:
    from bs4 import BeautifulSoup, NavigableString
except ImportError:
    os.system(f"{sys.executable} -m pip install beautifulsoup4")
    from bs4 import BeautifulSoup, NavigableString

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False


def colorize(text, color):
    if not HAS_COLOR:
        return text
    colors = {"green": Fore.GREEN, "red": Fore.RED, "yellow": Fore.YELLOW,
              "cyan": Fore.CYAN, "magenta": Fore.MAGENTA, "blue": Fore.BLUE}
    return f"{colors.get(color, '')}{text}{Style.RESET_ALL}"


# ----------------------------- Configuration ---------------------------------

INPUT_DIR = "akits_pages_source"
OUTPUT_DIR = "extracted_data"
BASE_URL = "https://akits.ac.in"


# ----------------------------- Navigation Extractor --------------------------

def extract_navigation(soup):
    """Extract the full navigation menu structure from the page header.
    Handles multi-level dropdown menus from HFE (Header Footer Elementor)."""
    nav_data = []

    # Find the main nav menu (HFE navigation widget)
    nav = soup.find("nav", class_=re.compile(r"hfe-nav-menu"))
    if not nav:
        # Fallback: look for any nav with menu items
        nav = soup.find("nav")
    if not nav:
        return nav_data

    def parse_menu_items(ul_element):
        """Recursively parse menu items from a <ul> element."""
        items = []
        if not ul_element:
            return items

        for li in ul_element.find_all("li", recursive=False):
            item = {}

            # Get the link
            a_tag = li.find("a", recursive=False)
            if not a_tag:
                # Check inside hfe-has-submenu-container
                container = li.find("div", class_="hfe-has-submenu-container")
                if container:
                    a_tag = container.find("a")

            if a_tag:
                item["label"] = clean_text(a_tag.get_text())
                href = a_tag.get("href", "#")
                item["href"] = href
                # Convert to relative path for React routing
                if href.startswith(BASE_URL):
                    item["path"] = href.replace(BASE_URL, "").strip("/") or "/"
                elif href == "#":
                    item["path"] = "#"
                else:
                    item["path"] = href

            # Check for submenu
            sub_menu = li.find("ul", class_="sub-menu", recursive=False)
            if sub_menu:
                item["children"] = parse_menu_items(sub_menu)

            if item.get("label"):
                items.append(item)

        return items

    main_ul = nav.find("ul", class_=re.compile(r"hfe-nav-menu"))
    if not main_ul:
        main_ul = nav.find("ul")

    if main_ul:
        nav_data = parse_menu_items(main_ul)

    return nav_data


# ----------------------------- Footer Extractor ------------------------------

def extract_footer(soup):
    """Extract footer content: copyright, address, phone, social links."""
    footer_data = {
        "copyright": "",
        "address": "",
        "phone": [],
        "email": [],
        "social_links": [],
        "footer_text": [],
        "footer_links": [],
    }

    footer = soup.find("footer") or soup.find("div", attrs={"data-footer": True})
    if not footer:
        return footer_data

    # Copyright text
    copyright_el = footer.find(attrs={"data-id": "copyright"}) or footer.find(class_=re.compile(r"copyright"))
    if copyright_el:
        footer_data["copyright"] = clean_text(copyright_el.get_text())

    # Social links
    for a_tag in footer.find_all("a", href=True):
        href = a_tag["href"]
        text = clean_text(a_tag.get_text())
        social_platforms = ["facebook", "twitter", "instagram", "youtube", "linkedin", "whatsapp"]
        for platform in social_platforms:
            if platform in href.lower():
                footer_data["social_links"].append({
                    "platform": platform,
                    "url": href,
                })
                break

    # Phone numbers
    for a_tag in footer.find_all("a", href=re.compile(r"^tel:")):
        phone = a_tag["href"].replace("tel:", "").strip()
        if phone:
            footer_data["phone"].append(phone)

    # Email addresses
    for a_tag in footer.find_all("a", href=re.compile(r"^mailto:")):
        email = a_tag["href"].replace("mailto:", "").strip()
        if email:
            footer_data["email"].append(email)

    # Address - look for icon-list items or address-like text
    for item in footer.find_all(class_=re.compile(r"icon-list|address|location")):
        text = clean_text(item.get_text())
        if text and len(text) > 10:
            footer_data["address"] = text
            break

    # All text paragraphs in footer
    for widget in footer.find_all(class_="elementor-widget-container"):
        text = clean_text(widget.get_text())
        if text and len(text) > 5 and text not in footer_data["footer_text"]:
            footer_data["footer_text"].append(text)

    # Footer links
    for a_tag in footer.find_all("a", href=True):
        href = a_tag["href"]
        text = clean_text(a_tag.get_text())
        if text and href.startswith(BASE_URL):
            path = href.replace(BASE_URL, "").strip("/")
            footer_data["footer_links"].append({"label": text, "path": path or "/"})

    return footer_data


# ----------------------------- Page Content Extractor ------------------------

def clean_text(text):
    """Clean extracted text: strip whitespace, normalize spaces, decode HTML entities."""
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    # Remove zero-width and invisible chars
    text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)
    return text


def is_in_header_or_footer(element):
    """Check if an element is inside header, footer, or navigation (not main content)."""
    for parent in element.parents:
        if parent.name in ("html", "body", "[document]", "main"):
            # Stop checking once we reach body/main — these are not header/footer
            return False
        if parent.name in ("header", "footer", "nav"):
            return True
        classes = parent.get("class", [])
        # Check for exact class name matches (not substring)
        for cls in classes:
            if cls in ("hfe-nav-menu", "site-footer", "footer-width-fixer"):
                return True
    return False


def extract_page_content(soup, page_url):
    """Extract all meaningful content from a page's main content area."""
    content = {
        "url": page_url,
        "title": "",
        "meta_description": "",
        "breadcrumbs": [],
        "banner_image": "",
        "headings": [],
        "paragraphs": [],
        "sections": [],
        "images": [],
        "videos": [],
        "iframes": [],
        "tables": [],
        "lists": [],
        "documents": [],
    }

    # ---- Title ----
    title_tag = soup.find("title")
    if title_tag:
        content["title"] = clean_text(title_tag.get_text()).replace(" - AKITS", "").replace(" | AKITS", "").strip()

    # ---- Meta Description ----
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc:
        content["meta_description"] = clean_text(meta_desc.get("content", ""))

    # ---- Breadcrumbs from JSON-LD ----
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and "@graph" in data:
                for item in data["@graph"]:
                    if item.get("@type") == "BreadcrumbList":
                        for crumb in item.get("itemListElement", []):
                            content["breadcrumbs"].append({
                                "name": crumb.get("name", ""),
                                "url": crumb.get("item", ""),
                            })
        except (json.JSONDecodeError, TypeError):
            pass

    # ---- Find main content area ----
    main = soup.find("main", id="main") or soup.find("main") or soup.find("div", class_="site-main")
    if not main:
        main = soup.find("body")
    if not main:
        return content

    # ---- Banner/Slider Image ----
    slider = main.find(class_=re.compile(r"n2-ss-slide-background|smart-slider|banner"))
    if slider:
        img = slider.find("img")
        if img:
            content["banner_image"] = img.get("src", "")

    # ---- Extract ALL headings directly from main (skip header/footer/nav) ----
    seen_headings = set()
    for heading in main.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        if is_in_header_or_footer(heading):
            continue
        text = clean_text(heading.get_text())
        if text and len(text) > 1:
            key = f"{heading.name}:{text}"
            if key not in seen_headings:
                seen_headings.add(key)
                content["headings"].append({
                    "level": int(heading.name[1]),
                    "text": text,
                })

    # ---- Extract ALL paragraphs directly from main ----
    seen_paragraphs = set()
    for p in main.find_all("p"):
        if is_in_header_or_footer(p):
            continue
        text = clean_text(p.get_text())
        if text and len(text) > 5 and text not in seen_paragraphs:
            seen_paragraphs.add(text)
            content["paragraphs"].append(text)

    # ---- Also extract text from Elementor text-editor widgets ----
    for widget in main.find_all(class_=re.compile(r"elementor-widget-text-editor")):
        if is_in_header_or_footer(widget):
            continue
        container = widget.find(class_="elementor-widget-container")
        if container:
            for p in container.find_all("p"):
                text = clean_text(p.get_text())
                if text and len(text) > 5 and text not in seen_paragraphs:
                    seen_paragraphs.add(text)
                    content["paragraphs"].append(text)

    # ---- Extract content by section for structure ----
    sections = main.find_all("section", class_=re.compile(r"elementor-section|elementor-top-section"))
    if not sections:
        sections = [main]

    for section in sections:
        section_data = extract_section_content(section)
        if section_data and (section_data.get("headings") or section_data.get("paragraphs") or section_data.get("images")):
            content["sections"].append(section_data)

    # ---- All images in main content ----
    seen_srcs = set()
    for img in main.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
        if src and src not in seen_srcs:
            seen_srcs.add(src)
            width = img.get("width", "")
            height = img.get("height", "")
            if width and height:
                try:
                    if int(width) < 10 or int(height) < 10:
                        continue
                except (ValueError, TypeError):
                    pass

            content["images"].append({
                "src": src,
                "alt": clean_text(img.get("alt", "")),
                "width": width,
                "height": height,
                "class": " ".join(img.get("class", [])),
            })

    # ---- Videos ----
    for video in main.find_all("video"):
        src = video.get("src") or ""
        source = video.find("source")
        if source:
            src = source.get("src", src)
        poster = video.get("poster", "")
        if src:
            content["videos"].append({"src": src, "poster": poster})

    # ---- Iframes (YouTube, etc.) ----
    for iframe in main.find_all("iframe"):
        src = iframe.get("src") or iframe.get("data-src") or ""
        if src:
            content["iframes"].append({
                "src": src,
                "title": clean_text(iframe.get("title", "")),
            })

    # ---- Tables ----
    for table in main.find_all("table"):
        table_data = extract_table(table)
        if table_data:
            content["tables"].append(table_data)

    # ---- Document links (PDFs, etc.) ----
    doc_extensions = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}
    for a_tag in main.find_all("a", href=True):
        href = a_tag["href"]
        ext = os.path.splitext(urlparse(href).path.lower())[1]
        if ext in doc_extensions:
            content["documents"].append({
                "url": href,
                "text": clean_text(a_tag.get_text()) or os.path.basename(urlparse(href).path),
                "type": ext.lstrip(".").upper(),
            })

    # ---- Lists ----
    for ul in main.find_all(["ul", "ol"]):
        if ul.find_parent("nav") or "menu" in " ".join(ul.get("class", [])):
            continue
        if is_in_header_or_footer(ul):
            continue
        items = []
        for li in ul.find_all("li", recursive=False):
            text = clean_text(li.get_text())
            if text and len(text) > 2:
                items.append(text)
        if items and len(items) > 1:
            content["lists"].append({
                "type": "ordered" if ul.name == "ol" else "unordered",
                "items": items,
            })

    return content


def extract_section_content(section):
    """Extract content from a single Elementor section."""
    data = {
        "headings": [],
        "paragraphs": [],
        "images": [],
        "background_image": "",
    }

    # Background image from inline style or data attributes
    style = section.get("style", "")
    bg_match = re.search(r'url\(["\']?(.*?)["\']?\)', style)
    if bg_match:
        data["background_image"] = bg_match.group(1)

    # Find all widget containers (where actual content lives)
    widgets = section.find_all(class_="elementor-widget-container")
    if not widgets:
        widgets = [section]

    for widget in widgets:
        # Skip navigation widgets
        parent = widget.find_parent(class_=re.compile(r"navigation-menu|hfe-nav-menu|footer"))
        if parent:
            continue

        # Headings
        for heading in widget.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            text = clean_text(heading.get_text())
            if text and len(text) > 1:
                data["headings"].append({
                    "level": int(heading.name[1]),
                    "text": text,
                })

        # Paragraphs
        for p in widget.find_all("p"):
            text = clean_text(p.get_text())
            if text and len(text) > 3:
                # Check if paragraph contains an image
                img = p.find("img")
                if img and not text.replace(clean_text(img.get("alt", "")), "").strip():
                    continue  # Skip paragraphs that are just image alt text
                data["paragraphs"].append(text)

        # Images within widgets
        for img in widget.find_all("img"):
            src = img.get("src") or img.get("data-src")
            if src:
                data["images"].append({
                    "src": src,
                    "alt": clean_text(img.get("alt", "")),
                })

    # Deduplicate
    seen_headings = set()
    unique_headings = []
    for h in data["headings"]:
        key = f"{h['level']}:{h['text']}"
        if key not in seen_headings:
            seen_headings.add(key)
            unique_headings.append(h)
    data["headings"] = unique_headings

    seen_paragraphs = set()
    unique_paragraphs = []
    for p in data["paragraphs"]:
        if p not in seen_paragraphs:
            seen_paragraphs.add(p)
            unique_paragraphs.append(p)
    data["paragraphs"] = unique_paragraphs

    seen_images = set()
    unique_images = []
    for img in data["images"]:
        if img["src"] not in seen_images:
            seen_images.add(img["src"])
            unique_images.append(img)
    data["images"] = unique_images

    return data


def extract_table(table):
    """Extract a table into structured data."""
    headers = []
    rows = []

    # Extract headers
    thead = table.find("thead")
    if thead:
        for th in thead.find_all(["th", "td"]):
            headers.append(clean_text(th.get_text()))
    else:
        # First row might be headers
        first_row = table.find("tr")
        if first_row:
            ths = first_row.find_all("th")
            if ths:
                headers = [clean_text(th.get_text()) for th in ths]

    # Extract rows
    tbody = table.find("tbody") or table
    for tr in tbody.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if cells:
            row = [clean_text(cell.get_text()) for cell in cells]
            # Skip if this row is actually the header row
            if row == headers:
                continue
            if any(cell.strip() for cell in row):
                rows.append(row)

    if not rows and not headers:
        return None

    return {"headers": headers, "rows": rows}


# ----------------------------- Main Processor --------------------------------

def find_html_files(input_dir):
    """Recursively find all HTML files in the input directory."""
    html_files = []
    for root, dirs, files in os.walk(input_dir):
        for f in files:
            if f.endswith(".html") and not f.startswith("_"):
                html_files.append(os.path.join(root, f))
    return sorted(html_files)


def get_source_url(html_content):
    """Extract the source URL from the comment header we added during scraping."""
    match = re.search(r'SOURCE URL:\s*(https?://\S+)', html_content)
    return match.group(1) if match else ""


def process_all_pages(input_dir, output_dir):
    """Process all scraped HTML pages and extract structured content."""
    os.makedirs(output_dir, exist_ok=True)

    html_files = find_html_files(input_dir)
    if not html_files:
        print(f"No HTML files found in {input_dir}")
        return

    print(f"\n{'=' * 70}")
    print(f"  {colorize('AKITS CONTENT EXTRACTOR', 'cyan')}")
    print(f"  Input:  {colorize(os.path.abspath(input_dir), 'yellow')}")
    print(f"  Output: {colorize(os.path.abspath(output_dir), 'green')}")
    print(f"  Pages:  {colorize(str(len(html_files)), 'magenta')}")
    print(f"{'=' * 70}\n")

    # Global data (extracted once)
    navigation = None
    footer = None
    all_pages = []

    for i, filepath in enumerate(html_files, 1):
        rel_path = os.path.relpath(filepath, input_dir)
        print(f"  [{i:3d}/{len(html_files)}] {colorize(rel_path, 'cyan')} ... ", end="", flush=True)

        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                html_content = f.read()

            source_url = get_source_url(html_content)
            soup = BeautifulSoup(html_content, "html.parser")

            # Extract navigation (once, from the first page)
            if navigation is None:
                navigation = extract_navigation(soup)
                if navigation:
                    print(f"{colorize('(+nav)', 'green')} ", end="")

            # Extract footer (once, from the first page)
            if footer is None:
                footer = extract_footer(soup)
                if footer.get("copyright") or footer.get("social_links"):
                    print(f"{colorize('(+footer)', 'green')} ", end="")

            # Extract page content
            page_content = extract_page_content(soup, source_url)
            page_content["local_file"] = rel_path

            # Generate a slug/route for React
            if source_url:
                path = source_url.replace(BASE_URL, "").strip("/")
                page_content["route"] = f"/{path}" if path else "/"
            else:
                # Derive from file path
                route = rel_path.replace("\\", "/").replace("/index.html", "")
                page_content["route"] = f"/{route}" if route != "index.html" else "/"

            all_pages.append(page_content)

            # Stats
            n_headings = len(page_content.get("headings", []))
            n_paragraphs = len(page_content.get("paragraphs", []))
            n_images = len(page_content["images"])
            print(
                f"{colorize('[OK]', 'green')} "
                f"({n_headings}h, {n_paragraphs}p, {n_images}img)"
            )

        except Exception as e:
            print(f"{colorize('[ERROR]', 'red')} {e}")

    # ---- Save all extracted data ----
    print(f"\n{'-' * 60}")
    print(f"  Saving extracted data...")

    # 1. Navigation
    nav_path = os.path.join(output_dir, "navigation.json")
    with open(nav_path, "w", encoding="utf-8") as f:
        json.dump(navigation or [], f, indent=2, ensure_ascii=False)
    print(f"  {colorize('[SAVED]', 'green')} navigation.json ({len(navigation or [])} top-level items)")

    # 2. Footer
    footer_path = os.path.join(output_dir, "footer.json")
    with open(footer_path, "w", encoding="utf-8") as f:
        json.dump(footer or {}, f, indent=2, ensure_ascii=False)
    print(f"  {colorize('[SAVED]', 'green')} footer.json")

    # 3. All pages content
    pages_path = os.path.join(output_dir, "pages.json")
    with open(pages_path, "w", encoding="utf-8") as f:
        json.dump(all_pages, f, indent=2, ensure_ascii=False)
    print(f"  {colorize('[SAVED]', 'green')} pages.json ({len(all_pages)} pages)")

    # 4. Routes index (for React Router)
    routes = []
    for page in all_pages:
        routes.append({
            "route": page["route"],
            "title": page["title"],
            "description": page.get("meta_description", ""),
            "has_images": len(page["images"]) > 0,
            "has_tables": len(page.get("tables", [])) > 0,
            "has_videos": len(page.get("videos", [])) > 0,
            "has_documents": len(page.get("documents", [])) > 0,
        })
    routes_path = os.path.join(output_dir, "routes.json")
    with open(routes_path, "w", encoding="utf-8") as f:
        json.dump(routes, f, indent=2, ensure_ascii=False)
    print(f"  {colorize('[SAVED]', 'green')} routes.json ({len(routes)} routes)")

    # 5. Images index (all unique images across all pages)
    all_images = {}
    for page in all_pages:
        for img in page["images"]:
            src = img["src"]
            if src not in all_images:
                all_images[src] = {
                    "src": src,
                    "alt": img.get("alt", ""),
                    "used_on": [],
                }
            all_images[src]["used_on"].append(page["route"])

    images_path = os.path.join(output_dir, "images_index.json")
    with open(images_path, "w", encoding="utf-8") as f:
        json.dump(list(all_images.values()), f, indent=2, ensure_ascii=False)
    print(f"  {colorize('[SAVED]', 'green')} images_index.json ({len(all_images)} unique images)")

    # 6. Per-page JSON files (for individual page data)
    pages_dir = os.path.join(output_dir, "pages")
    os.makedirs(pages_dir, exist_ok=True)
    for page in all_pages:
        slug = page["route"].strip("/").replace("/", "_") or "home"
        page_path = os.path.join(pages_dir, f"{slug}.json")
        with open(page_path, "w", encoding="utf-8") as f:
            json.dump(page, f, indent=2, ensure_ascii=False)
    print(f"  {colorize('[SAVED]', 'green')} pages/ directory ({len(all_pages)} individual page JSONs)")

    # ---- Final stats ----
    total_headings = sum(len(p.get("headings", [])) for p in all_pages)
    total_paragraphs = sum(len(p.get("paragraphs", [])) for p in all_pages)
    total_images = len(all_images)
    total_tables = sum(len(p.get("tables", [])) for p in all_pages)
    total_documents = sum(len(p.get("documents", [])) for p in all_pages)

    print(f"\n{'=' * 70}")
    print(f"  {colorize('EXTRACTION COMPLETE', 'cyan')}")
    print(f"{'-' * 70}")
    print(f"  Pages processed    : {colorize(str(len(all_pages)), 'green')}")
    print(f"  Nav menu items     : {colorize(str(len(navigation or [])), 'yellow')}")
    print(f"  Total headings     : {colorize(str(total_headings), 'yellow')}")
    print(f"  Total paragraphs   : {colorize(str(total_paragraphs), 'yellow')}")
    print(f"  Unique images      : {colorize(str(total_images), 'yellow')}")
    print(f"  Tables             : {colorize(str(total_tables), 'yellow')}")
    print(f"  Documents (PDFs)   : {colorize(str(total_documents), 'yellow')}")
    print(f"{'-' * 70}")
    print(f"  Output directory   : {colorize(os.path.abspath(output_dir), 'green')}")
    print(f"{'=' * 70}\n")

    print("  Output files:")
    print(f"    navigation.json    - Full nav menu structure for React")
    print(f"    footer.json        - Footer content, social links, contact")
    print(f"    pages.json         - All pages content in one file")
    print(f"    routes.json        - React Router routes index")
    print(f"    images_index.json  - All unique images with usage mapping")
    print(f"    pages/             - Individual page JSON files")
    print()


# ----------------------------- Main ------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Extract structured content from scraped AKITS HTML pages")
    parser.add_argument("--input", "-i", default=INPUT_DIR, help=f"Input directory (default: {INPUT_DIR})")
    parser.add_argument("--output", "-o", default=OUTPUT_DIR, help=f"Output directory (default: {OUTPUT_DIR})")
    args = parser.parse_args()

    process_all_pages(args.input, args.output)


if __name__ == "__main__":
    main()
