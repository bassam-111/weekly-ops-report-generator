# Weekly Ops Report Generator

A small Python/Pandas command-line tool that turns a task log CSV into a
plain-English weekly operations report — the kind of Monday-morning summary
an Operations Executive actually sends to a team: what got done, what was
on time, what's overdue, who's carrying what, and what rolls into next week.

## What it does

- Reads tasks from a plain CSV (`data/tasks.csv`) — no database needed.
- Computes for any Monday–Sunday week:
  - Tasks completed, created, and due in the week
  - On-time delivery % (completed on or before the due date)
  - Overdue tasks with ageing buckets (1–3, 4–7, 8+ days)
  - Workload per owner (total / done / open / blocked)
  - Blocked tasks with the recorded reason
  - Carry-over list for next week
- Writes a Markdown report (`output/weekly-report-YYYY-MM-DD.md`) and a
  per-owner summary CSV (`output/summary-by-owner.csv`).

## How to run

```bash
pip install -r requirements.txt
python weekly_report.py --week-start 2026-11-02
# or default to the most recent Monday:
python weekly_report.py
```

Options: `--input` (task CSV), `--week-start YYYY-MM-DD`, `--out-dir`.

## Sample output

```
Week: 2026-11-02 to 2026-11-08
Completed: 13 | Created: 21 | Open: 11 | Overdue: 3 | Blocked: 2
On-time delivery: 76.9%
Report: output/weekly-report-2026-11-02.md
Summary: output/summary-by-owner.csv
```

From the generated report:

```markdown
## Headline numbers
- Tasks completed this week: **13**
- On-time delivery: **76.9%** (10 of 13 completed on or before due date)
- Open tasks: **11** (3 overdue)
- Blocked tasks: **2**

## Blocked — needs attention
- **T-116** — Escalate unresolved ticket #9912 (Ayesha, due 2026-11-02):
  Vendor has not responded in 6 days
- **T-122** — Follow up on invoice dispute #771 (Ayesha, due 2026-11-04):
  Client finance contact on leave
```

## Tests

```bash
python test_weekly_report.py
# All tests passed.
```

## Skills used

Python, Pandas, CSV data handling — all on the resume. No cloud, no
frameworks beyond Pandas. All sample data is fictional.

## Files

- `weekly_report.py` — the report generator (CLI)
- `test_weekly_report.py` — unit tests for the metrics and rendering
- `data/tasks.csv` — 24 fictional tasks for the week of 2–8 Nov 2026
- `output/weekly-report-2026-11-02.md` — sample generated report
- `output/summary-by-owner.csv` — sample per-owner summary
- `requirements.txt` — pandas, pytest
