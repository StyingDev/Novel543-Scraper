#!/usr/bin/env python3
"""
Fetches chapters from novel543.com and builds an EPUB file.
Usage: python3 fetch_epub.py
"""

import re
import time
import sys
import os
from ebooklib import epub
import requests
from bs4 import BeautifulSoup

# ── Configuration ────────────────────────────────────────────────────────────

BOOK_ID    = "1004612957"
FILE_ID    = "8096"
BASE_URL   = f"https://www.novel543.com/{BOOK_ID}"
DIR_URL    = f"{BASE_URL}/dir"
OUTPUT     = "novel_1004612957.epub"  # saves next to the script

# Polite crawl delay (seconds between requests)
DELAY = 0.1

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Referer": BASE_URL,
}

# ── Chapter list (Paste the List Here) ─────────────

RAW_CHAPTERS = """

"""

# ── Parse and deduplicate chapter list ───────────────────────────────────────

def parse_chapters(raw: str) -> list[dict]:
    """Parse the raw chapter list, deduplicate by URL, sort by chapter number."""
    seen_urls = {}
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line or " | " not in line:
            continue
        title, url = line.split(" | ", 1)
        title = title.strip()
        url = url.strip()
        # Extract chapter number from URL (8096_NNN.html)
        m = re.search(r'_(\d+)\.html$', url)
        num = int(m.group(1)) if m else 0
        if url not in seen_urls:
            seen_urls[url] = {"title": title, "url": url, "num": num}
    chapters = sorted(seen_urls.values(), key=lambda c: c["num"])
    return chapters


# ── Fetch a single chapter ────────────────────────────────────────────────────

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

def fetch_chapter_html(url: str, retries: int = 3) -> str | None:
    """Fetch a chapter page and return its main content as clean HTML, or None on failure."""
    for attempt in range(retries):
        try:
            r = SESSION.get(url, timeout=20)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")

            # novel543 structure:
            #   <div class="chapter-content px-3">
            #     <h1>…</h1>
            #     <div class="content py-5">
            #       <div class="gadBlock">…ads…</div>
            #       <p>…text…</p>  ← we want these
            #       <div class="adBlock">…</div>
            #       <div><p><span>溫馨提示…</span></p></div>  ← footer note
            #     </div>
            #   </div>

            # 1. Find the inner content div
            # novel543 uses <div class="content py-5"> — match by exact class membership
            def has_content_class(tag):
                return (
                    tag.name == "div"
                    and "content" in tag.get("class", [])
                    and "chapter-content" not in tag.get("class", [])
                )
            content = (
                soup.find(has_content_class)
                or soup.find("div", id="content")
                or soup.find("article")
            )
            if not content:
                body = soup.find("body")
                content = body if body else soup

            # 2. Strip all ad/script/style/nav noise
            for tag in content.find_all(
                ["script", "style", "ins", "nav", "header", "footer",
                 "noscript", "iframe", "button"]
            ):
                tag.decompose()

            # Strip ad block divs by class name
            for tag in content.find_all("div", class_=re.compile(r"gad|adBlock|ad-", re.I)):
                tag.decompose()

            # Strip the "溫馨提示" footer note div (contains a <span> with that text)
            for tag in content.find_all("div"):
                if "溫馨提示" in tag.get_text():
                    tag.decompose()

            # 3. Collect only <p> tags that have meaningful text
            paragraphs = content.find_all("p")
            clean_paras = []
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and "溫馨提示" not in text:
                    clean_paras.append(f"<p>{text}</p>")

            if clean_paras:
                return "\n".join(clean_paras)
            return "<p>[Could not extract content]</p>"

        except Exception as e:
            print(f"  ⚠  Attempt {attempt+1} failed for {url}: {e}")
            if attempt < retries - 1:
                time.sleep(3)
    return None


# ── Build EPUB ────────────────────────────────────────────────────────────────

def build_epub(chapters: list[dict]) -> None:
    book = epub.EpubBook()
    book.set_identifier(f"novel_{BOOK_ID}")
    book.set_title("小說 1004612957")
    book.set_language("zh-TW")

    # Basic CSS
    css = epub.EpubItem(
        uid="style_default",
        file_name="style/default.css",
        media_type="text/css",
        content="""
body { font-family: "Noto Serif CJK TC", "Source Han Serif TC", serif; line-height: 1.8; margin: 1em; }
h1 { font-size: 1.4em; margin-bottom: 1em; border-bottom: 1px solid #ccc; padding-bottom: .3em; }
p { text-indent: 2em; margin: .4em 0; }
""",
    )
    book.add_item(css)

    spine = ["nav"]
    toc = []
    total = len(chapters)

    for idx, ch in enumerate(chapters, 1):
        print(f"[{idx:4}/{total}] Fetching {ch['title']} …", end=" ", flush=True)
        html_body = fetch_chapter_html(ch["url"])
        if html_body is None:
            html_body = "<p>[Failed to fetch this chapter]</p>"
            print("FAILED")
        else:
            print("OK")

        # Wrap in a proper XHTML document
        chapter_content = f"""<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="zh-TW">
<head>
  <meta charset="utf-8"/>
  <title>{ch['title']}</title>
  <link rel="stylesheet" type="text/css" href="../style/default.css"/>
</head>
<body>
  <h1>{ch['title']}</h1>
  {html_body}
</body>
</html>"""

        if not html_body or not html_body.strip():
            html_body = "<p>[Content unavailable]</p>"

        # Store content as encoded bytes on the item to bypass ebooklib's
        # internal lxml HTML parser (which breaks on Python 3.14 / ebooklib 0.20)
        epub_ch = epub.EpubHtml(
            title=ch["title"],
            file_name=f"chap_{ch['num']:04d}.xhtml",
            lang="zh-TW",
        )
        epub_ch.content = chapter_content.encode("utf-8")
        epub_ch.add_item(css)
        book.add_item(epub_ch)
        spine.append(epub_ch)
        toc.append(epub.Link(f"chap_{ch['num']:04d}.xhtml", ch["title"], f"chap_{ch['num']:04d}"))

        time.sleep(DELAY)

    book.toc = toc
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = spine

    out_dir = os.path.dirname(os.path.abspath(OUTPUT))
    os.makedirs(out_dir, exist_ok=True)

    # Use options to skip the page-list feature that triggers the lxml crash
    epub.write_epub(OUTPUT, book, {"epub3_pages": False})
    print(f"\n EPUB saved to: {OUTPUT}")
    print(f"   Chapters included: {total}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    chapters = parse_chapters(RAW_CHAPTERS)
    print(f"Found {len(chapters)} unique chapters (sorted by number).")
    print(f"Output: {OUTPUT}\n")
    build_epub(chapters)