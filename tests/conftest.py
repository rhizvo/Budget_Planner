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
    holiday_files = [
        PROJECT_ROOT / 'holidays_2025.txt',
        PROJECT_ROOT / 'holidays_2026.txt',
        PROJECT_ROOT / 'holidays_2027.txt'
    ]
    from main import load_holidays
    return load_holidays(holiday_files)


@pytest.fixture
def budget_data():
    """Fixture for unit tests. Now points to a stable 'happy_path' case."""
    with open(TEST_DATA_DIR / '00_happy_path' / 'budget.json', 'r') as f:
        return json.load(f)


@pytest.fixture
def e2e_test_environment():
    test_user_dir = PROJECT_ROOT / "test_user_temp"
    if test_user_dir.exists():
        shutil.rmtree(test_user_dir)
    test_user_dir.mkdir()

    holidays_dir = test_user_dir / 'holidays'
    holidays_dir.mkdir()
    for year in [2025, 2026, 2027]:
        shutil.copy(PROJECT_ROOT / f'holidays_{year}.txt', holidays_dir / f'holidays_{year}.txt')

    yield test_user_dir

    shutil.rmtree(test_user_dir)