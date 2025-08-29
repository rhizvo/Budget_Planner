from datetime import date
from pytest import approx

# Import the classes and functions from your main script
from main import (
    Budget,
    Income,
    ProRatedIncome,
    calculate_twice_monthly_dates
)


# --- TEST 1: Test a core date calculation function ---
def test_calculate_twice_monthly_dates(holidays):
    """
    Tests the twice-monthly date calculation using the 'holidays' fixture.
    """
    print("\nRunning: Unit Test for twice-monthly date calculation...")
    start = date(2026, 4, 1)
    end = date(2026, 7, 16)

    expected_dates = [
        date(2026, 4, 15), date(2026, 4, 30),
        date(2026, 5, 15), date(2026, 5, 29),
        date(2026, 6, 15), date(2026, 6, 30),
        date(2026, 7, 15)
    ]

    actual_dates = calculate_twice_monthly_dates(start, end, holidays)

    assert actual_dates == expected_dates
    print("...OK")


# --- TEST 2: Test that the Budget class loads from JSON correctly ---
def test_budget_loading_from_dict(budget_data):
    """
    Tests the Budget.from_dict method using the 'budget_data' fixture.
    """
    print("\nRunning: Unit Test for loading budget from dictionary...")
    budget = Budget.from_dict(budget_data)

    assert budget.income is not None
    assert len(budget.expenses) == 2  # Groceries + Hydro
    assert len(budget.savings_transfers) == 1
    assert budget.initial_debit_balance == 500.0
    assert budget.income.amount == 2134.0
    assert budget.savings_accounts[0].name == "House"
    assert budget.savings_accounts[0].balance == 4200.0
    print("...OK")


# --- TEST 3: Test the pro-rated final paycheck logic ---
def test_pro_rated_final_paycheck(holidays):
    """
    Tests the special case of creating a pro-rated final paycheck.
    """
    print("\nRunning: Unit Test for pro-rated income calculation...")
    budget = Budget(start_date=date(2026, 1, 1), end_date=date(2026, 3, 31))

    budget.income = Income(
        amount=2000.0,
        frequency='twice-monthly',
        start_date_for_schedule=date(2026, 1, 15),
        expiry_date=date(2026, 1, 20)  # Expires 5 days after Jan 15 payday
    )

    budget.recalculate_schedules(budget.end_date, holidays)

    final_pay_expense = next((exp for exp in budget.expenses if isinstance(exp, ProRatedIncome)), None)

    assert final_pay_expense is not None, "Final pro-rated paycheck was not created."

    expected_amount = -((2000.0 / (31 / 2.0)) * 5)

    assert final_pay_expense.name == "Final Pro-rated Paycheck"
    assert final_pay_expense.dates[0] == date(2026, 1, 20)
    assert final_pay_expense.amount == approx(expected_amount, 0.01)
    print("...OK")