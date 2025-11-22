import os
import re
import yaml
import time
import hashlib
import requests
from typing import List, Dict, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urlparse

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# -----------------------------
# Fetching
# -----------------------------
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


# -----------------------------
# RSS detection & parsing
# -----------------------------
def _is_rss_like(text: str) -> bool:
    return "<rss" in text or "<feed" in text or "application/rss+xml" in text


def _infer_platform_from_url(url: str) -> str:
    url = url.lower()
    if "reddit" in url:
        return "Reddit"
    if "stackoverflow" in url:
        return "StackOverflow"
    if "linkedin" in url:
        return "LinkedIn"
    if "x.com" in url or "twitter.com" in url:
        return "X"
    if "hn" in url or "ycombinator.com" in url:
        return "HackerNews"
    if "discord" in url:
        return "Discord"
    return "Other"


def _extract_rss_with_quotes(text: str, feed_url: str) -> Tuple[str, List[Dict]]:
    soup = BeautifulSoup(text, "xml")
    items = soup.find_all("item")
    quotes = []

    fallback_platform = _infer_platform_from_url(feed_url)

    for item in items:
        title_tag = item.find("title")
        link_tag = item.find("link")
        
def fetch_site_batch(yaml_path: str) -> List[Dict]:

    if __name__ == "__main__":
        print("✅ fetch_site_batch is defined and ready.")
