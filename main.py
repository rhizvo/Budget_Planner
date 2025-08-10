import csv
from datetime import datetime, timedelta
from collections import defaultdict
import calendar
import os
import json


# --- Helper Functions ---

def get_date_input(prompt):
    """Helper function to get a valid date input."""
    while True:
        date_str = input(prompt + " (YYYY-MM-DD): ")
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")


def get_float_input(prompt):
    """Helper function to get a valid float input."""
    while True:
        try:
            value = float(input(prompt + ": "))
            if value < 0:
                print("Please enter a non-negative number.")
                continue
            return value
        except ValueError:
            print("Invalid input. Please enter a number.")


def get_frequency_input(prompt):
    """Helper function to get a valid frequency input."""
    while True:
        freq = input(prompt + " (weekly, bi-weekly, monthly, quarterly, yearly, one-time): ").lower()
        if freq in ["weekly", "bi-weekly", "monthly", "quarterly", "yearly", "one-time"]:
            return freq
        else:
            print("Invalid frequency. Please choose from: weekly, bi-weekly, monthly, quarterly, yearly, one-time.")


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


def load_holidays(filepath):
    """Loads holidays from a TXT file into a set of date objects."""
    holidays_set = set()
    if not os.path.exists(filepath):
        print(f"Warning: Holiday file not found at '{filepath}'. Payday adjustments will only consider weekends.")
        return holidays_set

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
        print(f"Error reading holiday file: {e}")
    return holidays_set


def is_business_day(date, holidays_set):
    """Checks if a given date is a business day (Mon-Fri and not a holiday)."""
    if date.weekday() >= 5:  # Saturday or Sunday
        return False
    if date in holidays_set:
        return False
    return True


def get_bi_monthly_pay_dates(start_date, end_date, holidays_set):
    """
    Generates 15th and last-day-of-month pay dates between start_date and end_date,
    adjusting to the closest business day *before* if it falls on a weekend or holiday.
    """
    pay_dates = []
    current_iter_date = start_date

    while current_iter_date <= end_date:
        year = current_iter_date.year
        month = current_iter_date.month

        # --- Calculate 15th of the month ---
        target_15th = datetime(year, month, 15).date()
        if start_date <= target_15th <= end_date:
            adjusted_date = target_15th
            while not is_business_day(adjusted_date, holidays_set):
                adjusted_date -= timedelta(days=1)
            pay_dates.append(adjusted_date)

        # --- Calculate last day of the month ---
        last_day_of_month_num = calendar.monthrange(year, month)[1]
        target_last_day = datetime(year, month, last_day_of_month_num).date()
        if start_date <= target_last_day <= end_date:
            adjusted_date = target_last_day
            while not is_business_day(adjusted_date, holidays_set):
                adjusted_date -= timedelta(days=1)
            pay_dates.append(adjusted_date)

        if month == 12:
            current_iter_date = datetime(year + 1, 1, 1).date()
        else:
            current_iter_date = datetime(year, month + 1, 1).date()

    pay_dates = sorted(list(set(pay_dates)))
    pay_dates = [d for d in pay_dates if d >= datetime.now().date()]

    return pay_dates


# --- JSON Save/Load Functions ---

def save_budget_data(data, filename="my_budget_data.json"):
    """Saves the budget configuration data to a JSON file."""
    try:
        serializable_data = data.copy()
        if 'expense_categories' in serializable_data:
            for category, items in serializable_data['expense_categories'].items():
                for item in items:
                    if 'dates' in item and item['dates']:
                        item['dates'] = [d.isoformat() for d in item['dates']]
                    if 'expiry_date' in item and item['expiry_date']:
                        item['expiry_date'] = item['expiry_date'].isoformat()
        if 'savings_transfers' in serializable_data:
            for transfer in serializable_data['savings_transfers']:
                if 'dates' in transfer and transfer['dates']:
                    transfer['dates'] = [d.isoformat() for d in transfer['dates']]

        # New: Serialize income dates
        if 'income' in serializable_data and 'dates' in serializable_data['income'] and serializable_data['income'][
            'dates']:
            serializable_data['income']['dates'] = [d.isoformat() for d in serializable_data['income']['dates']]

        with open(filename, 'w') as f:
            json.dump(serializable_data, f, indent=4)
        print(f"\nBudget configuration saved to '{filename}'.")
    except Exception as e:
        print(f"Error saving budget data: {e}")


