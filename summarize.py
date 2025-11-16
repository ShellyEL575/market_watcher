import os
import time
from collections import defaultdict, Counter
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
- Group key quotes and themes from real users.
- Highlight adoption blockers, shifts in sentiment, new tool buzz.
- Include direct quotes with links, grouped by theme if possible.

## 🧠 Executive Summary
- Top 3–5 insights across all competitors or market signals.
- Focus on new updates, notable reactions, or market shifts.

## 🏢 By Competitor (GitLab, GitHub, Harness, Grafana, etc.)
- Only include updates published this past week.
- Include release links and brief notes on significance.

## 🤖 AI in DevOps
- Highlight AI-driven feature releases, discussions, or usage shifts.
- Focus on LangChain, OpenAI, Nvidia, ML/AI-related DevOps chatter.

## 📜 Analyst & Media
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
        "sentiment": defaultdict(list),
        "platform_counts": Counter(),
        "competitor": [],
        "ai": [],
        "analyst": [],
        "jobs": [],
        "other": []
    }

    for c in changes:
        url = c.get("url", "")
        quotes = c.get("quotes") or []
        added = c.get("added") or []
        stype = c.get("source_type", "other")
        domain = url.lower()

        if stype == "social":
            for q in quotes:
                qtext = q.get("summary") or q.get("text") or "(no summary)"
                qlink = q.get("link") or url
                platform = q.get("platform") or "unknown"
                theme = "general"
                # Optional: use NLP to auto-categorize
                if any(kw in qtext.lower() for kw in ["ai", "ml", "artificial"]):
                    theme = "AI Integration in DevOps"
                elif any(kw in qtext.lower() for kw in ["learning curve", "adoption", "onboarding"]):
                    theme = "Adoption Barriers"
                elif any(kw in qtext.lower() for kw in ["tool", "platform", "feature"]):
                    theme = "Emerging Tools"
                sections["sentiment"][theme].append((qtext.strip(), qlink, platform))
                sections["platform_counts"].update([platform])

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

    output = []

    if sections["sentiment"]:
        sentiment_lines = ["## 🔥 Market Sentiment (Social only: Reddit, X, LinkedIn, StackOverflow)", "\n### Key Themes:"]
        for theme, quotes in sections["sentiment"].items():
            platform_counts = Counter([p for _, _, p in quotes])
            total = sum(platform_counts.values())
            platforms_str = ", ".join([f"{k.title()}: {v}" for k, v in platform_counts.items()])
            sentiment_lines.append(f"\n**{theme}**\n- **Mentions**: {total} ({platforms_str})\n- **Quotes:**")
            for qtext, qlink, _ in quotes[:3]:
                sentiment_lines.append(f'  - "{qtext}" [Link]({qlink})')
        output.append("\n".join(sentiment_lines))

    if sections["competitor"]:
        output.append("## 🏢 By Competitor\n" + "\n\n".join(sections["competitor"]))
    if sections["ai"]:
        output.append("## 🤖 AI in DevOps\n" + "\n\n".join(sections["ai"]))
    if sections["analyst"]:
        output.append("## 🗞️ Analyst & Media\n" + "\n\n".join(sections["analyst"]))
    if sections["jobs"]:
        output.append("## 📈 Hiring Signals\n" + "\n\n".join(sections["jobs"]))
    if sections["other"]:
        output.append("## 📚 Other Updates\n" + "\n\n".join(sections["other"]))

    return "\n\n".join(output)

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
