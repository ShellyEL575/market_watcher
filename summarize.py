import os
import time
from typing import List, Dict
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
- Group feedback into clear themes (e.g., onboarding, pricing, performance).
- Quantify mentions (e.g., “12 posts about agent flakiness”).
- Include 3–5 linked quotes as evidence.

## 🧠 Executive Summary
- 3–5 top insights across all competitors or market signals.
- Focus on things that could move the market or messaging.
- Use strong verbs. Add source links inline.

## 🏢 By Competitor (GitLab, GitHub, Harness, Grafana, etc.)
- For each, list only content published in the past 7 days.
- Include actual post dates (e.g., “Nov 10: GitHub launched…”).
- Skip or flag stale content even if diffed again.
- Add links to source content.

## 🗞️ Analyst & Media
- Summarize 1–3 relevant industry or analyst pieces.
- Include sentiment if opinionated (e.g., “GitLab is outpacing others in AI”).
- Link to source.

## 📈 Hiring Signals (Job Postings)
- Summarize patterns in recent job postings by competitors.
- Highlight roles tied to product growth, GTM focus, or strategic bets (e.g., AI, DevEx, ecosystem).
- Mention volume shifts, new regions, or notable senior hires.
- Include links to 2–3 representative listings.

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
        source_type = c.get("source_type", "official")

        # Only include social quotes in sentiment section
        if source_type == "social" and quotes:
            for q in quotes:
                qtext = q.get("summary") or q.get("text") or "(no summary)"
                qlink = q.get("link") or url
                quotes_section.append(f'• "{qtext.strip()}" — [source]({qlink})')

        if added:
            lines = "\n".join(f"• {line}" for line in added[:10])
            others_section.append(f"### {url}\n\n{lines}")

    all_sections = []
    if quotes_section:
        all_sections.append("## 🔥 Community & Sentiment Quotes (Social Only)\n" + "\n".join(quotes_section))
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
