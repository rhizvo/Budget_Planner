import csv
import json
from pathlib import Path
import os
import pytest

# --- New: Automatically find all test case directories ---
TEST_DATA_ROOT = Path(__file__).parent / "test_data"
# List all the test case directories, ignoring hidden ones like .pytest_cache
TEST_CASES = [d for d in TEST_DATA_ROOT.iterdir() if d.is_dir() and not d.name.startswith('.')]


def _read_csv_to_list_of_dicts(filepath):
    # This helper function remains the same
    data = []
    with open(filepath, mode='r', newline='') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            processed_row = {}
            for key, value in row.items():
                try:
                    processed_row[key] = f"{float(value):.2f}"
                except (ValueError, TypeError):
                    processed_row[key] = value
            data.append(processed_row)
    return data


# --- New: This decorator tells pytest to run the test for each directory ---
@pytest.mark.parametrize("test_case_dir", TEST_CASES, ids=[d.name for d in TEST_CASES])
def test_end_to_end_report_generation(e2e_test_environment, test_case_dir):
    """
    Tests the full flow. This test is now parametrized to run against
    every test case directory in tests/test_data.
    """
    from main import BudgetPlannerApp

    print(f"\nRunning E2E Test for: {test_case_dir.name}...")

    temp_user_dir = e2e_test_environment

    # --- New: Copy the correct budget.json for the current test run ---
    source_budget_file = test_case_dir / "budget.json"
    dest_budget_file = temp_user_dir / "my_budget_data.json"
    dest_budget_file.write_text(source_budget_file.read_text())

    # The rest of the test logic proceeds as before
    class MockUser:
        def __init__(self, directory):
            self.username = "test_user"
            self.directory = directory
            self.budget = None

        def load_budget(self):
            with open(os.path.join(self.directory, 'my_budget_data.json'), 'r') as f:
                data = json.load(f)
            from main import Budget
            self.budget = Budget.from_dict(data)

    app = BudgetPlannerApp()
    app.current_user = MockUser(temp_user_dir)
    app.current_user.load_budget()

    start_date = app.current_user.budget.start_date
    end_date = app.current_user.budget.end_date

    app._setup_holidays_and_recalculate(start_date, end_date)
    app._generate_report(start_date, end_date)

    generated_file = temp_user_dir / 'budget_plan.csv'
    expected_file = test_case_dir / "report.csv"  # Get the correct expected report

    assert generated_file.exists(), "Report file was not generated."

    generated_data = _read_csv_to_list_of_dicts(generated_file)
    expected_data = _read_csv_to_list_of_dicts(expected_file)

    assert set(generated_data[0].keys()) == set(expected_data[0].keys()), "CSV headers don’t match"

    assert generated_data == expected_data
    print(f"...OK: {test_case_dir.name}")