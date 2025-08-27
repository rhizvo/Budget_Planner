import csv
from datetime import datetime, timedelta
from collections import defaultdict
import calendar
import os
import json
import shutil
import copy


# --- Helper Functions (Remain largely unchanged) ---

def get_date_input(prompt, start_after=None):
    """Helper function to get a valid date input, with optional validation."""
    while True:
        date_str = input(prompt + " (YYYY-MM-DD): ")
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            if start_after and date_obj <= start_after:
                print(f"Error: The date must be after {start_after.strftime('%Y-%m-%d')}.")
                continue
            return date_obj
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")


def get_float_input(prompt):
    """Helper function to get a valid float input."""
    while True:
        try:
            value = input(prompt + ": ")
            if value == '':
                return None
            float_value = float(value)
            if float_value < 0:
                print("Please enter a non-negative number.")
                continue
            return float_value
        except ValueError:
            print("Invalid input. Please enter a number.")


def get_frequency_input(prompt, extra_options=None):
    """Helper function to get a valid frequency input, with optional extra choices."""
    valid_options = ["weekly", "bi-weekly", "monthly", "bi-monthly", "quarterly", "yearly", "one-time"]
    prompt_options = "(weekly, bi-weekly, monthly, bi-monthly, quarterly, yearly, one-time"

    if extra_options:
        valid_options.extend(extra_options)
        prompt_options += ", " + ", ".join(extra_options)
    prompt_options += "): "

    while True:
        freq = input(prompt + prompt_options).lower()
        if freq == '':
            return None
        if freq in valid_options:
            return freq
        else:
            print("Invalid frequency. Please choose from the available options.")


def get_multiple_dates(prompt):
    """Helper function to get multiple dates."""
    dates = []
    while True:
        date_str = input(prompt + " (YYYY-MM-DD) or 'done' to finish: ").lower()
        if date_str == 'done':
            break
        try:
            dates.append(datetime.strptime(date_str, "%Y-%m-%d").date())
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")
    return dates


def get_yes_no_input(prompt):
    """Helper function to get a yes/no answer."""
    while True:
        response = input(prompt + " (yes/no): ").lower()
        if response in ["yes", "y"]:
            return True
        elif response in ["no", "n"]:
            return False
        else:
            print("Invalid input. Please enter 'yes' or 'no'.")


def get_savings_target_input(prompt, existing_targets):
    """Helper function to get a valid savings target name."""
    if not existing_targets:
        print("You must first create a savings account before adding a transfer schedule.")
        return None
    while True:
        print("Available savings targets:")
        for i, target in enumerate(existing_targets):
            print(f"  {i + 1}. {target.name}")
        choice = input(prompt + " (Enter the number or name): ")
        try:
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(existing_targets):
                return existing_targets[choice_idx].name
            else:
                print("Invalid number.")
        except ValueError:
            if any(t.name == choice for t in existing_targets):
                return choice
            else:
                print(f"'{choice}' is not a valid savings target.")


def load_holidays(filepaths):
    """Loads holidays from a list of TXT files into a set of date objects."""
    holidays_set = set()
    for filepath in filepaths:
        if not os.path.exists(filepath):
            print(f"Warning: Holiday file not found at '{filepath}'. Skipping.")
            continue
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    parts = line.strip().split(',')
                    if len(parts) == 2:
                        try:
                            holiday_date = datetime.strptime(parts[1].strip(), "%Y-%m-%d").date()
                            holidays_set.add(holiday_date)
                        except ValueError:
                            print(f"Warning: Could not parse holiday date '{parts[1].strip()}' in line: {line.strip()}")
                    else:
                        print(f"Warning: Skipping malformed holiday line: {line.strip()}")
        except Exception as e:
            print(f"Error reading holiday file '{filepath}': {e}")
    return holidays_set


def is_business_day(date, holidays_set):
    """Checks if a given date is a business day (Mon-Fri and not a holiday)."""
    if date.weekday() >= 5:
        return False
    if date in holidays_set:
        return False
    return True


def calculate_twice_monthly_dates(start_date, end_date, holidays_set):
    """
    Generates 15th and last-day-of-month dates between start_date and end_date,
    adjusting to the closest business day *before* if it falls on a weekend or holiday.
    """
    dates = []
    current_iter_date = start_date

    while current_iter_date <= end_date:
        year = current_iter_date.year
        month = current_iter_date.month

        target_15th = datetime(year, month, 15).date()
        if start_date <= target_15th <= end_date:
            adjusted_date = target_15th
            while not is_business_day(adjusted_date, holidays_set):
                adjusted_date -= timedelta(days=1)
            if adjusted_date >= start_date:
                dates.append(adjusted_date)

        last_day_of_month_num = calendar.monthrange(year, month)[1]
        target_last_day = datetime(year, month, last_day_of_month_num).date()
        if start_date <= target_last_day <= end_date:
            adjusted_date = target_last_day
            while not is_business_day(adjusted_date, holidays_set):
                adjusted_date -= timedelta(days=1)
            if adjusted_date >= start_date:
                dates.append(adjusted_date)

        if month == 12:
            current_iter_date = datetime(year + 1, 1, 1).date()
        else:
            current_iter_date = datetime(year, month + 1, 1).date()

    dates = sorted(list(set(dates)))
    return [d for d in dates if d >= datetime.now().date()]


def calculate_bi_monthly_dates_every_two_months(start_date, end_date, holidays_set, adjust_for_holidays=True):
    """
    Generates a list of recurring dates every two months.
    Date adjustment for weekends/holidays is now conditional.
    """
    dates = []
    current_date = start_date

    while current_date <= end_date:
        adjusted_date = current_date
        # --- MODIFIED LOGIC ---
        if adjust_for_holidays:
            while not is_business_day(adjusted_date, holidays_set):
                adjusted_date -= timedelta(days=1)
        dates.append(adjusted_date)

        new_month = current_date.month + 2
        new_year = current_date.year
        if new_month > 12:
            new_month -= 12
            new_year += 1
        day = min(current_date.day, calendar.monthrange(new_year, new_month)[1])
        current_date = datetime(new_year, new_month, day).date()

    return [d for d in dates if d >= datetime.now().date()]


