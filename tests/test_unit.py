from datetime import date
from pytest import approx

# Import the classes and functions from your main script
from main import (
    Budget,
    Income,
    ProRatedIncome,
    calculate_twice_monthly_dates
)


# --- This test is unaffected and remains the same ---
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


# --- THIS IS THE UPDATED TEST ---
def test_budget_loading_from_dict(budget_data):
    """
    Tests the Budget.from_dict method using our new, verified 'budget_data'.
    """
    print("\nRunning: Unit Test for loading budget from dictionary...")
    budget = Budget.from_dict(budget_data)

    # Assertions are now updated to match the new test case
    assert budget.income is not None
    assert len(budget.expenses) == 2  # Groceries + Phone Bill
    assert len(budget.savings_transfers) == 1
    assert budget.initial_debit_balance == 100.0  # <-- Changed from 500.0
    assert budget.income.amount == 1000.0  # <-- Changed from 2134.0
    assert budget.savings_accounts[0].name == "Emergency Fund"  # <-- Changed from "House"
    assert budget.savings_accounts[0].balance == 500.0  # <-- Changed from 4200.0
    print("...OK")


# --- This test is also unaffected and remains the same ---
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


def test_one_time_income_dates_preserved_without_start(apply_holidays_fixture=None):
    from main import Budget, Income
    b = Budget(
        start_date=date(2025, 10, 6),
        end_date=date(2025, 10, 7),
        initial_debit_balance=0.0
    )
    one_time_date = date(2025, 10, 6)
    b.income = Income(name="Primary Income", amount=100.0, frequency="one-time",
                      dates=[one_time_date], start_date_for_schedule=None)
    b.recalculate_schedules(b.end_date, holidays=[])  # or your holiday list
    assert b.income.dates == [one_time_date]