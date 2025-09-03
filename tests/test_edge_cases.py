# tests/test_edge_cases.py
import csv
import json
import os
import calendar
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Dict, cast

import pytest


# ----------------- helpers -----------------

def _write_budget(tmp_dir: Path, payload: dict):
    (tmp_dir / "my_budget_data.json").write_text(json.dumps(payload, indent=2))


def _load_rows(csv_path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with open(csv_path, newline="") as f:
        reader: csv.DictReader = csv.DictReader(f)
        for row in reader:
            row_dict = cast(Dict[str, str], row)
            # normalize None -> ""
            rows.append({k: (v if v is not None else "") for k, v in row_dict.items()})
    return rows


def _parse_d(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _row_week_bounds(row: Dict[str, str]):
    return _parse_d(row["Week Start Date"]), _parse_d(row["Week End Date"])


def _in_week(d: date, row: Dict[str, str]) -> bool:
    ws, we = _row_week_bounds(row)
    return ws <= d <= we


def _floatish(s) -> float:
    try:
        return float(s)
    except Exception:
        return 0.0


def _week_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


# =========================================================
# EDGE-01: Pro-Rated Income Expiry (E2E)
# Goal from plan: ensure a “Final Pro-rated Paycheck” expense is created with the correct negative amount on the expiry date.
# =========================================================

def test_edge_pro_rated_income_expiry_e2e(e2e_test_environment):
    """
    Twice-monthly income expires a few days after the last full payday.
    Expect a negative 'Income: Final Pro-rated Paycheck' line on the expiry week with the correct amount.
    """
    from main import \
        BudgetPlannerApp  # report builder uses "{category}: {name}" keys for expense columns【turn17file9†L14-L18】

    start = date(2026, 1, 1)
    end = date(2026, 1, 31)
    last_full_payday = date(2026, 1, 15)
    expiry = date(2026, 1, 20)

    budget_dict = {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "initial_debit_balance": 0.0,
        "savings_balances": {},
        "income": {
            "name": "Primary Income",
            "amount": 2000.0,
            "frequency": "twice-monthly",
            "start_date_for_schedule": last_full_payday.isoformat(),
            "expiry_date": expiry.isoformat()
        },
        "expense_categories": {},
        "savings_transfers": []
    }

    tmp_dir = e2e_test_environment
    _write_budget(tmp_dir, budget_dict)

    # run through the app
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

    app._setup_holidays_and_recalculate(start, end)
    app._generate_report(start, end)

    # compute expected pro-rated amount exactly like the app does【turn17file6†L16-L23】【turn17file6†L25-L37】
    days_in_month = calendar.monthrange(last_full_payday.year, last_full_payday.month)[1]  # 31
    period_days = days_in_month / 2.0
    pro_days = (expiry - last_full_payday).days  # 5
    expected_negative = -((2000.0 / period_days) * pro_days)

    rows = _load_rows(tmp_dir / "budget_plan.csv")
    col = "Income: Final Pro-rated Paycheck"  # built from f"{category}: {name}"【turn17file9†L14-L18】

    # find the expiry week row and assert amount ~= expected_negative
    found = False
    for row in rows:
        if _in_week(expiry, row):
            amt = _floatish(row.get(col, "0"))
            assert abs(amt - expected_negative) < 1e-2, f"Expected {expected_negative:.2f}, got {amt:.2f}"
            found = True
            break
    assert found, "No report row found for the expiry week containing the pro-rated paycheck"


# =========================================================
# EDGE-02: Leap Year & Holiday Adjustment (E2E)
# Plan asks: Feb 2028 bill on Feb 29 must occur; payday falling on a holiday must move to previous business day【turn17file15†L35-L43】.
# =========================================================

def test_edge_leap_year_and_holiday_adjustment_e2e(e2e_test_environment):
    """
    Period: Feb–Mar 2028 (leap year).
    - Monthly bill scheduled on the 29th should hit on Feb 29, 2028.
    - Twice-monthly income: last-of-month in Feb would be 29th, but mark 29th as a holiday
      so payday must shift to the previous business day.
    """
    from main import BudgetPlannerApp, \
        calculate_twice_monthly_dates  # holiday-aware calculation for twice-monthly【turn17file3†L46-L61】

    start = date(2028, 2, 1)
    end = date(2028, 3, 31)

    tmp_dir = e2e_test_environment
    holidays_dir = tmp_dir / "holidays"
    holidays_dir.mkdir(exist_ok=True)
    # Create the 2028 holiday file expected by the app’s loader【turn17file13†L12-L24】【turn17file13†L32-L35】
    (holidays_dir / "holidays_2028.txt").write_text("Leap Day,2028-02-29\n")

    budget_dict = {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "initial_debit_balance": 0.0,
        "savings_balances": {},
        "income": {
            "name": "Primary Income",
            "amount": 1000.0,
            "frequency": "twice-monthly",
            "start_date_for_schedule": start.isoformat()
        },
        "expense_categories": {
            "Bills": [
                {
                    "name": "Rent29",
                    "amount": 10.0,
                    "frequency": "monthly",
                    "start_date_for_schedule": date(2028, 2, 29).isoformat(),
                    "category": "Bills"
                }
            ]
        },
        "savings_transfers": []
    }

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

    app._setup_holidays_and_recalculate(start, end)
    app._generate_report(start, end)

    rows = _load_rows(tmp_dir / "budget_plan.csv")

    # --- Part A: Bill on Feb 29 appears ---
    bill_col = "Bills: Rent29"
    feb29 = date(2028, 2, 29)
    present = False
    for row in rows:
        if _in_week(feb29, row):
            assert abs(_floatish(row.get(bill_col, "0")) - 10.0) < 1e-6, "Feb 29 bill missing or wrong amount"
            present = True
            break
    assert present, "Did not find the Feb 29 bill occurrence in the report"

    # --- Part B: Last-of-Feb payday moves off the holiday (29th) to previous business day ---
    expected_paydays = calculate_twice_monthly_dates(start, end, app.holidays)  # holiday-aware dates
    # Specifically check that 2028-02-29 is NOT a payday, while the previous business day IS.
    assert date(2028, 2, 29) not in expected_paydays, "Payday should not land on the holiday (Feb 29)"
    # Find the adjusted last-of-Feb payday (likely Feb 28, unless it was also a holiday/weekend)
    adjusted_feb_last = max(d for d in expected_paydays if d.month == 2 and d.year == 2028)
    wk = _week_monday(adjusted_feb_last)

    # Map CSV income by week start
    actual_income_by_week = {_parse_d(r["Week Start Date"]): _floatish(r.get("Income Received", "0.0")) for r in rows}
    assert wk in actual_income_by_week, f"Missing income week covering {adjusted_feb_last}"
    assert abs(actual_income_by_week[
                   wk] - 1000.0) < 1e-6, f"Expected $1000 income in week of {adjusted_feb_last}, got {actual_income_by_week[wk]}"
