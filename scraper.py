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

def _extract_html_text(text: str) -> str:
    soup = BeautifulSoup(text, "html.parser")

    # Try focusing on <main> content
    main = soup.find("main")
    target = main if main else soup.body

    if not target:
        return ""

    for script in target(["script", "style"]):
        script.decompose()

    # Keep relevant text only
    lines = [line.strip() for line in target.get_text(separator="\n").splitlines()]
    lines = [line for line in lines if line and not re.match(r"^\s*$", line)]
    return "\n".join(lines)

def _normalize_text_for_hash(text: str) -> str:
    lines = [line.strip().lower() for line in text.splitlines()]
    lines = list(dict.fromkeys(lines))  # deduplicate while preserving order
    return "\n".join(lines)

def _safe_filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.replace(".", "_")
    path = parsed.path.strip("/").replace("/", "_")
    return f"{host}_{path or 'root'}"

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
            extracted, quotes = _extract_rss_with_quotes(text_raw, url)
        else:
            extracted = _extract_html_text(text_raw)
            quotes = []

        normed = _normalize_text_for_hash(extracted)
        site_id = _safe_filename_from_url(url)
        tmp_path = f"/tmp/{site_id}.txt"

        with open(tmp_path, "w") as f:
            f.write(normed)
        print(f"📝 Saved normalized text to {tmp_path}")

        source_type = site.get("type") or _infer_source_type(url)

        results.append({
            "url": url,
            "text": normed,
            "quotes": quotes,
            "fetched_at": int(time.time()),
            "hash": hashlib.md5(normed.encode("utf-8")).hexdigest(),
            "source_type": source_type
        })

    return results
