# novel543 EPUB Scraper

Fetches all chapters from a novel on [novel543.com](https://www.novel543.com) and packages them into a clean EPUB file.

---

## Requirements

- Python 3.8+
- The following packages:

```bash
pip install requests beautifulsoup4 ebooklib
```

## Quick Start

### Step 1 - Get the chapter links from the browser

1. Open the novel's directory page in your browser, e.g.:
   ```
   https://www.novel543.com/0321692786/dir
   ```

2. Press **F12** to open DevTools and go to the Console tab.

3. Paste and run this snippet:
   ```js
   const links = [...document.querySelectorAll('a[href*="/0321692786/"]')]
     .filter(a => !a.href.endsWith('/dir'))
     .map(a => `${a.textContent.trim()} | ${a.href}`)
     .join('\n');
   console.log(links);
   copy(links);
   ```

4. Your clipboard now contains all chapter links in this format:
   ```
   第1章 第一個瘋子 | https://www.novel543.com/0321692786/8096_1.html
   第2章 認屍 | https://www.novel543.com/0321692786/8096_2.html
   ...
   ```

> **Note:** Replace `0321692786` in the selector with the novel's ID if you are scraping a different novel.

---

### Step 2 - Paste the links into the script

Open `Novel543-Scraper.py` in any text editor and find the `RAW_CHAPTERS` variable near the top of the file:

```python
RAW_CHAPTERS = """第1章 第一個瘋子 | https://...
...
"""
```

Delete everything between the triple quotes and paste your clipboard contents in its place. The script will automatically:
- Remove duplicate entries
- Sort all chapters by number regardless of paste order

---

### Step 3 - Run the script

Open PowerShell, navigate to the folder containing the script, and run:

```powershell
cd Desktop
python '.\Novel543-Scraper.py'
```

The finished EPUB is saved in the same folder as the script.

---

## Configuration

All settings are at the top of the script:

| Variable | Default | Description |
|---|---|---|
| `DELAY` | `0.5` | Seconds to wait between chapter fetches. Increase if you get rate-limited. |
| `OUTPUT` | `novel_1004612957.epub` | Output file path. Change to save elsewhere. |
| `BOOK_ID` | `0321692786` | The novel's ID from the URL. |
