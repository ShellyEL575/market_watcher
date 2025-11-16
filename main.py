import os, time
from dotenv import load_dotenv
from scraper import fetch_site_batch
from summarize import write_summary
from storage import upsert_snapshots, save_report
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

    # -----------------------------
    # 🔥 USE LATEST SNAPSHOTS
    # -----------------------------
    # Instead of diffing, summarize the latest content directly. This keeps
    # prompts focused on current signals and avoids missing fresh context when
    # prior snapshots are incomplete.
    print("🧮 Skipping diffs; summarizing latest content...")
    chosen_changes = make_baseline_changes(pages)

    # Preserve social quotes for downstream sentiment grouping
    for change in chosen_changes:
        page = next((p for p in pages if p["url"] == change["url"]), {})
        source_type = page.get("source_type", "official")
        change["source_type"] = source_type
        if source_type == "social":
            change["quotes"] = page.get("quotes", [])
        else:
            change["quotes"] = []

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
