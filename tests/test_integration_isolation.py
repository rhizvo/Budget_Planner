# tests/test_integration_isolation.py
import csv
import json
import os
import shutil
from pathlib import Path

import pytest


TESTS_DIR = Path(__file__).parent
HAPPY_PATH_DIR = TESTS_DIR / "test_data" / "00_happy_path"  # reuse a stable case


def _read_csv_to_list_of_dicts(filepath: Path):
    rows = []
    with open(filepath, mode="r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            processed = {}
            for k, v in row.items():
                try:
                    processed[k] = f"{float(v):.2f}"
                except (TypeError, ValueError):
                    processed[k] = v
            rows.append(processed)
    return rows


def _write_budget(dest_dir: Path, budget_dict: dict):
    dest_dir.mkdir(parents=True, exist_ok=True)
    with open(dest_dir / "my_budget_data.json", "w") as f:
        json.dump(budget_dict, f, indent=2)


def _copy_holidays_into(user_dir: Path, from_dir: Path):
    src = from_dir / "holidays"
    dst = user_dir / "holidays"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def _generate_report_for(user_dir: Path):
    # local MockUser mimicking tests/test_e2e.py
    class MockUser:
        def __init__(self, directory: Path):
            self.username = directory.name
            self.directory = str(directory)  # app expects str path
            self.budget = None

        def load_budget(self):
            with open(os.path.join(self.directory, "my_budget_data.json"), "r") as f:
                data = json.load(f)
            from main import Budget  # import here to avoid global test imports side-effects
            self.budget = Budget.from_dict(data)

    from main import BudgetPlannerApp

    app = BudgetPlannerApp()
    app.current_user = MockUser(user_dir)
    app.current_user.load_budget()

    start_date = app.current_user.budget.start_date
    end_date = app.current_user.budget.end_date

    app._setup_holidays_and_recalculate(start_date, end_date)
    app._generate_report(start_date, end_date)

    return user_dir / "budget_plan.csv"


@pytest.mark.integration
def test_multi_user_data_isolation(e2e_test_environment):
    """
    INT-01: Verify UserA's report is unaffected by changes to UserB.
    Steps (from test plan):
      1) Generate report for UserA.
      2) Set up and make changes to UserB.
      3) Re-generate UserA report and assert identical.
    """

    base = e2e_test_environment
    user_a = base / "alice"
    user_b = base / "bob"

    # Prepare per-user holiday folders (app reads from <user>/holidays)
    _copy_holidays_into(user_a, base)
    _copy_holidays_into(user_b, base)

    # Load a stable budget and write it to both users
    with open(HAPPY_PATH_DIR / "budget.json", "r") as f:
        base_budget = json.load(f)

    _write_budget(user_a, base_budget)
    _write_budget(user_b, base_budget)

    # 1) First run for UserA -> baseline
    a_csv_1 = _generate_report_for(user_a)
    assert a_csv_1.exists(), "UserA report not generated (first run)."
    a_rows_1 = _read_csv_to_list_of_dicts(a_csv_1)

    # 2) Generate UserB once, then CHANGE UserB and generate again (to ensure isolation scenario is meaningful)
    b_csv_1 = _generate_report_for(user_b)
    assert b_csv_1.exists(), "UserB report not generated (first run)."

    # SNAPSHOT baseline BEFORE mutation (so we don't re-read the overwritten file)
    b_rows_1 = _read_csv_to_list_of_dicts(b_csv_1)

    # Mutate UserB's budget: tweak an amount and add a one-time expense
    mutated = json.loads(json.dumps(base_budget))  # deep copy
    try:
        mutated["expense_categories"]["Groceries"][0]["amount"] = (
                mutated["expense_categories"]["Groceries"][0]["amount"] + 23.45
        )
    except Exception:
        pass
    mutated.setdefault("expense_categories", {}).setdefault("Bills", []).append(
        {
            "name": "Coffee Grinder",
            "amount": 99.0,
            "frequency": "one-time",
            "dates": [str(base_budget["start_date"])],
            "category": "Bills",
        }
    )

    _write_budget(user_b, mutated)

    # Generate again and read the CHANGED report
    b_csv_2 = _generate_report_for(user_b)
    assert b_csv_2.exists(), "UserB report not generated (after mutation)."
    b_rows_2 = _read_csv_to_list_of_dicts(b_csv_2)

    assert b_rows_1 != b_rows_2, "Mutation to UserB did not affect UserB's report (sanity check)."

    # 3) Re-run UserA and ensure its report is IDENTICAL to baseline
    a_csv_2 = _generate_report_for(user_a)
    assert a_csv_2.exists(), "UserA report not generated (second run)."
    a_rows_2 = _read_csv_to_list_of_dicts(a_csv_2)

    assert a_rows_1 == a_rows_2, "UserA's report changed after modifying UserB (isolation failure)."
