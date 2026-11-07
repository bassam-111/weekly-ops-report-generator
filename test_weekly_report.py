"""Tests for weekly_report.py — run with: python -m pytest test_weekly_report.py -v
(or: python test_weekly_report.py for a plain-assert run)."""

import io
from datetime import date

import pandas as pd

from weekly_report import compute_metrics, last_monday, render_markdown

SAMPLE = """task_id,title,owner,status,priority,created_date,due_date,completed_date,blocker
A-1,On time task,Ana,Done,High,2026-11-02,2026-11-03,2026-11-03,
A-2,Late task,Ana,Done,Medium,2026-11-02,2026-11-03,2026-11-05,
A-3,Overdue open task,Ben,In Progress,High,2026-11-02,2026-11-04,,
A-4,Blocked task,Ben,Blocked,High,2026-11-02,2026-11-02,,Waiting on vendor
A-5,Future task,Ana,To Do,Low,2026-11-06,2026-11-20,,
"""


def _df():
    return pd.read_csv(io.StringIO(SAMPLE), parse_dates=["created_date", "due_date", "completed_date"])


def test_last_monday():
    # 2026-11-07 is a Saturday; the Monday of that week is 2026-11-02.
    assert last_monday(date(2026, 11, 7)) == date(2026, 11, 2)
    assert last_monday(date(2026, 11, 2)) == date(2026, 11, 2)


def test_metrics():
    m = compute_metrics(_df(), date(2026, 11, 2))
    assert len(m["done_in_week"]) == 2
    assert len(m["on_time"]) == 1
    assert m["on_time_pct"] == 50.0
    assert len(m["overdue"]) == 2          # A-3 and A-4 are open and past due
    assert len(m["blocked"]) == 1
    assert len(m["carry_over"]) == 2       # A-3, A-4 due on/before week end
    assert m["ageing"]["4-7 days overdue"] == 2


def test_render_contains_headline():
    m = compute_metrics(_df(), date(2026, 11, 2))
    md = render_markdown(m)
    assert "Weekly Ops Report" in md
    assert "50.0%" in md
    assert "Blocked task" in md
    assert "Waiting on vendor" in md


if __name__ == "__main__":
    test_last_monday()
    test_metrics()
    test_render_contains_headline()
    print("All tests passed.")
