"""Weekly Ops Report Generator.

Reads a task log CSV and builds a plain-English weekly operations report:
completion rate, on-time delivery, overdue ageing, workload per owner,
blockers, and what carries over into next week.

Usage:
    python weekly_report.py [--input data/tasks.csv]
                            [--week-start 2026-11-02]
                            [--out-dir output]

The week is Monday-Sunday starting at --week-start (defaults to the most
recent Monday). Output is a Markdown report plus a per-owner summary CSV.
All sample data is fictional.
"""

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

DATE_COLS = ["created_date", "due_date", "completed_date"]
OPEN_STATUSES = {"To Do", "In Progress", "Blocked"}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Generate a weekly ops report from a task CSV.")
    parser.add_argument("--input", default="data/tasks.csv", help="Task log CSV (default: data/tasks.csv)")
    parser.add_argument("--week-start", default=None,
                        help="Monday of the report week, YYYY-MM-DD (default: most recent Monday)")
    parser.add_argument("--out-dir", default="output", help="Directory for report files (default: output)")
    return parser.parse_args(argv)


def last_monday(today=None):
    today = today or date.today()
    return today - timedelta(days=today.weekday())


def load_tasks(path):
    df = pd.read_csv(path, parse_dates=DATE_COLS)
    df["completed_date"] = pd.to_datetime(df["completed_date"], errors="coerce")
    return df


def compute_metrics(df, week_start):
    """Return a dict of report metrics for the week starting week_start."""
    week_end = week_start + timedelta(days=6)
    ws, we = pd.Timestamp(week_start), pd.Timestamp(week_end)

    done = df[df["status"] == "Done"].copy()
    done_in_week = done[(done["completed_date"] >= ws) & (done["completed_date"] <= we)]
    created_in_week = df[(df["created_date"] >= ws) & (df["created_date"] <= we)]
    due_in_week = df[(df["due_date"] >= ws) & (df["due_date"] <= we)]

    on_time = done_in_week[done_in_week["completed_date"] <= done_in_week["due_date"]]
    on_time_pct = round(100 * len(on_time) / len(done_in_week), 1) if len(done_in_week) else 0.0

    open_tasks = df[df["status"].isin(OPEN_STATUSES)].copy()
    overdue = open_tasks[open_tasks["due_date"] < we]
    overdue = overdue.assign(age_days=(we - overdue["due_date"]).dt.days)
    carry_over = open_tasks[open_tasks["due_date"] <= we].copy()

    blocked = df[df["status"] == "Blocked"]

    per_owner = (
        df.groupby("owner")
        .agg(
            total=("task_id", "count"),
            done=("status", lambda s: (s == "Done").sum()),
            open=("status", lambda s: s.isin(OPEN_STATUSES).sum()),
            blocked=("status", lambda s: (s == "Blocked").sum()),
        )
        .reset_index()
        .sort_values("total", ascending=False)
    )

    def ageing_bucket(age):
        if age <= 3:
            return "1-3 days overdue"
        if age <= 7:
            return "4-7 days overdue"
        return "8+ days overdue"

    ageing = (
        overdue.assign(bucket=overdue["age_days"].map(ageing_bucket))
        .groupby("bucket")
        .size()
        .reindex(["1-3 days overdue", "4-7 days overdue", "8+ days overdue"], fill_value=0)
    )

    return {
        "week_start": week_start,
        "week_end": week_end,
        "done_in_week": done_in_week,
        "created_in_week": created_in_week,
        "due_in_week": due_in_week,
        "on_time": on_time,
        "on_time_pct": on_time_pct,
        "open_tasks": open_tasks,
        "overdue": overdue,
        "carry_over": carry_over,
        "blocked": blocked,
        "per_owner": per_owner,
        "ageing": ageing,
    }


def render_markdown(m):
    lines = []
    ws, we = m["week_start"], m["week_end"]
    lines.append(f"# Weekly Ops Report — {ws:%d %b} to {we:%d %b %Y}")
    lines.append("")
    lines.append("## Headline numbers")
    lines.append("")
    lines.append(f"- Tasks completed this week: **{len(m['done_in_week'])}**")
    lines.append(f"- Tasks created this week: **{len(m['created_in_week'])}**")
    lines.append(f"- Tasks due this week: **{len(m['due_in_week'])}**")
    lines.append(f"- On-time delivery: **{m['on_time_pct']}%** "
                 f"({len(m['on_time'])} of {len(m['done_in_week'])} completed on or before due date)")
    lines.append(f"- Open tasks: **{len(m['open_tasks'])}** ({len(m['overdue'])} overdue)")
    lines.append(f"- Blocked tasks: **{len(m['blocked'])}**")
    lines.append("")
    lines.append("## Overdue ageing")
    lines.append("")
    for bucket, count in m["ageing"].items():
        lines.append(f"- {bucket}: **{count}**")
    lines.append("")
    lines.append("## Workload per owner")
    lines.append("")
    lines.append("| Owner | Total | Done | Open | Blocked |")
    lines.append("|-------|------:|-----:|-----:|--------:|")
    for _, r in m["per_owner"].iterrows():
        lines.append(f"| {r['owner']} | {r['total']} | {r['done']} | {r['open']} | {r['blocked']} |")
    lines.append("")
    lines.append("## Blocked — needs attention")
    lines.append("")
    if len(m["blocked"]) == 0:
        lines.append("Nothing blocked this week. 🎉")
    else:
        for _, r in m["blocked"].iterrows():
            lines.append(f"- **{r['task_id']}** — {r['title']} ({r['owner']}, due {r['due_date'].date()}): "
                         f"{r['blocker'] or 'no reason recorded'}")
    lines.append("")
    lines.append("## Carry-over into next week")
    lines.append("")
    if len(m["carry_over"]) == 0:
        lines.append("No open tasks due this week or earlier — clean slate.")
    else:
        for _, r in m["carry_over"].sort_values("due_date").iterrows():
            lines.append(f"- **{r['task_id']}** — {r['title']} ({r['owner']}, {r['status']}, "
                         f"due {r['due_date'].date()})")
    lines.append("")
    lines.append("## Completed this week")
    lines.append("")
    for _, r in m["done_in_week"].sort_values("completed_date").iterrows():
        late = " (late)" if r["completed_date"] > r["due_date"] else ""
        lines.append(f"- {r['task_id']} — {r['title']} ({r['owner']}, completed {r['completed_date'].date()}){late}")
    lines.append("")
    return "\n".join(lines)


def main(argv=None):
    args = parse_args(argv)
    week_start = (
        date.fromisoformat(args.week_start) if args.week_start else last_monday()
    )
    df = load_tasks(args.input)
    m = compute_metrics(df, week_start)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / f"weekly-report-{week_start:%Y-%m-%d}.md"
    report_path.write_text(render_markdown(m), encoding="utf-8")
    summary_path = out_dir / "summary-by-owner.csv"
    m["per_owner"].to_csv(summary_path, index=False)

    print(f"Week: {week_start} to {m['week_end']}")
    print(f"Completed: {len(m['done_in_week'])} | Created: {len(m['created_in_week'])} | "
          f"Open: {len(m['open_tasks'])} | Overdue: {len(m['overdue'])} | Blocked: {len(m['blocked'])}")
    print(f"On-time delivery: {m['on_time_pct']}%")
    print(f"Report: {report_path}")
    print(f"Summary: {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
