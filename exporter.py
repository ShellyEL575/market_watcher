import os, time
from typing import List, Dict

def _ensure_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

def _today_slug(ts: int) -> str:
    # local date slug, e.g., 2025-09-30
    return time.strftime("%Y-%m-%d", time.localtime(ts))

def write_markdown(report_text: str, changes: List[Dict], out_dir: str = "reports") -> str:
    _ensure_dir(out_dir)
    now = int(time.time())
    slug = _today_slug(now)
    path = os.path.join(out_dir, f"{slug}.md")

    # Build a small per-site change table
    lines = [
        f"# Weekly Market Watch Report ({slug})",
        "",
        "## Change Overview",
        "",
        "| Site | +Added | -Removed |",
        "|------|:-----:|:--------:|",
    ]
    if changes:
        for c in changes:
            added = c.get("added_count", len(c.get("added", []) or []))
            removed = c.get("removed_count", len(c.get("removed", []) or []))
            lines.append(f"| {c['url']} | {added} | {removed} |")
    else:
        lines.append("| (no sites) | 0 | 0 |")

    lines += [
        "",
        "## Summary & Recommendations",
        "",
        report_text.strip() if report_text else "_(empty)_",
        "",
    ]

    content = "\n".join(lines)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path
