import os, time
from dotenv import load_dotenv
from scraper import fetch_site_batch
from diffing import compute_changes
from summarize import write_summary
from storage import upsert_snapshots, get_last_snapshots, save_report
from exporter import write_markdown

def _to_lines(s):
    return [ln.strip().lower() for ln in (s or "").splitlines() if ln.strip()]

def make_baseline_changes(pages, cap_per_site=200):
    baseline = []
    for p in pages:
        lines = _to_lines(p.get("text", ""))
        baseline.append({
            "url": p["url"],
            "added": lines[:cap_per_site],
            "removed": [],
            "added_count": min(len(lines), cap_per_site),
            "removed_count": 0,
            "source_type": p.get("source_type", "official"),
            "quotes": p.get("quotes", []),
        })
    return baseline

def run_weekly():
    sites_yaml = os.path.join(os.path.dirname(__file__), "sites.yaml")

    print("🔍 Fetching site content...")
    pages = fetch_site_batch(sites_yaml)

    if not pages:
        msg = "No pages fetched this run (all sites skipped or failed)."
        now = int(time.time())
        save_report(now, msg)
        md_path = write_markdown(msg, [])
        print("\n✅ Weekly Market Watch Report\n" + "="*32 + "\n")
        print(msg)
        print(f"\n(saved to SQLite, Markdown: {md_path})")
        return

    print(f"✅ Fetched {len(pages)} pages.")

    print("🗂 Comparing with last snapshots...")
    prev = get_last_snapshots([p["url"] for p in pages])

    print("🧮 Computing diffs...")
    changes = compute_changes(pages, prev)

    force = os.getenv("FORCE_SUMMARY") == "1"
    no_real_diffs = not changes or all(
        not (c.get("added") or c.get("removed")) for c in changes
    )

    # -----------------------------
    # 🔥 FILTER + ENRICH CHANGES
    # -----------------------------
    if force or no_real_diffs:
        print("📌 No real diffs detected. Generating baseline summary...")
        chosen_changes = make_baseline_changes(pages)

    else:
        print("📊 Real diffs detected. Using them for summary...")

        chosen_changes = []

        for c in changes:
            # Skip empty diffs
            if not (c.get("added") or c.get("removed")):
                continue

            # Find related page metadata
            page = next((p for p in pages if p["url"] == c["url"]), {})
            source_type = page.get("source_type", "official")

            # SOCIAL‑ONLY QUOTES HERE
            if source_type == "social":
                filtered_quotes = page.get("quotes", [])
            else:
                filtered_quotes = []

            new_change = {
                **c,
                "source_type": source_type,
                "quotes": filtered_quotes,
            }

            chosen_changes.append(new_change)

    # -----------------------------
    # LLM SUMMARY
    # -----------------------------
    print("🧠 Sending diffs to OpenAI for summary...")
    report = write_summary(chosen_changes)
    print("📝 Received summary from OpenAI.")

    # -----------------------------
    # STORE SNAPSHOTS + REPORT
    # -----------------------------
    upsert_snapshots(pages)

    now = int(time.time())
    print("📤 Writing Markdown report...")
    md_path = write_markdown(report, chosen_changes)
    save_report(now, report)

    # -----------------------------
    # FINAL OUTPUT
    # -----------------------------
    print("\n✅ Weekly Market Watch Report\n" + "="*32 + "\n")
    print(report)
    print(f"\n(saved to SQLite, Markdown: {md_path})")

if __name__ == "__main__":
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️ OPENAI_API_KEY not set. Set it in .env or environment.")
        raise SystemExit(1)
    run_weekly()
