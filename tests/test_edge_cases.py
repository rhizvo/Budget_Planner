import csv
import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Dict, cast

import pytest


# Reuse helpers from this file if they exist; otherwise keep these local:
def _write_budget(tmp_dir: Path, payload: dict):
    (tmp_dir / "my_budget_data.json").write_text(json.dumps(payload, indent=2))


def _load_rows(csv_path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with open(csv_path, newline="") as f:
        reader: csv.DictReader = csv.DictReader(f)
        for row in reader:
            row_dict = cast(Dict[str, str], row)
            rows.append({k: (v if v is not None else "") for k, v in row_dict.items()})
    return rows


def _parse_d(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _week_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _floatish(s) -> float:
    try:
        return float(s)
    except Exception:
        return 0.0


@pytest.mark.parametrize(
    "year, month, holiday_strings, expected_adjusted_last",
    [
        # A) Last day is Sunday (2027-02-28), and the Friday before (2027-02-26) is a holiday -> shift to Thursday
        # 2027-02-25
        (2027, 2, ["Chained Holiday,2027-02-26"], date(2027, 2, 25)),

        # B) Last day is Saturday (2026-10-31) and that very day is a holiday -> shift to Friday 2026-10-30
        (2026, 10, ["Month-End Holiday,2026-10-31"], date(2026, 10, 30)),
    ],
    ids=["EDGE-02B-sun-end+fri-holiday", "EDGE-02C-sat-end+holiday"],
)
def test_edge_weekend_holiday_chaining_for_last_of_month(e2e_test_environment, year, month, holiday_strings,
                                                         expected_adjusted_last):
    """
    Twice-monthly income: ensure the *last-of-month* payday moves to the previous business day
    when the month-end falls on a weekend and/or a holiday (including chained back-offs).
    """
    from main import BudgetPlannerApp, calculate_twice_monthly_dates

    start = date(year, month, 1)
    # month end:
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = (date(year, month + 1, 1) - timedelta(days=1))

    tmp_dir = e2e_test_environment
    holidays_dir = tmp_dir / "holidays"
    holidays_dir.mkdir(exist_ok=True)
    # Write the year-specific holidays file the app expects
    (holidays_dir / f"holidays_{year}.txt").write_text("\n".join(holiday_strings) + "\n")

    budget_dict = {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "initial_debit_balance": 0.0,
        "savings_balances": {},
        "income": {
            "name": "Primary Income",
            "amount": 1000.0,
            "frequency": "twice-monthly",
            # Start schedule anywhere inside the period; the function will compute the 15th & last-of-month
            "start_date_for_schedule": start.isoformat()
        },
        "expense_categories": {},
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

    # Recalculate with holidays, then produce the CSV
    app._setup_holidays_and_recalculate(start, end)
    app._generate_report(start, end)

    rows = _load_rows(tmp_dir / "budget_plan.csv")

    # Compute holiday/weekend-adjusted paydays using the same function as the app
    paydays = calculate_twice_monthly_dates(start, end, app.holidays)
    # filter for the last-of-month in this month
    last_paydays = [d for d in paydays if d.year == year and d.month == month]
    assert last_paydays, "No paydays found for the target month—unexpected."

    # The adjusted last-of-month should be exactly as expected
    assert expected_adjusted_last in last_paydays, f"Adjusted last-of-month payday should be {expected_adjusted_last}, got {sorted(last_paydays)}"

    # Confirm it's reflected in the CSV 'Income Received' for that week
    wk = _week_monday(expected_adjusted_last)
    income_by_week = {_parse_d(r["Week Start Date"]): _floatish(r.get("Income Received", "0")) for r in rows}
    assert wk in income_by_week, f"Report missing the week for {expected_adjusted_last}"
    assert abs(income_by_week[
                   wk] - 1000.0) < 1e-6, f"Expected $1000 income in week of {expected_adjusted_last}, got {income_by_week[wk]}"

    # And ensure the literal month-end date itself is NOT used as a payday
    month_end = end
    assert month_end not in paydays, f"Month-end {month_end} should not be a payday when it's weekend/holiday-adjusted"
