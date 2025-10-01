import difflib

def compute_changes(current_pages, prev_snapshots):
    changes = []
    for page in current_pages:
        url = page["url"]
        curr_text = page.get("text", "") or ""
        prev_text = prev_snapshots.get(url, "") or ""

        curr_lines = [ln.strip().lower() for ln in curr_text.splitlines() if ln.strip()]

        if not prev_text:
            # Baseline: treat all current lines as added
            added = curr_lines[:200]  # cap to avoid huge prompts
            removed = []
        else:
            prev_lines = [ln.strip().lower() for ln in prev_text.splitlines() if ln.strip()]
            diff = list(difflib.unified_diff(prev_lines, curr_lines, lineterm=""))
            added, removed = [], []
            for ln in diff:
                if ln.startswith("+ ") and not ln.startswith("+++"):
                    added.append(ln[2:].strip())
                elif ln.startswith("- ") and not ln.startswith("---"):
                    removed.append(ln[2:].strip())

        changes.append({
            "url": url,
            "added": added,
            "removed": removed,
            "added_count": len(added),
            "removed_count": len(removed),
        })
    return changes