def get_recurring_dates(start_date, end_date, frequency, holidays_set=None, adjust_for_holidays=False):
    """
    Generates a list of recurring dates based on frequency.
    Date adjustment for weekends/holidays is now conditional.
    """
    dates = []
    current_date = start_date
    holidays_set = holidays_set if holidays_set is not None else set()

    while current_date <= end_date:
        adjusted_date = current_date
        # --- MODIFIED LOGIC ---
        # Only adjust the date if the flag is True
        if adjust_for_holidays:
            while not is_business_day(adjusted_date, holidays_set):
                adjusted_date -= timedelta(days=1)

        if adjusted_date >= datetime.now().date():
            dates.append(adjusted_date)

        # Calculation for the next date remains the same
        if frequency == 'weekly':
            current_date += timedelta(weeks=1)
        elif frequency == 'bi-weekly':
            current_date += timedelta(weeks=2)
        elif frequency == 'monthly':
            new_month = current_date.month + 1
            new_year = current_date.year
            if new_month > 12:
                new_month = 1
                new_year += 1
            day = min(start_date.day, calendar.monthrange(new_year, new_month)[1])
            current_date = datetime(new_year, new_month, day).date()
        elif frequency == 'bi-monthly':
            new_month = current_date.month + 2
            new_year = current_date.year
            if new_month > 12:
                new_month -= 12
                new_year += 1
            day = min(start_date.day, calendar.monthrange(new_year, new_month)[1])
            current_date = datetime(new_year, new_month, day).date()
        elif frequency == 'quarterly':
            new_month = current_date.month + 3
            new_year = current_date.year
            if new_month > 12:
                new_month -= 12
                new_year += 1
            day = min(start_date.day, calendar.monthrange(new_year, new_month)[1])
            current_date = datetime(new_year, new_month, day).date()
        elif frequency == 'yearly':
            current_date = datetime(current_date.year + 1, start_date.month, start_date.day).date()
        else:
            break

    return sorted(list(set(dates)))


# --- NEW: OOP Class Definitions ---

class FinancialItem:
    """Base class for any item with a name, amount, and schedule."""

    def __init__(self, name, amount, frequency, dates=None, start_date_for_schedule=None):
        self.name = name
        self.amount = amount
        self.frequency = frequency
        self.dates = dates if dates is not None else []
        self.start_date_for_schedule = start_date_for_schedule

    def to_dict(self):
        data = {
            'name': self.name,
            'amount': self.amount,
            'frequency': self.frequency,
            'dates': [d.isoformat() for d in self.dates],
        }
        if self.start_date_for_schedule:
            data['start_date_for_schedule'] = self.start_date_for_schedule.isoformat()
        return data

    @classmethod
    def from_dict(cls, data):
        # Create a mutable copy to avoid altering the original dictionary
        init_data = data.copy()

        # Deserialize dates
        init_data['dates'] = [datetime.fromisoformat(d).date() for d in init_data.get('dates', [])]
        if init_data.get('start_date_for_schedule'):
            init_data['start_date_for_schedule'] = datetime.fromisoformat(init_data['start_date_for_schedule']).date()

        # Remove keys that are not part of the constructor for this specific class
        # This makes the from_dict more robust for subclasses
        if 'category' in init_data:
            del init_data['category']
        if 'expiry_date' in init_data:
            del init_data['expiry_date']
        if 'target' in init_data:
            del init_data['target']

        return cls(**init_data)


class Expense(FinancialItem):
    """Represents an expense, inheriting from FinancialItem."""

    def __init__(self, name, amount, frequency, category, dates=None, start_date_for_schedule=None, expiry_date=None):
        super().__init__(name, amount, frequency, dates, start_date_for_schedule)
        self.category = category
        self.expiry_date = expiry_date

    def to_dict(self):
        data = super().to_dict()
        data.update({
            'category': self.category,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None
        })
        return data

    @classmethod
    def from_dict(cls, data):
        init_data = data.copy()
        init_data['dates'] = [datetime.fromisoformat(d).date() for d in init_data.get('dates', [])]
        if init_data.get('start_date_for_schedule'):
            init_data['start_date_for_schedule'] = datetime.fromisoformat(init_data['start_date_for_schedule']).date()
        if init_data.get('expiry_date'):
            init_data['expiry_date'] = datetime.fromisoformat(init_data['expiry_date']).date()

        # For direct instantiation of Expense, remove subclass-specific keys
        if 'target' in init_data:
            del init_data['target']

        return cls(**init_data)


class Bill(Expense):
    """Represents a bill, a specific type of Expense."""

    def __init__(self, **kwargs):
        kwargs['category'] = 'Bills'
        super().__init__(**kwargs)


class StreamingService(Expense):
    """Represents a streaming service, a specific type of Expense."""

    def __init__(self, **kwargs):
        kwargs['category'] = 'Streaming Services'
        super().__init__(**kwargs)


class Income(FinancialItem):
    """Represents an income source, now with an optional expiry date."""

    def __init__(self, name="Primary Income", amount=0.0, frequency=None, dates=None, start_date_for_schedule=None,
                 expiry_date=None):
        super().__init__(name, amount, frequency, dates, start_date_for_schedule)
        self.expiry_date = expiry_date

    def to_dict(self):
        data = super().to_dict()
        data['expiry_date'] = self.expiry_date.isoformat() if self.expiry_date else None
        return data

    @classmethod
    def from_dict(cls, data):
        init_data = data.copy()
        init_data['dates'] = [datetime.fromisoformat(d).date() for d in init_data.get('dates', [])]
        if init_data.get('start_date_for_schedule'):
            init_data['start_date_for_schedule'] = datetime.fromisoformat(init_data['start_date_for_schedule']).date()
        if init_data.get('expiry_date'):
            init_data['expiry_date'] = datetime.fromisoformat(init_data['expiry_date']).date()

        # Clean up keys not in the constructor
        if 'category' in init_data: del init_data['category']
        if 'target' in init_data: del init_data['target']

        return cls(**init_data)


class SavingsTransfer(FinancialItem):
    """Represents a transfer to a savings account."""

    def __init__(self, name, amount, frequency, target, dates=None, start_date_for_schedule=None):
        super().__init__(name, amount, frequency, dates, start_date_for_schedule)
        self.target = target

    def to_dict(self):
        data = super().to_dict()
        data['target'] = self.target
        return data

    @classmethod
    def from_dict(cls, data):
        init_data = data.copy()
        init_data['dates'] = [datetime.fromisoformat(d).date() for d in init_data.get('dates', [])]
        if init_data.get('start_date_for_schedule'):
            init_data['start_date_for_schedule'] = datetime.fromisoformat(init_data['start_date_for_schedule']).date()

        if 'category' in init_data:
            del init_data['category']
        if 'expiry_date' in init_data:
            del init_data['expiry_date']

        return cls(**init_data)


class SavingsAccount:
    """Represents a savings account with a name and balance."""

    def __init__(self, name, balance=0.0):
        self.name = name
        self.balance = balance

    def to_dict(self):
        return {'name': self.name, 'balance': self.balance}

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


