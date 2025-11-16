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
    """
    Extracts items from RSS/Atom feeds and preserves the *precise* link per item.
    This fixes the broken-link issue in Market Sentiment.
    """
    soup = BeautifulSoup(text, "xml")
    items = soup.find_all("item")
    quotes = []

    fallback_platform = _infer_platform_from_url(feed_url)

    for item in items:
        title_tag = item.find("title")
        link_tag = item.find("link")
        guid_tag = item.find("guid")
        date_tag = item.find("pubDate")

        summary = title_tag.text.strip() if title_tag else ""
        link = link_tag.text.strip() if link_tag else ""
        guid = guid_tag.text.strip() if guid_tag else ""
        pub_date = date_tag.text.strip() if date_tag else None

        # Choose the most precise URL available
        item_url = link or guid or feed_url

        platform = _infer_platform_from_url(item_url) or fallback_platform

        if not summary:
            continue

        quotes.append({
            "summary": summary,
            "link": item_url,
            "platform": platform,
            "pub_date": pub_date
        })

    # Combined text used for hashing & diffing
    combined = "\n".join(f"[{q['platform']}] {q['summary']} ({q['link']})" for q in quotes)
    return combined, quotes

def _extract_html_text(text: str) -> str:
    soup = BeautifulSoup(text, "html.parser")
    for script in soup(["script", "style"]):
        script.decompose()
    return soup.get_text(separator="\n")

def _infer_source_type(url: str) -> str:
    social_domains = [
        "reddit.com", "stackoverflow.com", "linkedin.com",
        "twitter.com", "x.com", "hnrss.org", "discord.com"
    ]
    return "social" if any(domain in url for domain in social_domains) else "official"

def fetch_site_batch(yaml_path: str) -> List[Dict]:
    """
    Fetches all sites defined in sites.yaml and returns structured results:
    - text: extracted text (RSS items or full HTML text)
    - quotes: list of structured sentiment items (for RSS/social feeds)
    - source_type: social or official
    """
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

        # Detect RSS vs HTML and extract accordingly
        if _is_rss_like(text_raw):
            extracted, quotes = _extract_rss_with_quotes(text_raw, url)
        else:
            extracted = _extract_html_text(text_raw)
            quotes = []

        # Prefer YAML-specified type; if missing, infer from URL
        source_type = site.get("type") or _infer_source_type(url)

        results.append({
            "url": url,
            "text": extracted,
            "quotes": quotes,
            "fetched_at": int(time.time()),
            "hash": hashlib.md5(extracted.encode("utf-8")).hexdigest(),
            "source_type": source_type
        })

    return results
