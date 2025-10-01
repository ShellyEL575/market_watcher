Market Watcher Agent

This is a simple local agent that:

Scrapes websites and RSS feeds (with polite retries and optional CSS selectors)

Stores snapshots in a local SQLite database

Computes diffs between weekly content

Uses OpenAI to generate structured summaries and recommendations

Saves each report in the database and exports it as a Markdown file

Setup

Install Python 3.9+

Create a virtual environment (recommended):

python -m venv .venv
source .venv/bin/activate   # macOS/Linux
.venv\Scripts\activate      # Windows

Install dependencies:

pip install -r requirements.txt

Create a .env file with your OpenAI API key:

OPENAI_API_KEY=your-api-key-here

Run the watcher:

python main.py
Config

sites.yaml contains your list of sites. Add URLs and optional CSS selectors to target main content.

All snapshots and reports are saved in market_watcher.db (SQLite).

Markdown summaries are saved in the reports/ folder (e.g., reports/2025-09-30.md).

Automation

macOS/Linux: Add a cronjob to run main.py weekly.

Windows: Use Task Scheduler to automate the run.

Prompt Persona

The OpenAI summary is tailored for a VP of Product Marketing. It generates:

Executive Summary

Competitor Breakdown

Analyst & Community Insights

Recommendations for the PMM team

You can modify summarize.py to adjust tone, persona, or report structure.

Next Steps

Turn summaries into a game for kids or non-tech users

Add Slack or email notifications

Build a web UI to browse reports and stats

Extend to support new site types or analysis styles

Tips for Faster Runs

If sites like linearb.io or grafana.com frequently fail, comment them out in sites.yaml to avoid long fallback delays.

You can also reduce retries in scraper.py by changing _fetch(..., retries=4) to something lower like retries=2.

Credits

Created with ❤️ to help you track market trends, week by week.