class Budget:
    """Container for all financial data for a user."""

    def __init__(self, start_date=None, end_date=None, initial_debit_balance=0.0):
        self.start_date = start_date
        self.end_date = end_date
        self.initial_debit_balance = initial_debit_balance
        self.savings_accounts = []
        self.income = None
        self.expenses = []
        self.savings_transfers = []

    def to_dict(self):
        return {
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'initial_debit_balance': self.initial_debit_balance,
            'savings_balances': {sa.name: sa.balance for sa in self.savings_accounts},
            'income': self.income.to_dict() if self.income else {},
            'expense_categories': self._expenses_to_dict(),
            'savings_transfers': [st.to_dict() for st in self.savings_transfers]
        }

    def _expenses_to_dict(self):
        exp_dict = defaultdict(list)
        for exp in self.expenses:
            exp_dict[exp.category].append(exp.to_dict())
        return exp_dict

    @classmethod
    def from_dict(cls, data):
        start = datetime.fromisoformat(data['start_date']).date() if data.get('start_date') else None
        end = datetime.fromisoformat(data['end_date']).date() if data.get('end_date') else None
        budget = cls(start, end, data.get('initial_debit_balance', 0.0))

        for name, balance in data.get('savings_balances', {}).items():
            budget.savings_accounts.append(SavingsAccount(name, balance))

        if data.get('income') and data['income'].get('amount'):
            budget.income = Income.from_dict(data['income'])

        for category, items in data.get('expense_categories', {}).items():
            for item_data in items:
                if category == 'Bills':
                    budget.expenses.append(Bill.from_dict(item_data))
                elif category == 'Streaming Services':
                    budget.expenses.append(StreamingService.from_dict(item_data))
                else:
                    budget.expenses.append(Expense.from_dict(item_data))

        for transfer_data in data.get('savings_transfers', []):
            budget.savings_transfers.append(SavingsTransfer.from_dict(transfer_data))

        return budget

    def recalculate_schedules(self, start_date, end_date, holidays):
        """Recalculates all recurring dates based on the new budget period."""
        print("\nRecalculating all schedules for the new budget period...")

        if self.income:
            income_freq = self.income.frequency

            # Case 1: Twice-monthly frequency
            if income_freq == 'twice-monthly' and self.income.start_date_for_schedule:
                # Use the user-provided start date for calculation
                calc_start_date = self.income.start_date_for_schedule
                self.income.dates = calculate_twice_monthly_dates(calc_start_date, end_date, holidays)

            # Case 2: All other frequencies that rely on a saved start date
            elif self.income.start_date_for_schedule:
                original_start = self.income.start_date_for_schedule

                if income_freq == 'bi-monthly':
                    self.income.dates = calculate_bi_monthly_dates_every_two_months(
                        original_start, end_date, holidays, adjust_for_holidays=True)
                elif income_freq not in ['one-time', 'manual']:
                    self.income.dates = get_recurring_dates(
                        original_start, end_date, income_freq, holidays, adjust_for_holidays=True)
            else:
                self.income.dates = []

            # --- NEW LOGIC ---
            # After calculating dates, filter them by the income's expiry date if it exists.
            if self.income.expiry_date:
                self.income.dates = [d for d in self.income.dates if d <= self.income.expiry_date]

        # Recalculate Expenses & Savings (This logic remains correct)
        items_to_recalculate = self.expenses + self.savings_transfers
        for item in items_to_recalculate:
            freq = item.frequency

            should_adjust = (isinstance(item, SavingsTransfer) and item.frequency == 'match payday')

            if freq == 'match payday' and self.income:
                item.dates = self.income.dates
            elif item.start_date_for_schedule:
                original_start = item.start_date_for_schedule
                if freq == 'bi-monthly':
                    item.dates = calculate_bi_monthly_dates_every_two_months(original_start, end_date, holidays,
                                                                             adjust_for_holidays=should_adjust)
                elif freq not in ['one-time', 'manual']:
                    item.dates = get_recurring_dates(original_start, end_date, freq, holidays,
                                                     adjust_for_holidays=should_adjust)

            if hasattr(item, 'expiry_date') and item.expiry_date:
                item.dates = [d for d in item.dates if d <= item.expiry_date]

        print("Schedules recalculated.")

class User:
    """Manages user data, including loading and saving their budget."""

    def __init__(self, username):
        self.username = username
        self.directory = username
        self.budget_filepath = os.path.join(self.directory, "my_budget_data.json")
        self.budget = None

    def load_budget(self):
        """Loads the budget from the user's JSON file."""
        if not os.path.exists(self.budget_filepath):
            print(f"No existing budget file found for {self.username}. Starting a new budget setup.")
            self.budget = Budget()
            return

        with open(self.budget_filepath, 'r') as f:
            try:
                data = json.load(f)
                self.budget = Budget.from_dict(data)
                print(f"Budget configuration loaded for {self.username}.")
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                print(f"Error reading or parsing budget file for {self.username}: {e}. Starting fresh.")
                self.budget = Budget()

    def save_budget(self):
        """Saves the user's budget to their JSON file."""
        if self.budget:
            with open(self.budget_filepath, 'w') as f:
                json.dump(self.budget.to_dict(), f, indent=4)
            print(f"\nBudget configuration saved for {self.username}.")

    def setup_directories(self):
        """Ensures the user's main directory and holidays subdirectory exist."""
        os.makedirs(self.directory, exist_ok=True)
        os.makedirs(os.path.join(self.directory, 'holidays'), exist_ok=True)


