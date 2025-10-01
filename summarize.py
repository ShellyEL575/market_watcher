import os
from typing import List, Dict
from openai import OpenAI

SYSTEM = """You are a VP of Product Marketing (PMM) reviewing competitive and market intelligence.
Your goal is to brief the executive team and guide the PMM org.
You write in a clear, concise, executive style."""

USER_TMPL = """You receive diffs of market/competitor content (blogs, releases, forums, analyst notes).
Please produce a structured weekly report with these sections:

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
- **Community / Forums**: Summarize Reddit, HN, other forums.
- Highlight sentiment, recurring themes, adoption pain points.

# Recommendations (PMM Team)
- 3–5 actionable moves for the PMM org (messaging, enablement, content).
- Note dependencies (e.g., need support from Eng, Sales, Exec).
- Be crisp and prescriptive.

---
Here are the raw diffs to analyze:

{diffs}
"""

def _build_diffs_text(changes: List[Dict]) -> str:
    sections = []
    for c in changes:
        added = c.get("added") or []
        quotes = c.get("quotes") or []

        bullets = "\n".join(f"• {ln}" for ln in added[:60]) if added else "(no visible changes)"
        quote_lines = "\n".join(f'• “{q["summary"]}” — [source]({q["link"]})' for q in quotes) if quotes else ""

        quote_section = f"\n\n🔗 Quotes:\n{quote_lines}" if quote_lines else ""
        section = f"### {c['url']}\n\n{bullets}{quote_section}"
        sections.append(section)

    return "\n\n".join(sections) if sections else "(no diffs)"

def write_summary(changes: List[Dict]) -> str:
    if not changes or all(not (c.get("added") or c.get("removed")) for c in changes):
        return "No changes detected this period."

    diffs_text = _build_diffs_text(changes)
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": USER_TMPL.format(diffs=diffs_text)},
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()
