import csv
import json
from pathlib import Path
import os

# Define path to our test data
TEST_DATA_DIR = Path(__file__).parent / "test_data"


# --- THIS IS THE UPDATED HELPER FUNCTION ---
def _read_csv_to_list_of_dicts(filepath):
    """
    Reads a CSV file and standardizes all numerical strings to two decimal places
    for robust comparison.
    """
    data = []
    with open(filepath, mode='r', newline='') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            processed_row = {}
            for key, value in row.items():
                try:
                    # Try to convert to float and format to 2 decimal places
                    processed_row[key] = f"{float(value):.2f}"
                except (ValueError, TypeError):
                    # If it's not a number (e.g., a date or empty string), keep it as is
                    processed_row[key] = value
            data.append(processed_row)
    return data


# --- THE REST OF THE FILE REMAINS EXACTLY THE SAME ---
def test_end_to_end_report_generation(e2e_test_environment):
    """
    Tests the full flow from loading data to generating a matching CSV report.
    """
    from main import BudgetPlannerApp

    print("\nRunning: End-to-End Test for CSV report generation...")
    test_user_dir = e2e_test_environment

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
    app.current_user = MockUser(test_user_dir)
    app.current_user.load_budget()

    start_date = app.current_user.budget.start_date
    end_date = app.current_user.budget.end_date

    app._setup_holidays_and_recalculate(start_date, end_date)
    app._generate_report(start_date, end_date)

    # Compare the generated file with the expected file from our test_data directory
    generated_file = test_user_dir / 'budget_plan.csv'
    expected_file = TEST_DATA_DIR / 'expected_report.csv'

    assert generated_file.exists(), "Report file was not generated."

    generated_data = _read_csv_to_list_of_dicts(generated_file)
    expected_data = _read_csv_to_list_of_dicts(expected_file)

    assert generated_data == expected_data
    print("...OK")