class BudgetPlannerApp:
    """The main application class that orchestrates the user interface and logic."""

    def __init__(self):
        self.current_user = None
        self.holidays = set()

    def run(self):
        """Starts the main application loop."""
        print("--- Welcome to the Budget Planner ---")
        while True:
            print("\n[1] Sign In")
            print("[2] Sign Up")
            print("[3] Delete Account")
            print("[4] Exit")
            choice = input("Please select an option: ")

            if choice == '1':
                self._handle_sign_in()
            elif choice == '2':
                self._handle_sign_up()
            elif choice == '3':
                self._handle_delete_account()
            elif choice == '4':
                print("Goodbye!")
                break
            else:
                print("Invalid choice. Please enter 1, 2, 3, or 4.")

            if not get_yes_no_input("\nDo you want to return to the main user menu? (yes=return, no=exit)"):
                print("Goodbye!")
                break

    def _handle_sign_in(self):
        users = [d for d in os.listdir() if os.path.isdir(d) and not d.startswith('.')]
        if not users:
            print("No user accounts found. Please sign up first.")
            return
        print("Existing Users:", ", ".join(users))
        username = input("Enter your username: ").lower()
        if not username.strip():
            print("Username cannot be empty.")
            return
        if os.path.isdir(username):
            print(f"Welcome back, {username}!")
            self.current_user = User(username)
            self.current_user.load_budget()
            self._run_user_session()
        else:
            print(f"Error: No account found for username '{username}'. Please sign up.")

    def _handle_sign_up(self):
        username = input("Enter your new username: ").lower()
        if not username.strip():
            print("Username cannot be empty.")
            return
        if os.path.isdir(username):
            print(f"Error: Username '{username}' already exists. Please sign in.")
            return

        try:
            self.current_user = User(username)
            self.current_user.setup_directories()
            print(f"Account '{username}' created successfully!")
            self.current_user.load_budget()
            self._run_user_session()
        except OSError as e:
            print(f"Error creating directory for user '{username}': {e}")

    def _handle_delete_account(self):
        users = [d for d in os.listdir() if os.path.isdir(d) and not d.startswith('.')]
        if not users:
            print("No user accounts found to delete.")
            return
        print("Existing Users:", ", ".join(users))
        username = input("Enter the username of the account to delete: ").lower()
        if username in users:
            if get_yes_no_input(
                    f"Are you sure you want to permanently delete the account for '{username}'? This cannot be undone."):
                try:
                    shutil.rmtree(username)
                    print(f"Account '{username}' has been deleted.")
                except OSError as e:
                    print(f"Error deleting account: {e}")
        else:
            print(f"Error: No account found for username '{username}'.")

    def _run_user_session(self):
        """Handles the main menu and actions for a logged-in user."""
        if not self.current_user or not self.current_user.budget:
            return

        start_date, end_date, _ = self._manage_budget_period()
        self._setup_holidays_and_recalculate(start_date, end_date)

        while True:
            print("\n--- Main Menu ---")
            print(f"User: {self.current_user.username}")
            print(f"Budget Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            print("1. Guided Budget Setup")
            print("2. Manage Specific Categories")
            print("3. Generate Budget Report and Save")
            print("4. Exit to User Selection")

            choice = input("Select an option: ")

            if choice == '1':
                self._run_guided_setup(start_date, end_date)
            elif choice == '2':
                new_start, new_end, period_changed = self._manage_categories_menu(start_date, end_date)
                if period_changed:
                    start_date, end_date = new_start, new_end
                    self._setup_holidays_and_recalculate(start_date, end_date)
            elif choice == '3':
                self._generate_report(start_date, end_date)
                self.current_user.save_budget()
            elif choice == '4':
                if get_yes_no_input("Do you want to save any changes before exiting?"):
                    self.current_user.save_budget()
                print(f"Exiting session for {self.current_user.username}.")
                break
            else:
                print("Invalid choice. Please select a valid option.")

    def _manage_budget_period(self):
        """Gets or updates the budget start and end dates."""
        print("\n--- Manage Budget Period ---")

        start_date = self.current_user.budget.start_date
        end_date = self.current_user.budget.end_date
        period_changed = False

        if start_date and end_date:
            print(
                f"Current budget period is from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}.")
            if not get_yes_no_input("Do you want to change it?"):
                return start_date, end_date, period_changed

        print("Please define your budget period.")
        while True:
            new_start_date = get_date_input("Enter the budget start date")
            new_end_date = get_date_input("Enter the budget end date", start_after=new_start_date)
            if new_end_date > new_start_date:
                if new_start_date != start_date or new_end_date != end_date:
                    period_changed = True
                self.current_user.budget.start_date = new_start_date
                self.current_user.budget.end_date = new_end_date
                print("Budget period updated.")
                return new_start_date, new_end_date, period_changed
            else:
                print("Error: The end date must be after the start date. Please try again.")

    def _setup_holidays_and_recalculate(self, start_date, end_date):
        """Handles holiday file setup and recalculates all schedules."""
        print("\n--- Holiday Information ---")
        required_years = range(start_date.year, end_date.year + 1)
        holiday_files_to_load = []
        holidays_folder = os.path.join(self.current_user.directory, 'holidays')

        for year in required_years:
            user_holiday_path = os.path.join(holidays_folder, f"holidays_{year}.txt")
            holiday_files_to_load.append(user_holiday_path)
            if not os.path.exists(user_holiday_path):
                print(f"Holiday file for {year} is missing.")
                while True:
                    source_holiday_file = input(
                        f"Enter the path to a source holiday file for {year} (e.g., holidays.txt): ")
                    if os.path.exists(source_holiday_file):
                        try:
                            shutil.copy(source_holiday_file, user_holiday_path)
                            print(f"Holiday file for {year} copied to your user folder.")
                            break
                        except Exception as e:
                            print(f"Error copying file: {e}")
                            if not get_yes_no_input("Try a different file path?"): break
                    else:
                        print(f"File not found at '{source_holiday_file}'.")
                        if not get_yes_no_input("Try again?"): break

        self.holidays = load_holidays(holiday_files_to_load)
        if self.holidays:
            print(f"Loaded {len(self.holidays)} holidays across {len(required_years)} year(s).")

        self.current_user.budget.recalculate_schedules(start_date, end_date, self.holidays)

    def _manage_categories_menu(self, start_date, end_date):
        """Shows a menu to manage specific budget categories."""
        period_changed = False
        while True:
            print("\n--- Manage Specific Categories ---")
            print("1. Initial Debit & Savings Balances")
            print("2. Income")
            print("3. Groceries")
            print("4. Bills")
            print("5. Streaming Services")
            print("6. Miscellaneous Monthly Expenses")
            print("7. One-Time Expenses")
            print("8. Savings Transfer Schedules")
            print("9. Manage Budget Period (Start/End Dates)")
            print("10. Return to Previous Menu")

            choice = input("Enter your choice (1-10): ")

            if choice == '1':
                self._manage_balances()
            elif choice == '2':
                self._manage_income(start_date, end_date)
            elif choice == '3':
                self._manage_groceries(start_date, end_date)
            elif choice == '4':
                self._manage_expense_category("Bills", Bill, start_date, end_date)
            elif choice == '5':
                self._manage_expense_category("Streaming Services", StreamingService, start_date, end_date)
            elif choice == '6':
                self._manage_expense_category("Misc Monthly", Expense, start_date, end_date)
            elif choice == '7':
                self._manage_one_time()
            elif choice == '8':
                self._manage_savings_transfers(start_date, end_date)
            elif choice == '9':
                new_start, new_end, changed = self._manage_budget_period()
                if changed:
                    start_date, end_date = new_start, new_end
                    period_changed = True
            elif choice == '10':
                print("Returning to the previous menu.")
                break
            else:
                print("Invalid choice. Please enter a number between 1 and 10.")
        return start_date, end_date, period_changed

    def _generate_report(self, start_date, end_date):
        """Calculates the budget and writes the final CSV report."""
        print("\n--- Generating Budget Report ---")

        output_filename = os.path.join(self.current_user.directory, "budget_plan.csv")

        report_budget = copy.deepcopy(self.current_user.budget)
        report_budget.recalculate_schedules(start_date, end_date, self.holidays)

        all_expenses_to_process = report_budget.expenses
        all_savings_to_process = report_budget.savings_transfers
        all_income_paydates = report_budget.income.dates if report_budget.income else []

        start_of_first_week = start_date - timedelta(days=start_date.weekday())
        weeks = []
        current_week_start = start_of_first_week
        while current_week_start <= end_date:
            weeks.append(current_week_start)
            current_week_start += timedelta(weeks=1)

        financial_data = []
        cumulative_savings_by_target = defaultdict(float)
        for acc in report_budget.savings_accounts:
            cumulative_savings_by_target[acc.name] = acc.balance

        running_balance = report_budget.initial_debit_balance

        for week_start in weeks:
            week_end = week_start + timedelta(days=6)
            week_of_year = week_start.isocalendar()[1]

            weekly_income = 0.0
            weekly_expenses_breakdown = defaultdict(float)
            weekly_total_expenses = 0.0
            weekly_total_savings = 0.0
            weekly_savings_by_target = defaultdict(float)

            if report_budget.income:
                for pay_date in all_income_paydates:
                    if week_start <= pay_date <= week_end:
                        weekly_income += report_budget.income.amount

            for item in all_expenses_to_process:
                should_apply_expense_this_week = False
                if item.expiry_date and week_start > item.expiry_date:
                    continue

                # --- MODIFIED LOGIC ---
                # Removed the special case for 'weekly'. All frequencies now rely on the 'dates' list.
                if item.dates:
                    for expense_date in item.dates:
                        if week_start <= expense_date <= week_end:
                            should_apply_expense_this_week = True
                            break

                if should_apply_expense_this_week:
                    key_name = f"{item.category}: {item.name}"
                    weekly_expenses_breakdown[key_name] += item.amount
                    weekly_total_expenses += item.amount

            for s_transfer in all_savings_to_process:
                should_apply_savings_this_week = False
                # We can remove the 'weekly' special case here too for consistency, though it had no effect
                if s_transfer.dates:
                    for s_date in s_transfer.dates:
                        if week_start <= s_date <= week_end:
                            should_apply_savings_this_week = True
                            break
                if should_apply_savings_this_week:
                    weekly_savings_by_target[s_transfer.target] += s_transfer.amount
                    weekly_total_savings += s_transfer.amount

            running_balance += weekly_income - weekly_total_expenses - weekly_total_savings
            for target, amount in weekly_savings_by_target.items():
                cumulative_savings_by_target[target] += amount

            week_data_row = {
                'Week of Year': week_of_year,
                'Week Start Date': week_start.strftime("%Y-%m-%d"),
                'Week End Date': week_end.strftime("%Y-%m-%d"),
                'Income Received': weekly_income,
                'Total Weekly Expenses': weekly_total_expenses,
                'Total Savings Transferred': weekly_total_savings,
                'Running Balance at End of Week': running_balance,
                **weekly_expenses_breakdown
            }
            for target, amount in weekly_savings_by_target.items():
                week_data_row[f'Savings Transferred ({target})'] = amount
            for target, cumulative_amount in cumulative_savings_by_target.items():
                week_data_row[f'Saved Amount at End of Week ({target})'] = cumulative_amount
            financial_data.append(week_data_row)

        if financial_data:
            all_keys = set()
            for row in financial_data:
                all_keys.update(row.keys())

            ordered_keys_initial = [
                'Week of Year', 'Week Start Date', 'Week End Date', 'Income Received',
                'Total Weekly Expenses', 'Total Savings Transferred', 'Running Balance at End of Week'
            ]
            savings_keys = sorted([k for k in all_keys if 'Saved Amount' in k or 'Savings Transferred' in k])
            expense_keys = sorted([k for k in all_keys if k not in ordered_keys_initial and k not in savings_keys])
            final_keys = ordered_keys_initial + savings_keys + expense_keys

            with open(output_filename, 'w', newline='') as output_file:
                dict_writer = csv.DictWriter(output_file, fieldnames=final_keys, extrasaction='ignore')
                dict_writer.writeheader()
                dict_writer.writerows(financial_data)
            print(f"\nBudget plan report generated as '{output_filename}'.")
        else:
            print("\nNo financial data to generate report.")

    def _run_guided_setup(self, start_date, end_date):
        """Runs the user through all management functions sequentially."""
        print("\n--- Guided Budget Setup ---")
        print("Let's walk through all the sections of your budget.")

        self._manage_balances()
        self._manage_income(start_date, end_date)
        self._manage_groceries(start_date, end_date)
        self._manage_expense_category("Bills", Bill, start_date, end_date)
        self._manage_expense_category("Streaming Services", StreamingService, start_date, end_date)
        self._manage_expense_category("Misc Monthly", Expense, start_date, end_date)
        self._manage_one_time()
        self._manage_savings_transfers(start_date, end_date)

        print("\n--- Guided Setup Complete ---")

    def _manage_balances(self):
        """Handles updating the initial debit balance and managing savings accounts."""
        print("\n--- Initial Balances ---")
        current_debit = self.current_user.budget.initial_debit_balance
        print(f"Current initial debit balance: ${current_debit:.2f}")
        if get_yes_no_input("Do you want to update your initial debit balance?"):
            new_debit = get_float_input("Enter your current debit account balance")
            if new_debit is not None:
                self.current_user.budget.initial_debit_balance = new_debit

        self._manage_savings_accounts()

    def _manage_savings_accounts(self):
        """Manages the creation, modification, and deletion of named savings accounts."""
        print("\n--- Manage Savings Accounts & Balances ---")
        savings_accounts = self.current_user.budget.savings_accounts

        while True:
            if not savings_accounts:
                print("You don't have any savings accounts set up yet.")
                if get_yes_no_input("Do you want to add one?"):
                    name = input("Enter the name for your new savings account (e.g., House Fund): ")
                    balance = get_float_input(f"Enter the current balance for '{name}'")
                    if name and balance is not None:
                        savings_accounts.append(SavingsAccount(name, balance))
                        print(f"Savings account '{name}' added with a balance of ${balance:.2f}.")
                    else:
                        print("Invalid input. Account not created.")
                else:
                    break
            else:
                print("Current Savings Accounts:")
                for i, acc in enumerate(savings_accounts):
                    print(f"  {i + 1}. {acc.name}: ${acc.balance:.2f}")

                if get_yes_no_input("\nDo you want to add a new saving account or modify your existing ones?"):
                    try:
                        choice_str = input(
                            "Enter the number of the account to modify/remove, 'add' a new one, or 'done': ").lower()
                        if choice_str == 'done': break
                        if choice_str == 'add':
                            name = input("Enter the name for your new savings account: ")
                            if any(acc.name == name for acc in savings_accounts):
                                print(f"An account with the name '{name}' already exists.")
                                continue
                            balance = get_float_input(f"Enter the current balance for '{name}'")
                            if name and balance is not None:
                                savings_accounts.append(SavingsAccount(name, balance))
                                print(f"Account '{name}' added.")
                            continue

                        idx = int(choice_str) - 1
                        if 0 <= idx < len(savings_accounts):
                            old_name = savings_accounts[idx].name
                            if get_yes_no_input(
                                    f"Do you want to remove the '{old_name}' account? (This will also remove associated transfer schedules)"):
                                # Cascade delete
                                self.current_user.budget.savings_transfers = [t for t in
                                                                              self.current_user.budget.savings_transfers
                                                                              if t.target != old_name]
                                savings_accounts.pop(idx)
                                print(f"Account '{old_name}' and its transfers have been removed.")
                            else:
                                new_balance = get_float_input(
                                    f"Enter new balance for '{old_name}' (or press Enter to keep ${savings_accounts[idx].balance:.2f})")
                                if new_balance is not None:
                                    savings_accounts[idx].balance = new_balance
                                    print(f"Balance for '{old_name}' updated.")
                        else:
                            print("Invalid number.")
                    except ValueError:
                        print("Invalid input.")
                else:
                    break

    def _manage_income(self, start_date, end_date):
        """Handles the logic for adding or updating income information."""
        print("\n--- Income Information ---")
        budget = self.current_user.budget
        income_item = budget.income

        # --- UPDATE/MODIFY EXISTING INCOME ---
        if income_item and income_item.amount > 0:
            print(f"Current income: ${income_item.amount:.2f} ({income_item.frequency})")
            if not get_yes_no_input("Do you want to update your income information?"):
                return

            new_amount = get_float_input(f"Enter new income (or press Enter to keep ${income_item.amount:.2f})")
            if new_amount is not None: income_item.amount = new_amount

            if get_yes_no_input("Do you want to update the frequency or schedule start date?"):
                new_freq = get_frequency_input(
                    f"Enter new frequency (or press Enter to keep '{income_item.frequency}')",
                    extra_options=['twice-monthly'])
                if new_freq is not None: income_item.frequency = new_freq

                # Use the existing start date as a default for the prompt
                prompt = "Enter the date of your next upcoming paycheck"
                if income_item.start_date_for_schedule:
                    prompt += f" (or press Enter to keep {income_item.start_date_for_schedule.strftime('%Y-%m-%d')})"

                new_start_date = get_date_input(prompt)
                if new_start_date is not None: income_item.start_date_for_schedule = new_start_date

            if get_yes_no_input("Do you want to update the income end date?"):
                if get_yes_no_input("Does this income have an end date?"):
                    income_item.expiry_date = get_date_input("Enter the income end date")
                else:
                    income_item.expiry_date = None

            # After all changes, perform a full recalculation of the income schedule
            self._update_single_item_schedule(income_item, start_date, end_date)

        # --- ADD NEW INCOME ---
        else:
            amount = get_float_input("Enter your income amount after taxes")
            if amount is None: return

            frequency = get_frequency_input("How often do you receive this income?", extra_options=['twice-monthly'])
            if frequency is None: return

            start_date_for_schedule = get_date_input("Enter the date of your next upcoming paycheck")
            if start_date_for_schedule is None: return

            expiry_date = None
            if get_yes_no_input("Does this income have an end date (e.g., end of contract)?"):
                expiry_date = get_date_input("Enter the income end date")

            # Create the new income object
            new_income = Income(amount=amount, frequency=frequency,
                                start_date_for_schedule=start_date_for_schedule, expiry_date=expiry_date)

            # Calculate its schedule
            self._update_single_item_schedule(new_income, start_date, end_date)
            budget.income = new_income

        if not budget.income.dates:
            print("Warning: No pay dates were generated for the budget period.")
        else:
            print("\nCalculated Pay Dates for your budget period:")
            for date in budget.income.dates[:12]:
                print(f"- {date.strftime('%Y-%m-%d')}")
            if len(budget.income.dates) > 12:
                print(f"... and {len(budget.income.dates) - 12} more.")

    def _manage_groceries(self, start_date, end_date):
        """Handles the logic for managing grocery expenses."""
        print("\n--- Manage Your Groceries ---")
        budget = self.current_user.budget
        grocery_expense = next((exp for exp in budget.expenses if exp.category == 'Groceries'), None)

        if grocery_expense:
            print(f"Current typical weekly grocery expense: ${grocery_expense.amount:.2f}")
            if get_yes_no_input("Do you want to update your grocery expense details?"):
                new_amount = get_float_input(f"Enter new amount (or press Enter to keep ${grocery_expense.amount:.2f})")
                if new_amount is not None:
                    grocery_expense.amount = new_amount

                if get_yes_no_input("Do you want to update the schedule (e.g., the start date)?"):
                    start_date_for_schedule = get_date_input("Enter the first date for your weekly grocery expense")
                    dates = get_recurring_dates(start_date_for_schedule, end_date, 'weekly', self.holidays,
                                                adjust_for_holidays=False)
                    grocery_expense.start_date_for_schedule = start_date_for_schedule
                    grocery_expense.dates = dates
                    print("Grocery schedule updated.")

        elif get_yes_no_input("Do you have a regular grocery expense?"):
            amount = get_float_input("Enter your typical weekly grocery expense")
            if amount is not None:
                # --- MODIFIED LOGIC ---
                # Now we properly ask for a start date for the weekly schedule
                start_date_for_schedule = get_date_input(
                    "Enter the first date for this weekly expense (e.g., next Saturday)")
                dates = get_recurring_dates(start_date_for_schedule, end_date, 'weekly', self.holidays,
                                            adjust_for_holidays=False)

                budget.expenses.append(
                    Expense(name='Groceries', amount=amount, frequency='weekly', category='Groceries',
                            dates=dates, start_date_for_schedule=start_date_for_schedule)
                )
                print("Weekly grocery expense has been set up.")

    def _manage_expense_category(self, category_name, expense_class, start_date, end_date):
        """Generic function to manage an expense category."""
        print(f"\n--- Manage {category_name} ---")
        budget = self.current_user.budget

        current_expenses = [exp for exp in budget.expenses if exp.category == category_name]

        if current_expenses:
            if get_yes_no_input(f"Do you want to modify or remove an existing item in {category_name}?"):
                while True:
                    current_expenses_loop = [exp for exp in budget.expenses if exp.category == category_name]
                    if not current_expenses_loop:
                        print(f"No more items in {category_name} to modify.")
                        break

                    print(f"Existing {category_name}:")
                    for i, item in enumerate(current_expenses_loop):
                        expiry_info = f", Expires: {item.expiry_date.strftime('%Y-%m-%d')}" if item.expiry_date else ", No expiry"
                        print(f"  {i + 1}. {item.name}: ${item.amount:.2f} ({item.frequency}{expiry_info})")

                    try:
                        choice = input(
                            f"Enter the number of the item to modify/remove, or 'done' to finish: ").lower()
                        if choice == 'done': break
                        idx = int(choice) - 1

                        if 0 <= idx < len(current_expenses_loop):
                            selected_item = current_expenses_loop[idx]
                            if get_yes_no_input(f"Do you want to remove this item?"):
                                budget.expenses.remove(selected_item)
                                print(f"'{selected_item.name}' removed.")
                                continue

                            # --- MODIFIED LOGIC ---
                            # First, update all properties of the item
                            new_name = input(f"Enter new name (or press Enter to keep '{selected_item.name}'): ")
                            if new_name: selected_item.name = new_name

                            new_amount = get_float_input(
                                f"Enter new amount (or press Enter to keep ${selected_item.amount:.2f})")
                            if new_amount is not None: selected_item.amount = new_amount

                            if get_yes_no_input("Do you want to update the payment schedule?"):
                                # For expenses, we don't adjust for holidays
                                freq, dates, start_sched = self._get_schedule(start_date, end_date,
                                                                              adjust_for_holidays=False)
                                if freq:
                                    selected_item.frequency = freq
                                    # Temporarily assign dates; they will be recalculated and filtered next
                                    selected_item.dates = dates
                                    selected_item.start_date_for_schedule = start_sched

                            if get_yes_no_input("Do you want to update the expiry date?"):
                                if get_yes_no_input("Does it have an expiry date?"):
                                    selected_item.expiry_date = get_date_input("Enter the new expiry date")
                                else:
                                    selected_item.expiry_date = None

                            # Second, recalculate the schedule based on all updated properties
                            self._update_single_item_schedule(selected_item, start_date, end_date)
                            print(f"'{selected_item.name}' updated.")
                        else:
                            print("Invalid number.")
                    except ValueError:
                        print("Invalid input. Please enter a number or 'done'.")

        if get_yes_no_input(f"Do you want to add a new item to {category_name}?"):
            while True:
                name = input(f"Enter the name of the new item: ")
                amount = get_float_input(f"Enter the amount for {name}")
                if amount is None: break

                expiry_date = None
                if get_yes_no_input(f"Does {name} have an expiry date?"):
                    expiry_date = get_date_input(f"Enter the expiry date for {name}")

                frequency, dates, start_date_for_schedule = self._get_schedule(start_date, end_date,
                                                                               adjust_for_holidays=False)
                if frequency is None:
                    print("Item creation cancelled.")
                    break

                # Filter dates based on expiry date upon creation
                if expiry_date:
                    dates = [d for d in dates if d <= expiry_date]

                new_expense_data = {
                    'name': name, 'amount': amount, 'frequency': frequency, 'dates': dates,
                    'start_date_for_schedule': start_date_for_schedule, 'expiry_date': expiry_date
                }
                if expense_class == Expense:
                    new_expense_data['category'] = category_name

                budget.expenses.append(expense_class(**new_expense_data))
                print(f"Added '{name}' to {category_name}.")

                if not get_yes_no_input(f"Add another item to {category_name}?"):
                    break

    def _manage_one_time(self):
        """Manages one-time expenses."""
        print("\n--- Manage One-Time Expenses ---")
        budget = self.current_user.budget
        one_time_expenses = [exp for exp in budget.expenses if exp.category == 'One-Time']

        # --- MODIFIED LOGIC ---
        # Only ask to modify if one-time expenses exist.
        if one_time_expenses:
            if get_yes_no_input("Do you want to modify or remove an existing one-time expense?"):
                while True:
                    # Re-fetch inside loop
                    one_time_expenses_loop = [exp for exp in budget.expenses if exp.category == 'One-Time']
                    if not one_time_expenses_loop:
                        print("No more one-time expenses to modify.")
                        break

                    print("Existing One-Time Expenses:")
                    for i, item in enumerate(one_time_expenses_loop):
                        date_str = item.dates[0].strftime('%Y-%m-%d') if item.dates else "N/A"
                        print(f"  {i + 1}. {item.name}: ${item.amount:.2f} on {date_str}")

                    try:
                        choice = input(
                            "Enter the number of the expense to modify/remove, or 'done' to finish: ").lower()
                        if choice == 'done': break
                        idx = int(choice) - 1
                        if 0 <= idx < len(one_time_expenses_loop):
                            selected_item = one_time_expenses_loop[idx]
                            if get_yes_no_input(f"Do you want to remove this expense?"):
                                budget.expenses.remove(selected_item)
                                print(f"'{selected_item.name}' removed.")
                                continue

                            new_name = input(f"Enter new name (or press Enter to keep '{selected_item.name}'): ")
                            if new_name: selected_item.name = new_name

                            new_amount = get_float_input(
                                f"Enter new amount (or press Enter to keep ${selected_item.amount:.2f})")
                            if new_amount is not None: selected_item.amount = new_amount

                            if get_yes_no_input("Update the date?"):
                                selected_item.dates = [get_date_input("Enter the new date")]

                            print(f"'{selected_item.name}' updated.")
                        else:
                            print("Invalid number.")
                    except ValueError:
                        print("Invalid input.")

        # This 'add' part is always asked.
        if get_yes_no_input("Do you want to add a new one-time expense?"):
            while True:
                name = input("Enter the name of the one-time expense or 'done' to finish: ").lower()
                if name == 'done': break
                amount = get_float_input(f"Enter the amount for {name}")
                if amount is None: break
                date = get_date_input(f"Enter the date for {name}")
                budget.expenses.append(
                    Expense(name=name, amount=amount, frequency='one-time', dates=[date], category='One-Time'))
                if not get_yes_no_input("Add another one-time expense?"):
                    break

    def _manage_savings_transfers(self, start_date, end_date):
        """Manages adding, modifying, and removing savings transfers."""
        print("\n--- Manage Savings Transfers ---")
        budget = self.current_user.budget

        if budget.savings_transfers:
            if get_yes_no_input("Do you want to modify or remove an existing savings transfer?"):
                while True:
                    if not budget.savings_transfers:
                        print("No savings transfers to modify.")
                        break

                    print("Existing Savings Transfers:")
                    for i, trans in enumerate(budget.savings_transfers):
                        print(f"  {i + 1}. ${trans.amount:.2f} ({trans.frequency}) to '{trans.target}'")

                    try:
                        choice = input("Enter number to modify/remove, or 'done': ").lower()
                        if choice == 'done': break
                        idx = int(choice) - 1

                        if 0 <= idx < len(budget.savings_transfers):
                            selected_trans = budget.savings_transfers[idx]
                            if get_yes_no_input("Remove this transfer?"):
                                budget.savings_transfers.pop(idx)
                                print("Transfer removed.")
                                continue

                            new_amount = get_float_input(f"New amount (keep ${selected_trans.amount:.2f})")
                            if new_amount is not None: selected_trans.amount = new_amount

                            if get_yes_no_input("Change target account?"):
                                new_target = get_savings_target_input("Choose new target", budget.savings_accounts)
                                if new_target: selected_trans.target = new_target

                            if get_yes_no_input("Update schedule?"):
                                freq_opts = ['match payday'] if budget.income else None
                                # --- MODIFIED LOGIC ---
                                # We set adjust_for_holidays=False because only 'match payday' should adjust,
                                # and that case is handled automatically inside _get_schedule.
                                freq, dates, start_sched = self._get_schedule(start_date, end_date,
                                                                              extra_freq_options=freq_opts,
                                                                              adjust_for_holidays=False)
                                if freq:
                                    selected_trans.frequency = freq
                                    selected_trans.dates = dates
                                    selected_trans.start_date_for_schedule = start_sched

                                # After changes, we must recalculate the item's schedule
                                self._update_single_item_schedule(selected_trans, start_date, end_date)

                            print("Transfer updated.")
                        else:
                            print("Invalid number.")
                    except ValueError:
                        print("Invalid input.")

        if get_yes_no_input("Add a new savings transfer?"):
            if not budget.savings_accounts:
                print("Error: You must create a savings account first.")
                return
            while True:
                amount = get_float_input("Enter transfer amount")
                if amount is None: break

                target = get_savings_target_input("Which account is this for?", budget.savings_accounts)
                if target is None: break

                freq_opts = ['match payday'] if budget.income else None
                # --- MODIFIED LOGIC ---
                # This should also be False.
                frequency, dates, start_date_for_schedule = self._get_schedule(start_date, end_date,
                                                                               extra_freq_options=freq_opts,
                                                                               adjust_for_holidays=False)
                if frequency is None:
                    print("Transfer creation cancelled.")
                    break

                name = f"Transfer to {target}"
                new_transfer = SavingsTransfer(name=name, amount=amount, frequency=frequency, target=target,
                                               dates=dates,
                                               start_date_for_schedule=start_date_for_schedule)

                # Recalculate just in case 'match payday' was selected
                self._update_single_item_schedule(new_transfer, start_date, end_date)

                budget.savings_transfers.append(new_transfer)
                print("Savings transfer added.")

                if not get_yes_no_input("Add another transfer?"):
                    break

    def _get_schedule(self, start_date, end_date, extra_freq_options=None, adjust_for_holidays=False):
        """Helper to get schedule details for any financial item."""
        frequency = None
        dates = []
        start_date_for_schedule = None

        if get_yes_no_input("Do you want to set a periodic schedule? (e.g., weekly, monthly)"):
            frequency = get_frequency_input("How often does this occur?", extra_options=extra_freq_options)
            if not frequency: return None, [], None

            if frequency == 'match payday':
                if self.current_user.budget.income and self.current_user.budget.income.dates:
                    dates = self.current_user.budget.income.dates
                    print("Schedule set to match income dates.")
                else:
                    print("Cannot match payday because income is not set up. Please set schedule manually.")
                    return None, [], None
                    # --- MODIFIED LOGIC --- (added adjust_for_holidays parameter to the call)
            elif frequency == 'bi-monthly':
                start_date_for_schedule = get_date_input("Enter the start date for this schedule")
                dates = calculate_bi_monthly_dates_every_two_months(start_date_for_schedule, end_date, self.holidays,
                                                                    adjust_for_holidays=adjust_for_holidays)
            elif frequency == "one-time":
                dates.append(get_date_input("Enter the specific date for this item"))
            else:
                start_date_for_schedule = get_date_input("Enter the start date for this schedule")
                dates = get_recurring_dates(start_date_for_schedule, end_date, frequency, self.holidays,
                                            adjust_for_holidays=adjust_for_holidays)
        else:
            print("You've chosen to enter specific dates manually.")
            dates = get_multiple_dates("Enter a specific date (or 'done' to finish)")
            if dates:
                frequency = "manual"
            else:
                print("No dates entered.")
                return None, [], None

        return frequency, dates, start_date_for_schedule

    def _update_single_item_schedule(self, item, start_date, end_date):
        """
        Calculates and filters the date schedule for a single financial item.
        This ensures the date list is correct after any modification and respects the expiry date.
        """
        # Step 1: Regenerate the full list of dates for the budget period
        freq = item.frequency
        holidays = self.holidays  # The app class has access to the loaded holidays

        # --- MODIFIED LOGIC ---
        # Determine if dates should be adjusted.
        should_adjust = (isinstance(item, SavingsTransfer) and item.frequency == 'match payday')

        # Generate the full list of potential dates
        if freq == 'match payday' and self.current_user.budget.income:
            item.dates = self.current_user.budget.income.dates
        elif item.start_date_for_schedule:
            original_start = item.start_date_for_schedule
            if freq == 'bi-monthly':
                item.dates = calculate_bi_monthly_dates_every_two_months(
                    original_start, end_date, holidays, adjust_for_holidays=should_adjust
                )
            elif freq not in ['one-time', 'manual', 'weekly']:
                item.dates = get_recurring_dates(
                    original_start, end_date, freq, holidays, adjust_for_holidays=should_adjust
                )

        # Step 2: Filter the regenerated list based on the item's expiry date
        # This check is safe for SavingsTransfer as it won't have the attribute
        if hasattr(item, 'expiry_date') and item.expiry_date:
            item.dates = [d for d in item.dates if d <= item.expiry_date]


if __name__ == "__main__":
    app = BudgetPlannerApp()
    app.run()