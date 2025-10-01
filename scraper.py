import os
import re
import yaml
import time
import hashlib
import requests
from typing import List, Dict, Tuple
from bs4 import BeautifulSoup

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def _fetch(url: str, headers=None, timeout=15, retries=2) -> str:
    headers = headers or DEFAULT_HEADERS
    last_err = None
    for _ in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                return resp.text
            else:
                last_err = f"HTTP {resp.status_code}"
        except Exception as e:
            last_err = str(e)
        time.sleep(0.5)
    raise RuntimeError(f"Failed to fetch {url}: {last_err}")

def _is_rss_like(text: str) -> bool:
    return "<rss" in text or "<feed" in text or "application/rss+xml" in text

def _extract_rss_with_quotes(text: str) -> Tuple[str, List[Dict]]:
    soup = BeautifulSoup(text, "xml")
    items = soup.find_all("item")
    quotes = []

    for item in items:
        title = item.find("title").text.strip() if item.find("title") else ""
        link = item.find("link").text.strip() if item.find("link") else ""
        if title:
            quotes.append({"summary": title, "link": link})

    combined = "\n".join(q["summary"] for q in quotes)
    return combined, quotes

def _extract_html_text(text: str) -> str:
    soup = BeautifulSoup(text, "html.parser")
    for script in soup(["script", "style"]):
        script.decompose()
    return soup.get_text(separator="\n")

def fetch_site_batch(yaml_path: str) -> List[Dict]:
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)

    sites = data["sites"]

    results = []

    for site in sites:
        url = site["url"]
        print(f"🌐 Fetching: {url}")

        try:
            text_raw = _fetch(url)
        except Exception as e:
            print(f"⚠️  Skipping {url}: {e}")
            continue

        if _is_rss_like(text_raw):
            extracted, quotes = _extract_rss_with_quotes(text_raw)
        else:
            extracted = _extract_html_text(text_raw)
            quotes = []

        results.append({
            "url": url,
            "text": extracted,
            "quotes": quotes,
            "fetched_at": int(time.time()),
            "hash": hashlib.md5(extracted.encode("utf-8")).hexdigest()
        })

    return results
