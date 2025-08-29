import pytest
import json
import os
import shutil
from pathlib import Path

# Define key paths
PROJECT_ROOT = Path(__file__).parent.parent
TEST_DATA_DIR = Path(__file__).parent / "test_data"


@pytest.fixture(scope="session")
def holidays():
    """A session-scoped fixture to load all holiday files once."""
    holiday_files = [
        PROJECT_ROOT / 'holidays_2025.txt',
        PROJECT_ROOT / 'holidays_2026.txt',
        PROJECT_ROOT / 'holidays_2027.txt'
    ]
    from main import load_holidays
    return load_holidays(holiday_files)


@pytest.fixture
def budget_data():
    """Fixture to load the test budget JSON data from the tests/test_data folder."""
    with open(TEST_DATA_DIR / 'test_budget.json', 'r') as f:
        return json.load(f)


@pytest.fixture
def e2e_test_environment():
    """
    Sets up a temporary user directory for the E2E test, copies
    the test data and holiday files, and cleans up afterward.
    """
    test_user_dir = PROJECT_ROOT / "test_user_temp"
    if test_user_dir.exists():
        shutil.rmtree(test_user_dir)
    test_user_dir.mkdir()

    # Copy the test budget data
    shutil.copy(TEST_DATA_DIR / 'test_budget.json', test_user_dir / 'my_budget_data.json')

    # Copy holiday files into a subdirectory within the temp environment
    holidays_dir = test_user_dir / 'holidays'
    holidays_dir.mkdir()
    for year in [2025, 2026, 2027]:
        shutil.copy(PROJECT_ROOT / f'holidays_{year}.txt', holidays_dir / f'holidays_{year}.txt')

    yield test_user_dir

    shutil.rmtree(test_user_dir)