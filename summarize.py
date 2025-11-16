import os
import time
from typing import List, Dict
from openai import OpenAI, APIConnectionError

SYSTEM = """You are a VP of Product Marketing (PMM) reviewing competitive and market intelligence.
Your goal is to brief the executive team and guide the PMM org.
You write in a clear, concise, executive style."""

USER_TMPL = """You receive diffs of market/competitor content (blogs, releases, forums, analyst notes).
Please produce a structured weekly report with these sections:

# Community & Sentiment
- Summarize Reddit, HN, and forums.
- Include direct quotes with links and any standout opinions.
- Highlight recurring themes, concerns, or praises.

# Executive Summary
- High-level highlights across all competitors and market chatter.
- Major risks or opportunities.

# By Competitor
For each named competitor (Harness, GitLab, GitHub, DX, LinearB, Grafana):
- Key updates from official sources (blogs, changelogs, docs).
- Implications for CloudBees.
- Risks / Opportunities.

# By Site Type
- **Analyst / Media**: Summarize analyst blogs (Gartner, Forrester, TheNewStack, InfoQ).
- Link to original content where possible.

# Recommendations (PMM Team)
- 3–5 actionable moves for the PMM org (messaging, enablement, content).
- Note dependencies (e.g., need support from Eng, Sales, Exec).
- Be crisp and prescriptive.

---
Here are the raw diffs to analyze:

{diffs}
"""

def _build_diffs_text(changes: List[Dict]) -> str:
    quotes_section = []
    others_section = []

    for c in changes:
        url = c.get("url", "")
        quotes = c.get("quotes") or []
        added = c.get("added") or []

        if quotes:
            for q in quotes:
                qtext = q.get("summary") or q.get("text") or "(no summary)"
                qlink = q.get("link") or url
                quotes_section.append(f'• "{qtext.strip()}" — [source]({qlink})')

        if added:
            lines = "\n".join(f"• {line}" for line in added[:10])
            others_section.append(f"### {url}\n\n{lines}")

    all_sections = []
    if quotes_section:
        all_sections.append("## 🔥 Community & Sentiment Quotes\n" + "\n".join(quotes_section))
    if others_section:
        all_sections.append("\n\n## 📚 Other Updates\n" + "\n\n".join(others_section))

    return "\n\n".join(all_sections) if all_sections else "(no diffs)"

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