def load_budget_data(filename="my_budget_data.json"):
    """Loads the budget configuration data from a JSON file."""
    if not os.path.exists(filename):
        print(f"No existing budget file found at '{filename}'. Starting with an empty budget.")
        return None

    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            if 'expense_categories' in data:
                for category, items in data['expense_categories'].items():
                    for item in items:
                        if 'dates' in item and item['dates']:
                            item['dates'] = [datetime.fromisoformat(d).date() for d in item['dates']]
                        if 'expiry_date' in item and item['expiry_date']:
                            item['expiry_date'] = datetime.fromisoformat(item['expiry_date']).date()
            if 'savings_transfers' in data:
                for transfer in data['savings_transfers']:
                    if 'dates' in transfer and transfer['dates']:
                        transfer['dates'] = [datetime.fromisoformat(d).date() for d in transfer['dates']]

            # New: Deserialize income dates
            if 'income' in data and 'dates' in data['income'] and data['income']['dates']:
                data['income']['dates'] = [datetime.fromisoformat(d).date() for d in data['income']['dates']]

            data.pop('income_pay_dates', None)

            print(f"Budget configuration loaded from '{filename}'.")
            return data
    except json.JSONDecodeError as e:
        print(f"Error reading budget file '{filename}'. It might be corrupted: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading budget data: {e}")
        return None


def get_recurring_dates(start_date, end_date, frequency, holidays_set=None, initial_day=None):
    """
    Generates a list of recurring dates based on frequency, adjusting for weekends/holidays.
    """
    dates = []
    current_date = start_date
    holidays_set = holidays_set if holidays_set is not None else set()

    while current_date <= end_date:
        adjusted_date = current_date
        while not is_business_day(adjusted_date, holidays_set):
            adjusted_date -= timedelta(days=1)
        dates.append(adjusted_date)

        if frequency == 'weekly':
            current_date += timedelta(weeks=1)
        elif frequency == 'bi-weekly':
            current_date += timedelta(weeks=2)
        elif frequency == 'monthly':
            # Corrected logic for monthly rollover
            new_month = current_date.month + 1
            new_year = current_date.year
            if new_month > 12:
                new_month = 1
                new_year += 1
            # Adjust day if the new month doesn't have enough days
            day = min(current_date.day, calendar.monthrange(new_year, new_month)[1])
            current_date = datetime(new_year, new_month, day).date()
        elif frequency == 'quarterly':
            # Corrected logic for quarterly rollover
            new_month = current_date.month + 3
            new_year = current_date.year
            if new_month > 12:
                new_month -= 12
                new_year += 1
            day = min(current_date.day, calendar.monthrange(new_year, new_month)[1])
            current_date = datetime(new_year, new_month, day).date()
        elif frequency == 'yearly':
            current_date = datetime(current_date.year + 1, current_date.month, current_date.day).date()
        else:
            break

    # Remove dates that are before the current date
    return sorted([d for d in dates if d >= datetime.now().date()])


# --- Main Budget Planning Function ---

