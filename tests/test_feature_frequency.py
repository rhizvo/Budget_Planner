# tests/test_feature_frequency.py
import csv
import json
import os
from datetime import date, datetime, timedelta
from typing import List, Dict, cast
from pathlib import Path
import calendar
import pytest


# --- helpers --------------------------------------------------------------

def _write_budget(tmp_dir: Path, payload: dict):
    (tmp_dir / "my_budget_data.json").write_text(json.dumps(payload, indent=2))


def _load_rows(csv_path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with open(csv_path, newline="") as f:
        reader: csv.DictReader = csv.DictReader(f)  # explicit type helps PyCharm
        for row in reader:
            row_dict = cast(Dict[str, str], row)  # tell the type checker what this is
            rows.append(row_dict)
    return rows


def _parse_d(s):  # 'YYYY-MM-DD' -> date
    return datetime.strptime(s, "%Y-%m-%d").date()


def _row_week_bounds(row):
    return _parse_d(row["Week Start Date"]), _parse_d(row["Week End Date"])


def _week_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _in_week(d: date, row):
    ws, we = _row_week_bounds(row)
    return ws <= d <= we


def _floatish(s):
    try:
        return float(s)
    except Exception:
        return 0.0


# build expected dates (safe day choices to avoid month-end ambiguity)
def _expected_dates(freq: str, start_sched: date, start: date, end: date):
    dates = []
    if freq == "weekly":
        # align to the first on/after start
        first = start_sched if start_sched >= start else start + timedelta(
            days=(7 - ((start - start_sched).days % 7)) % 7)
        d = first
        while d <= end:
            dates.append(d)
            d += timedelta(days=7)
    elif freq == "bi-weekly":
        first = start_sched if start_sched >= start else start + timedelta(
            days=(14 - ((start - start_sched).days % 14)) % 14)
        d = first
        while d <= end:
            dates.append(d)
            d += timedelta(days=14)
    elif freq in ("monthly", "bi-monthly", "quarterly", "yearly"):
        step_months = {"monthly": 1, "bi-monthly": 2, "quarterly": 3, "yearly": 12}[freq]
        y, m, dom = start_sched.year, start_sched.month, start_sched.day
        # start from the very first >= start
        d = start_sched
        if d < start:
            # jump forward in month steps until >= start
            while d < start:
                m += step_months
                y += (m - 1) // 12
                m = ((m - 1) % 12) + 1
                last = calendar.monthrange(y, m)[1]
                d = date(y, m, min(dom, last))
        while d <= end:
            dates.append(d)
            m += step_months
            y += (m - 1) // 12
            m = ((m - 1) % 12) + 1
            last = calendar.monthrange(y, m)[1]
            d = date(y, m, min(dom, last))
    else:
        raise ValueError(f"Unsupported freq in test generator: {freq}")
    # clip to [start, end]
    return [d for d in dates if start <= d <= end]


# --- FEAT-01…07: Expense frequencies --------------------------------------

@pytest.mark.parametrize(
    "freq,start_sched,amount",
    [
        ("weekly", date(2026, 1, 6), 10.0),  # Tue
        ("bi-weekly", date(2026, 1, 6), 10.0),
        ("monthly", date(2026, 1, 5), 10.0),
        ("bi-monthly", date(2026, 1, 5), 10.0),
        ("quarterly", date(2026, 1, 5), 10.0),
        ("yearly", date(2026, 6, 15), 10.0),
    ],
    ids=[
        "FEAT-01-weekly", "FEAT-02-biweekly", "FEAT-03-monthly",
        "FEAT-04-bimonthly", "FEAT-05-quarterly", "FEAT-06-yearly"
    ]
)
def test_feat_expense_frequencies(e2e_test_environment, holidays, freq, start_sched, amount):
    """
    Verifies that a single expense fires on the exact dates dictated by its frequency (no holiday adjustment).
    """
    from main import BudgetPlannerApp  # app drives report generation

    start = date(2026, 1, 1)
    end = date(2026, 12, 31)

    budget_dict = {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "initial_debit_balance": 0.0,
        "savings_balances": {},
        "expense_categories": {
            "Bills": [
                {
                    "name": "Probe",
                    "amount": amount,
                    "frequency": freq,
                    "start_date_for_schedule": start_sched.isoformat(),
                    "category": "Bills"
                }
            ]
        },
        "savings_transfers": []
    }

    tmp_dir = e2e_test_environment
    _write_budget(tmp_dir, budget_dict)

    # run the app flow
    class MockUser:
        def __init__(self, directory):
            self.username = "test_user"
            self.directory = directory
            self.budget = None

        def load_budget(self):
            with open(os.path.join(self.directory, "my_budget_data.json")) as f:
                data = json.load(f)
            from main import Budget
            self.budget = Budget.from_dict(data)

    app = BudgetPlannerApp()
    app.current_user = MockUser(tmp_dir)
    app.current_user.load_budget()

    app._setup_holidays_and_recalculate(start, end)  # expenses: no holiday adjustment by design
    app._generate_report(start, end)

    csv_path = tmp_dir / "budget_plan.csv"
    assert csv_path.exists(), "Report file was not generated."

    rows: List[Dict[str, str]] = _load_rows(csv_path)
    col = "Bills: Probe"  # column naming uses f\"{category}: {name}\" in report building

    # expected dates
    expected_dates = _expected_dates(freq, start_sched, start, end)

    # assert: each expected date appears exactly in its week
    hits = 0
    for d in expected_dates:
        matched = False
        for row in rows:
            if _in_week(d, row):
                assert row.get(col, "") not in ("", None), f"Missing amount for {d} in column {col}"
                assert abs(_floatish(row[col]) - amount) < 1e-6, f"Wrong amount on {d}"
                matched = True
                hits += 1
                break
        assert matched, f"No report week covered expected date {d}"

    # assert: no extra occurrences
    total_in_col = sum(_floatish(r.get(col, 0.0)) for r in rows)
    assert abs(total_in_col - amount * len(expected_dates)) < 1e-6, "Extra/missing occurrences found"


# --- FEAT-08: Income twice-monthly (business-day adjustments) --------------

def test_feat_income_twice_monthly(e2e_test_environment, holidays):
    """
    Twice-monthly income must land on 15th and last day, adjusted to the previous business day.
    We validate weekly aggregation in the report.
    """
    from main import BudgetPlannerApp, calculate_twice_monthly_dates

    start = date(2026, 1, 1)
    end = date(2026, 12, 31)
    start_sched = date(2026, 1, 15)

    budget_dict = {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "initial_debit_balance": 0.0,
        "savings_balances": {},
        "income": {
            "name": "Primary Income",
            "amount": 1000.0,
            "frequency": "twice-monthly",
            "start_date_for_schedule": start_sched.isoformat()
        },
        "expense_categories": {},
        "savings_transfers": []
    }

    tmp_dir = e2e_test_environment
    _write_budget(tmp_dir, budget_dict)

    class MockUser:
        def __init__(self, directory):
            self.username = "test_user"
            self.directory = directory
            self.budget = None

        def load_budget(self):
            with open(os.path.join(self.directory, "my_budget_data.json")) as f:
                data = json.load(f)
            from main import Budget
            self.budget = Budget.from_dict(data)

    app = BudgetPlannerApp()
    app.current_user = MockUser(tmp_dir)
    app.current_user.load_budget()

    # App uses this function under the hood for twice-monthly
    app._setup_holidays_and_recalculate(start, end)
    app._generate_report(start, end)

    csv_path = tmp_dir / "budget_plan.csv"
    rows: List[Dict[str, str]] = _load_rows(csv_path)

    # expected paydays from the public function (already unit-tested)
    expected_paydays = calculate_twice_monthly_dates(start_sched, end, app.holidays)

    # group expected income by week
    expected_weekly = {}
    for d in expected_paydays:
        wk = _week_monday(d)
        expected_weekly[wk] = expected_weekly.get(wk, 0.0) + 1000.0

    # build actual income map from CSV
    actual_weekly = {}
    for row in rows:
        wk = _parse_d(row["Week Start Date"])
        actual_weekly[wk] = _floatish(row.get("Income Received", "0"))

    # compare (same keys and values)
    for wk, amt in expected_weekly.items():
        assert wk in actual_weekly, f"Missing week {wk} in report"
        assert abs(
            actual_weekly[wk] - amt) < 1e-6, f"Income mismatch for week {wk}: expected {amt}, got {actual_weekly[wk]}"

    # sanity: no unexpected income weeks containing money
    unexpected = [wk for wk, amt in actual_weekly.items() if amt > 0 and wk not in expected_weekly]
    assert not unexpected, f"Unexpected income detected in weeks: {unexpected}"


# --- FEAT-09: Dynamic period change ---------------------------------------

def test_feat_dynamic_period_change(e2e_test_environment, holidays):
    """
    Start with Jan 1–Mar 31 and a monthly 'Rent' on the 15th.
    Change to Feb 1–Apr 30, then generate the report:
      - January rent should disappear
      - April rent should appear
    """
    from main import BudgetPlannerApp

    jan_start, mar_end = date(2026, 1, 1), date(2026, 3, 31)
    feb_start, apr_end = date(2026, 2, 1), date(2026, 4, 30)

    budget_dict = {
        "start_date": jan_start.isoformat(),
        "end_date": mar_end.isoformat(),
        "initial_debit_balance": 0.0,
        "savings_balances": {},
        "expense_categories": {
            "Bills": [
                {
                    "name": "Rent",
                    "amount": 100.0,
                    "frequency": "monthly",
                    "start_date_for_schedule": date(2026, 1, 15).isoformat(),
                    "category": "Bills"
                }
            ]
        },
        "savings_transfers": []
    }

    tmp_dir = e2e_test_environment
    _write_budget(tmp_dir, budget_dict)

    class MockUser:
        def __init__(self, directory):
            self.username = "test_user"
            self.directory = directory
            self.budget = None

        def load_budget(self):
            with open(os.path.join(self.directory, "my_budget_data.json")) as f:
                data = json.load(f)
            from main import Budget
            self.budget = Budget.from_dict(data)

    app = BudgetPlannerApp()
    app.current_user = MockUser(tmp_dir)
    app.current_user.load_budget()

    # initial calc (not strictly necessary for the assertion but mirrors flow)
    app._setup_holidays_and_recalculate(jan_start, mar_end)

    # user changes period; app recalculates schedules for new period
    app.current_user.budget.start_date = feb_start
    app.current_user.budget.end_date = apr_end
    app._setup_holidays_and_recalculate(feb_start, apr_end)
    app._generate_report(feb_start, apr_end)

    rows: List[Dict[str, str]] = _load_rows(tmp_dir / "budget_plan.csv")
    col = "Bills: Rent"

    jan15 = date(2026, 1, 15)
    apr15 = date(2026, 4, 15)

    # assert January rent not present
    for row in rows:
        if _in_week(jan15, row):
            assert row.get(col, "") in ("", None, "0", "0.00"), "January rent should not be in the 'after' report"

    # assert April rent present exactly once
    occurrences = 0
    for row in rows:
        if _in_week(apr15, row):
            assert abs(_floatish(row.get(col, 0.0)) - 100.0) < 1e-6, "April rent missing or wrong amount"
            occurrences += 1
    assert occurrences == 1, f"Expected 1 April occurrence, found {occurrences}"
