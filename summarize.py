import os
import time
from typing import List, Dict
from collections import defaultdict, Counter
from openai import OpenAI, APIConnectionError

SYSTEM = """You are a VP of Product Marketing (PMM) reviewing competitive and market intelligence.
Your goal is to brief the executive team and guide the PMM org.
You write in a clear, concise, executive style."""

USER_TMPL = """You are a VP of Product Marketing (PMM) at CloudBees.

Each week, you receive market and competitive updates (blogs, changelogs, forums, job postings, analyst blogs, etc.).

Your job is to produce a clean, executive-style briefing for the PMM team and leadership.

It should prioritize insight, clarity, and actionable value, and feel polished enough to send as-is via email.

# Format the briefing with these structured sections:

## 🔥 Market Sentiment (Social only: Reddit, X, LinkedIn, StackOverflow)
- Group key quotes and themes from real users.
- Highlight adoption blockers, shifts in sentiment, new tool buzz.
- For each theme:
  - List number of mentions by platform (e.g., Reddit: 8, X: 5)
  - Include 2–3 direct quotes with real working links.

## 🧠 Executive Summary
- Top 3–5 insights across all competitors or market signals.
- Focus on new updates, notable reactions, or market shifts.

## 🏢 By Competitor (GitLab, GitHub, Harness, Grafana, etc.)
- Only include updates published this past week.
- Include release links and brief notes on significance.

## 🤖 AI in DevOps
- Highlight AI-driven feature releases, discussions, or usage shifts.
- Focus on LangChain, OpenAI, Nvidia, ML/AI-related DevOps chatter.

## 🗞️ Analyst & Media
- Include industry commentary or analyst takes.
- Link to original post. Summarize sentiment.

## 📈 Hiring Signals
- Summarize any hiring trends visible from job feeds or postings.
- Link to 2–3 relevant examples.

---
Here are the raw updates to analyze:

{diffs}
"""

def _build_diffs_text(changes: List[Dict]) -> str:
    sections = {
        "sentiment": [],
        "competitor": [],
        "ai": [],
        "analyst": [],
        "jobs": [],
        "other": []
    }

    sentiment_quotes = defaultdict(list)
    platform_counter = defaultdict(Counter)

    for c in changes:
        url = c.get("url", "")
        quotes = c.get("quotes") or []
        added = c.get("added") or []
        stype = c.get("source_type", "other")
        domain = url.lower()

        if stype == "social":
            for q in quotes:
                qtext = q.get("summary") or q.get("text")
                qlink = q.get("link") or url
                platform = q.get("platform") or infer_platform_from_url(qlink)
                theme = "general"
                sentiment_quotes[theme].append((qtext.strip(), qlink, platform))
                platform_counter[theme][platform] += 1
        elif any(x in domain for x in ["gitlab", "github", "harness", "grafana", "linearb"]):
            lines = "\n".join(f"• {ln}" for ln in added[:10])
            sections["competitor"].append(f"### {url}\n\n{lines}")
        elif any(x in domain for x in ["openai", "langchain", "nvidia", "ml", "ai"]):
            lines = "\n".join(f"• {ln}" for ln in added[:10])
            sections["ai"].append(f"### {url}\n\n{lines}")
        elif stype == "analyst":
            lines = "\n".join(f"• {ln}" for ln in added[:10])
            sections["analyst"].append(f"### {url}\n\n{lines}")
        elif "jobs" in stype or "job" in domain:
            lines = "\n".join(f"• {ln}" for ln in added[:10])
            sections["jobs"].append(f"### {url}\n\n{lines}")
        else:
            lines = "\n".join(f"• {ln}" for ln in added[:10])
            sections["other"].append(f"### {url}\n\n{lines}")

    if sentiment_quotes:
        sentiment_block = ["## 🔥 Market Sentiment"]
        for theme, quotes in sentiment_quotes.items():
            plat_counts = ", ".join(f"{k}: {v}" for k, v in platform_counter[theme].items())
            quote_lines = [f'  - "{qt}" [source]({ql})' for qt, ql, _ in quotes[:3]]
            sentiment_block.append(f"### Theme: {theme}\n- Posts: {len(quotes)} ({plat_counts})\n- Quotes:\n" + "\n".join(quote_lines))
        sections["sentiment"] = ["\n\n".join(sentiment_block)]

    output = []
    for key in ["sentiment", "competitor", "ai", "analyst", "jobs", "other"]:
        if sections[key]:
            title = {
                "sentiment": "## 🔥 Market Sentiment",
                "competitor": "## 🏢 By Competitor",
                "ai": "## 🤖 AI in DevOps",
                "analyst": "## 🗞️ Analyst & Media",
                "jobs": "## 📈 Hiring Signals",
                "other": "## 📚 Other Updates"
            }[key]
            output.append(title + "\n" + "\n\n".join(sections[key]))

    return "\n\n".join(output)

def infer_platform_from_url(url: str) -> str:
    url = url.lower()
    if "reddit" in url:
        return "Reddit"
    elif "stackoverflow" in url:
        return "StackOverflow"
    elif "linkedin" in url:
        return "LinkedIn"
    elif "x.com" in url or "twitter.com" in url:
        return "X"
    elif "hn" in url or "news.ycombinator.com" in url:
        return "HackerNews"
    return "Other"

def write_summary(changes: List[Dict], retries=3, delay=5) -> str:
    if not changes or all(not (c.get("added") or c.get("removed")) for c in changes):
        return "No changes detected this period."

    diffs_text = _build_diffs_text(changes)
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    for attempt in range(1, retries + 1):
        try:
            print(f"🧠 Generating summary (attempt {attempt}/{retries})...")
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": USER_TMPL.format(diffs=diffs_text)},
                ],
                temperature=0.2,
            )
            return resp.choices[0].message.content.strip()

        except APIConnectionError as e:
            print(f"⚠️ OpenAI connection failed (attempt {attempt}/{retries}): {e}")
            if attempt < retries:
                time.sleep(delay * attempt)
            else:
                raise