def plan_budget_for_year():
    print("--- Budget Planner for the Rest of the Year ---")

    today = datetime.now().date()
    end_of_year = datetime(today.year, 12, 31).date()

    budget_config_filename = "my_budget_data.json"

    budget_config = {
        'initial_debit_balance': 0.0,
        'initial_savings_balance': 0.0,
        'income': {
            'amount': 0.0,
            'frequency': 'bi-weekly',
            'dates': []
        },
        'expense_categories': {
            'Groceries': [],
            'Bills': [],
            'Streaming Services': [],
            'Misc Monthly': [],
            'One-Time': []
        },
        'savings_transfers': [],
        'holiday_filepath': ""
    }

    if os.path.exists(budget_config_filename):
        if get_yes_no_input(f"Do you want to load an existing budget from '{budget_config_filename}'?"):
            loaded_data = load_budget_data(budget_config_filename)
            if loaded_data:
                budget_config.update(loaded_data)
            else:
                print("Failed to load existing budget. Starting a new budget.")
        else:
            print("Starting a new budget.")
    else:
        print("No existing budget file found. Starting a new budget.")

    print("\n--- Initial Balances ---")
    if budget_config['initial_debit_balance'] > 0 or budget_config['initial_savings_balance'] > 0:
        print(f"Current initial debit balance: ${budget_config['initial_debit_balance']:.2f}")
        print(f"Current initial savings balance: ${budget_config['initial_savings_balance']:.2f}")
        if get_yes_no_input("Do you want to update your initial balances?"):
            budget_config['initial_debit_balance'] = get_float_input("Enter your current debit account balance")
            budget_config['initial_savings_balance'] = get_float_input("Enter your current savings account balance")
    else:
        budget_config['initial_debit_balance'] = get_float_input("Enter your current debit account balance")
        budget_config['initial_savings_balance'] = get_float_input("Enter your current savings account balance")

    print("\n--- Holiday Information ---")
    if budget_config['holiday_filepath'] and os.path.exists(budget_config['holiday_filepath']):
        print(f"Current holiday file path: {budget_config['holiday_filepath']}")
        if get_yes_no_input("Do you want to change the holiday file path?"):
            budget_config['holiday_filepath'] = input(
                "Enter the new path to your holiday list file (e.g., holidays.txt): ")
    else:
        budget_config['holiday_filepath'] = input("Enter the path to your holiday list file (e.g., holidays.txt): ")

    holidays = load_holidays(budget_config['holiday_filepath'])
    if holidays:
        print(f"Loaded {len(holidays)} holidays.")
    else:
        print("No holidays loaded or file not found. Payday adjustments will only consider weekends.")

    print("\n--- Income Information ---")
    current_income_amount = budget_config['income']['amount']
    current_income_freq = budget_config['income']['frequency']

    if current_income_amount > 0:
        print(f"Current income: ${current_income_amount:.2f} ({current_income_freq})")
        if get_yes_no_input("Do you want to update your income information?"):
            budget_config['income']['amount'] = get_float_input("Enter your new income amount after taxes")
            budget_config['income']['frequency'] = get_frequency_input("How often do you receive this income?")
            budget_config['income']['dates'] = [get_date_input("Enter the date of your next upcoming paycheck")]
    else:
        budget_config['income']['amount'] = get_float_input("Enter your income amount after taxes")
        budget_config['income']['frequency'] = get_frequency_input("How often do you receive this income?")
        budget_config['income']['dates'] = [get_date_input("Enter the date of your next upcoming paycheck")]

    # Recalculate income dates
    if budget_config['income']['frequency'] == 'bi-monthly':
        budget_config['income']['dates'] = get_bi_monthly_pay_dates(today, end_of_year, holidays)
    elif budget_config['income']['frequency'] != 'one-time' and budget_config['income']['dates']:
        budget_config['income']['dates'] = get_recurring_dates(budget_config['income']['dates'][0], end_of_year,
                                                               budget_config['income']['frequency'], holidays)

    if not budget_config['income']['dates']:
        print("Warning: No pay dates were generated for the rest of the year. Please check your input.")
    else:
        print("\nCalculated Pay Dates for the rest of the year (adjusted for weekends/holidays):")
        for date in budget_config['income']['dates']:
            print(f"- {date.strftime('%Y-%m-%d')}")

    print("\n--- Manage Your Expenses ---")

    if budget_config['expense_categories']['Groceries']:
        current_groceries = budget_config['expense_categories']['Groceries'][0]['amount']
        print(f"Current typical weekly grocery expense: ${current_groceries:.2f}")
        if get_yes_no_input("Do you want to update your weekly grocery expense?"):
            budget_config['expense_categories']['Groceries'][0]['amount'] = get_float_input(
                "Enter your new typical weekly grocery expense")
    elif get_yes_no_input("Do you have a regular grocery expense?"):
        groceries_amount = get_float_input("Enter your typical weekly grocery expense")
        budget_config['expense_categories']['Groceries'].append(
            {'name': 'Groceries', 'amount': groceries_amount, 'frequency': 'weekly', 'dates': [], 'expiry_date': None})

    print("\n--- Manage Your Bills ---")
    current_bills = budget_config['expense_categories']['Bills']
    if current_bills:
        print("Existing Bills:")
        for i, bill in enumerate(current_bills):
            expiry_info = f", Expires: {bill['expiry_date'].strftime('%Y-%m-%d')}" if bill[
                'expiry_date'] else ", No expiry"
            print(f"  {i + 1}. {bill['name']}: ${bill['amount']:.2f} ({bill['frequency']}{expiry_info})")

        if get_yes_no_input("Do you want to modify or remove an existing bill?"):
            while True:
                try:
                    choice = input("Enter the number of the bill to modify/remove, or 'done' to finish: ").lower()
                    if choice == 'done': break
                    idx = int(choice) - 1
                    if 0 <= idx < len(current_bills):
                        selected_bill = current_bills[idx]
                        print(f"Modifying: {selected_bill['name']}")
                        if get_yes_no_input("Do you want to remove this bill?"):
                            current_bills.pop(idx)
                            print(f"{selected_bill['name']} removed.")
                            break

                        selected_bill['name'] = input(
                            f"Enter new name for {selected_bill['name']} (or press Enter to keep '{selected_bill['name']}'): ") or \
                                                selected_bill['name']
                        selected_bill['amount'] = get_float_input(
                            f"Enter new amount for {selected_bill['name']} (current: ${selected_bill['amount']:.2f})") or \
                                                  selected_bill['amount']

                        new_freq = get_frequency_input(
                            f"Enter new frequency for {selected_bill['name']} (current: {selected_bill['frequency']})")
                        selected_bill['frequency'] = new_freq

                        if new_freq not in ["weekly"] and get_yes_no_input(
                                f"Do you want to update specific payment dates for {selected_bill['name']}? (current dates: {[d.strftime('%Y-%m-%d') for d in selected_bill['dates']]})"):
                            selected_bill['dates'] = get_multiple_dates(
                                f"Enter new specific payment dates for {selected_bill['name']}")
                            if not selected_bill['dates'] and new_freq != "one-time":
                                print(
                                    "Warning: For recurring expenses without specific dates, the program will estimate. For accuracy, provide specific dates if known.")
                        elif new_freq == "one-time" and not selected_bill['dates']:
                            selected_bill['dates'].append(get_date_input(
                                f"Enter the specific date for this one-time {selected_bill['name']} payment"))
                        elif new_freq == "weekly":
                            selected_bill['dates'] = []

                        if get_yes_no_input(
                                f"Do you want to update the expiry date for {selected_bill['name']}? (current: {selected_bill['expiry_date'].strftime('%Y-%m-%d') if selected_bill['expiry_date'] else 'None'})"):
                            if get_yes_no_input("Does it now have an expiry date?"):
                                selected_bill['expiry_date'] = get_date_input(
                                    f"Enter the new expiry date for {selected_bill['name']}")
                            else:
                                selected_bill['expiry_date'] = None
                        print(f"{selected_bill['name']} updated.")
                    else:
                        print("Invalid bill number.")
                except ValueError:
                    print("Invalid input. Please enter a number or 'done'.")

    if get_yes_no_input("Do you want to add a new bill?"):
        while True:
            bill_name = input("Enter the name of the new bill: ")
            bill_amount = get_float_input(f"Enter the amount for {bill_name}")
            bill_frequency = get_frequency_input(f"How often do you pay {bill_name}?")

            bill_expiry_date = None
            if get_yes_no_input(f"Does {bill_name} have an expiry date?"):
                bill_expiry_date = get_date_input(f"Enter the expiry date for {bill_name}")

            bill_dates = []
            if bill_frequency not in ["weekly"] and get_yes_no_input(
                    f"Do you have specific payment dates for {bill_name}?"):
                bill_dates = get_multiple_dates(f"Enter a specific payment date for {bill_name}")
                if not bill_dates and bill_frequency != "one-time":
                    print("Warning: For recurring expenses without specific dates, the program will estimate.")
            elif bill_frequency == "one-time":
                bill_dates.append(get_date_input(f"Enter the specific date for this one-time {bill_name} payment"))

            if bill_dates and bill_frequency not in ["weekly", "one-time"]:
                adjusted_bill_dates = []
                for b_date in bill_dates:
                    adjusted_date = b_date
                    while not is_business_day(adjusted_date, holidays):
                        adjusted_date -= timedelta(days=1)
                    adjusted_bill_dates.append(adjusted_date)
                bill_dates = adjusted_bill_dates

            budget_config['expense_categories']['Bills'].append({
                'name': bill_name,
                'amount': bill_amount,
                'frequency': bill_frequency,
                'dates': bill_dates,
                'expiry_date': bill_expiry_date
            })
            if not get_yes_no_input("Add another bill?"):
                break

    print("\n--- Manage Streaming Services ---")
    current_streaming = budget_config['expense_categories']['Streaming Services']
    if get_yes_no_input("Do you want to add/update streaming services?"):
        while True:
            service_name = input(
                "Enter the name of the streaming service (e.g., Netflix, Spotify) or 'done' to finish: ").lower()
            if service_name == 'done': break

            found_service = next((s for s in current_streaming if s['name'].lower() == service_name), None)

            if found_service:
                print(
                    f"Service '{found_service['name']}' already exists: ${found_service['amount']:.2f} (Expires: {found_service['expiry_date'].strftime('%Y-%m-%d') if found_service['expiry_date'] else 'None'})")
                if get_yes_no_input("Do you want to update this service?"):
                    found_service['amount'] = get_float_input(
                        f"Enter new monthly amount for {found_service['name']} (current: ${found_service['amount']:.2f})")
                    if get_yes_no_input(f"Do you want to update the expiry date for {found_service['name']}?"):
                        if get_yes_no_input("Does it now have an expiry date?"):
                            found_service['expiry_date'] = get_date_input(
                                f"Enter the new expiry date for {found_service['name']}")
                        else:
                            found_service['expiry_date'] = None
            else:
                service_amount = get_float_input(f"Enter the monthly amount for {service_name}")
                service_expiry_date = None
                if get_yes_no_input(f"Does {service_name} have an expiry date?"):
                    service_expiry_date = get_date_input(f"Enter the expiry date for {service_name}")
                current_streaming.append(
                    {'name': service_name, 'amount': service_amount, 'frequency': 'monthly', 'dates': [],
                     'expiry_date': service_expiry_date})
            if not get_yes_no_input("Add/Update another streaming service?"):
                break

    print("\n--- Manage Miscellaneous Monthly Expenses ---")
    current_misc = budget_config['expense_categories']['Misc Monthly']
    if get_yes_no_input("Do you want to add/update miscellaneous monthly expenses?"):
        while True:
            misc_name = input("Enter the name of the miscellaneous expense or 'done' to finish: ").lower()
            if misc_name == 'done': break

            found_misc = next((m for m in current_misc if m['name'].lower() == misc_name), None)

            if found_misc:
                print(
                    f"Expense '{found_misc['name']}' already exists: ${found_misc['amount']:.2f} (Expires: {found_misc['expiry_date'].strftime('%Y-%m-%d') if found_misc['expiry_date'] else 'None'})")
                if get_yes_no_input("Do you want to update this expense?"):
                    found_misc['amount'] = get_float_input(
                        f"Enter new monthly amount for {found_misc['name']} (current: ${found_misc['amount']:.2f})")
                    if get_yes_no_input(f"Do you want to update the expiry date for {found_misc['name']}?"):
                        if get_yes_no_input("Does it now have an expiry date?"):
                            found_misc['expiry_date'] = get_date_input(
                                f"Enter the new expiry date for {found_misc['name']}")
                        else:
                            found_misc['expiry_date'] = None
                    if get_yes_no_input(f"Do you want to update specific payment dates for {found_misc['name']}?"):
                        found_misc['dates'] = get_multiple_dates(
                            f"Enter new specific payment dates for {found_misc['name']}")
            else:
                misc_amount = get_float_input(f"Enter the monthly amount for {misc_name}")
                misc_expiry_date = None
                if get_yes_no_input(f"Does {misc_name} have an expiry date?"):
                    misc_expiry_date = get_date_input(f"Enter the expiry date for {misc_name}")
                misc_dates = []
                if get_yes_no_input(f"Do you have specific payment dates for {misc_name}?"):
                    misc_dates = get_multiple_dates(f"Enter a specific pay date for {misc_name}")
                current_misc.append(
                    {'name': misc_name, 'amount': misc_amount, 'frequency': 'monthly', 'dates': misc_dates,
                     'expiry_date': misc_expiry_date})
            if not get_yes_no_input("Add/Update another miscellaneous monthly expense?"):
                break

    print("\n--- Manage One-Time Expenses ---")
    current_one_time = budget_config['expense_categories']['One-Time']
    if get_yes_no_input("Do you want to add/update one-time expenses?"):
        while True:
            one_time_name = input("Enter the name of the one-time expense or 'done' to finish: ").lower()
            if one_time_name == 'done': break

            found_one_time = next((o for o in current_one_time if o['name'].lower() == one_time_name), None)

            if found_one_time:
                print(
                    f"Expense '{found_one_time['name']}' already exists: ${found_one_time['amount']:.2f} on {found_one_time['dates'][0].strftime('%Y-%m-%d')}")
                if get_yes_no_input("Do you want to update this expense?"):
                    found_one_time['amount'] = get_float_input(
                        f"Enter new amount for {found_one_time['name']} (current: ${found_one_time['amount']:.2f})")
                    found_one_time['dates'] = [get_date_input(
                        f"Enter the new date for {found_one_time['name']} (current: {found_one_time['dates'][0].strftime('%Y-%m-%d')})")]
            else:
                one_time_amount = get_float_input(f"Enter the amount for {one_time_name}")
                one_time_date = get_date_input(f"Enter the date for {one_time_name}")
                current_one_time.append({'name': one_time_name, 'amount': one_time_amount, 'frequency': 'one-time',
                                         'dates': [one_time_date], 'expiry_date': None})
            if not get_yes_no_input("Add/Update another one-time expense?"):
                break

    print("\n--- Manage Savings Transfers ---")
    current_savings_transfers = budget_config['savings_transfers']
    if current_savings_transfers:
        print("Existing Savings Transfers:")
        for i, transfer in enumerate(current_savings_transfers):
            print(f"  {i + 1}. ${transfer['amount']:.2f} ({transfer['frequency']})")
        if get_yes_no_input("Do you want to modify or remove an existing savings transfer?"):
            while True:
                try:
                    choice = input("Enter the number of the transfer to modify/remove, or 'done' to finish: ").lower()
                    if choice == 'done': break
                    idx = int(choice) - 1
                    if 0 <= idx < len(current_savings_transfers):
                        selected_transfer = current_savings_transfers[idx]
                        if get_yes_no_input("Do you want to remove this savings transfer?"):
                            current_savings_transfers.pop(idx)
                            print("Savings transfer removed.")
                            break

                        selected_transfer['amount'] = get_float_input(
                            f"Enter new amount for transfer (current: ${selected_transfer['amount']:.2f})")
                        selected_transfer['frequency'] = get_frequency_input(
                            f"Enter new frequency for transfer (current: {selected_transfer['frequency']})")
                        if selected_transfer['frequency'] != "weekly":
                            if get_yes_no_input(
                                    f"Do you want to update specific dates for this transfer? (current: {[d.strftime('%Y-%m-%d') for d in selected_transfer['dates']]})"):
                                selected_transfer['dates'] = get_multiple_dates(
                                    "Enter new specific dates for this transfer")
                        else:
                            selected_transfer['dates'] = []
                        print("Savings transfer updated.")
                    else:
                        print("Invalid transfer number.")
                except ValueError:
                    print("Invalid input. Please enter a number or 'done'.")

    if get_yes_no_input("Do you want to add a new savings transfer?"):
        while True:
            savings_amount = get_float_input("Enter the amount you want to transfer to savings per period")
            savings_frequency = get_frequency_input("How often do you want to transfer to savings?")
            s_dates = []
            if savings_frequency == "one-time":
                s_dates.append(get_date_input("Enter the specific date for this savings transfer"))
            else:
                if get_yes_no_input("Do you have specific dates for savings transfers for the rest of the year?"):
                    s_dates = get_multiple_dates("Enter a savings transfer date")
                    if not s_dates:
                        print(
                            "Warning: For recurring savings transfers without specific dates, the program will estimate.")

            # Apply holiday adjustment to specific dates
            if s_dates:
                adjusted_s_dates = []
                for s_date in s_dates:
                    adjusted_date = s_date
                    while not is_business_day(adjusted_date, holidays):
                        adjusted_date -= timedelta(days=1)
                    adjusted_s_dates.append(adjusted_date)
                s_dates = adjusted_s_dates

            budget_config['savings_transfers'].append(
                {'amount': savings_amount, 'frequency': savings_frequency, 'dates': s_dates})
            if not get_yes_no_input("Add another savings transfer?"):
                break

    # New logic to pre-calculate all recurring dates
    # --- Financial Planning Calculations ---

    all_expenses_to_process = []
    for category_list in budget_config['expense_categories'].values():
        for item in category_list:
            if item['dates'] and item['frequency'] not in ['weekly', 'one-time']:
                new_dates = get_recurring_dates(item['dates'][0], end_of_year, item['frequency'], holidays)
                item['dates'] = [d for d in new_dates if item['expiry_date'] is None or d <= item['expiry_date']]
        all_expenses_to_process.extend(category_list)

    all_savings_to_process = []
    for transfer in budget_config['savings_transfers']:
        if transfer['dates'] and transfer['frequency'] not in ['weekly', 'one-time']:
            transfer['dates'] = get_recurring_dates(transfer['dates'][0], end_of_year, transfer['frequency'], holidays)
        all_savings_to_process.append(transfer)

    # New: Pre-calculate all pay dates
    all_income_paydates = budget_config['income']['dates']

    start_of_current_week = today - timedelta(days=today.weekday())

    weeks = []
    current_week_start = start_of_current_week
    while current_week_start <= end_of_year:
        weeks.append(current_week_start)
        current_week_start += timedelta(weeks=1)

    financial_data = []
    cumulative_saved_amount = budget_config['initial_savings_balance']
    running_balance = budget_config['initial_debit_balance']

    for week_start in weeks:
        week_end = week_start + timedelta(days=6)
        week_of_year = week_start.isocalendar()[1]

        weekly_income = 0.0
        weekly_expenses_breakdown = defaultdict(float)
        weekly_total_expenses = 0.0
        weekly_savings_transfer = 0.0

        # New: Use pre-calculated paydates to check for income
        for pay_date in all_income_paydates:
            if week_start <= pay_date <= week_end:
                weekly_income += budget_config['income']['amount']

        for item in all_expenses_to_process:
            amount = item['amount']
            frequency = item['frequency']
            item_dates = item['dates']
            item_name = item['name']
            expiry_date = item.get('expiry_date')

            should_apply_expense_this_week = False

            if expiry_date is not None and week_start > expiry_date:
                continue

            if frequency == 'weekly':
                should_apply_expense_this_week = True
            elif frequency in ['bi-weekly', 'monthly', 'quarterly', 'yearly', 'one-time']:
                if item_dates:
                    for expense_date in item_dates:
                        if week_start <= expense_date <= week_end:
                            should_apply_expense_this_week = True
                            break
                elif frequency == 'bi-weekly':
                    if (week_start - start_of_current_week).days // 7 % 2 == 0:
                        should_apply_expense_this_week = True
                elif frequency == 'monthly':
                    if week_start.month != (week_start - timedelta(days=7)).month or week_start.day <= 7:
                        should_apply_expense_this_week = True
                elif frequency == 'quarterly':
                    # Simplified check for quarterly, assumes first quarter is Jan-Mar
                    if week_start.month in [1, 4, 7, 10] and (week_start.day <= 7 or week_start.day >= 25):
                        should_apply_expense_this_week = True
                elif frequency == 'yearly':
                    if week_start.month == 1 and week_start.day <= 7:
                        should_apply_expense_this_week = True

            if should_apply_expense_this_week:
                # Determine the correct key for the CSV header
                if 'Groceries' in budget_config['expense_categories'] and item in budget_config['expense_categories'][
                    'Groceries']:
                    key_name = item_name
                elif 'Bills' in budget_config['expense_categories'] and item in budget_config['expense_categories'][
                    'Bills']:
                    key_name = f"Bill: {item_name}"
                elif 'Streaming Services' in budget_config['expense_categories'] and item in \
                        budget_config['expense_categories']['Streaming Services']:
                    key_name = f"Streaming: {item_name}"
                elif 'Misc Monthly' in budget_config['expense_categories'] and item in \
                        budget_config['expense_categories']['Misc Monthly']:
                    key_name = f"Misc Monthly: {item_name}"
                elif 'One-Time' in budget_config['expense_categories'] and item in budget_config['expense_categories'][
                    'One-Time']:
                    key_name = f"One-Time: {item_name}"
                else:
                    key_name = item_name

                weekly_expenses_breakdown[key_name] += amount
                weekly_total_expenses += amount

        for s_transfer in all_savings_to_process:
            s_amount = s_transfer['amount']
            s_frequency = s_transfer['frequency']
            s_dates = s_transfer['dates']

            should_apply_savings_this_week = False

            if s_frequency == 'weekly':
                should_apply_savings_this_week = True
            elif s_frequency in ['bi-weekly', 'monthly', 'one-time']:
                if s_dates:
                    for s_date in s_dates:
                        if week_start <= s_date <= week_end:
                            should_apply_savings_this_week = True
                            break
                elif s_frequency == 'bi-weekly':
                    if (week_start - start_of_current_week).days // 7 % 2 == 0:
                        should_apply_savings_this_week = True
                elif s_frequency == 'monthly':
                    if week_start.month != (week_start - timedelta(days=7)).month or week_start.day <= 7:
                        should_apply_savings_this_week = True

            if should_apply_savings_this_week:
                weekly_savings_transfer += s_amount

        running_balance += weekly_income - weekly_total_expenses - weekly_savings_transfer
        cumulative_saved_amount += weekly_savings_transfer

        financial_data.append({
            'Week of Year': week_of_year,
            'Week Start Date': week_start.strftime("%Y-%m-%d"),
            'Week End Date': week_end.strftime("%Y-%m-%d"),
            'Income Received': weekly_income,
            'Total Weekly Expenses': weekly_total_expenses,
            'Savings Transferred': weekly_savings_transfer,
            'Saved Amount at End of Week': cumulative_saved_amount,
            'Running Balance at End of Week': running_balance,
            **weekly_expenses_breakdown
        })

    # The issue was here. The code incorrectly tried to rebuild the budget_config from the all_expenses_to_process and all_savings_to_process.
    # By removing this block, we ensure that the budget_config is saved exactly as the user has configured it.

    save_budget_data(budget_config, budget_config_filename)

    output_filename = "budget_plan_rest_of_year.csv"
    if financial_data:
        all_keys = set()
        for row in financial_data:
            all_keys.update(row.keys())

        ordered_keys_initial = [
            'Week of Year',
            'Week Start Date',
            'Week End Date',
            'Income Received',
            'Total Weekly Expenses',
            'Savings Transferred',
            'Saved Amount at End of Week',
            'Running Balance at End of Week'
        ]

        other_keys = sorted([k for k in all_keys if k not in ordered_keys_initial])
        final_keys = ordered_keys_initial + other_keys

        with open(output_filename, 'w', newline='') as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=final_keys)
            dict_writer.writeheader()
            dict_writer.writerows(financial_data)
        print(f"\nBudget plan report generated as '{output_filename}'.")
    else:
        print("\nNo financial data to generate report. Please ensure you've entered income and expenses.")


if __name__ == "__main__":
    plan_budget_for_year()