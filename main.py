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
            value = input(prompt + ": ")
            if value == '':
                return None  # Return None for empty input
            float_value = float(value)
            if float_value < 0:
                print("Please enter a non-negative number.")
                continue
            return float_value
        except ValueError:
            print("Invalid input. Please enter a number.")


def get_frequency_input(prompt):
    """Helper function to get a valid frequency input."""
    while True:
        freq = input(
            prompt + " (weekly, bi-weekly (every 2 weeks), monthly, bi-monthly (every 2 months), quarterly, yearly, one-time): ").lower()
        if freq == '':
            return None  # Return None for empty input
        if freq in ["weekly", "bi-weekly", "monthly", "bi-monthly", "quarterly", "yearly", "one-time"]:
            return freq
        else:
            print(
                "Invalid frequency. Please choose from: weekly, bi-weekly, monthly, bi-monthly, quarterly, yearly, one-time.")


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

        # --- Calculate 15th of the month ---
        target_15th = datetime(year, month, 15).date()
        if start_date <= target_15th <= end_date:
            adjusted_date = target_15th
            while not is_business_day(adjusted_date, holidays_set):
                adjusted_date -= timedelta(days=1)
            if adjusted_date >= start_date:
                dates.append(adjusted_date)

        # --- Calculate last day of the month ---
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


def calculate_bi_monthly_dates_every_two_months(start_date, end_date, holidays_set):
    """
    Generates a list of recurring dates every two months, adjusting for weekends/holidays.
    """
    dates = []
    current_date = start_date

    while current_date <= end_date:
        adjusted_date = current_date
        while not is_business_day(adjusted_date, holidays_set):
            adjusted_date -= timedelta(days=1)
        dates.append(adjusted_date)

        # Move to two months from now
        new_month = current_date.month + 2
        new_year = current_date.year
        if new_month > 12:
            new_month -= 12
            new_year += 1
        day = min(current_date.day, calendar.monthrange(new_year, new_month)[1])
        current_date = datetime(new_year, new_month, day).date()

    return [d for d in dates if d >= datetime.now().date()]


def get_recurring_dates(start_date, end_date, frequency, holidays_set=None):
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
        elif frequency == 'bi-monthly':
            new_month = current_date.month + 2
            new_year = current_date.year
            if new_month > 12:
                new_month -= 12
                new_year += 1
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
                        # Ensure each item has a category field when loaded
                        item.setdefault('category', category)
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


# --- Expense Management Functions ---

def manage_groceries(budget_config):
    print("\n--- Manage Your Groceries ---")
    if budget_config['expense_categories']['Groceries']:
        current_groceries = budget_config['expense_categories']['Groceries'][0]['amount']
        print(f"Current typical weekly grocery expense: ${current_groceries:.2f}")
        if get_yes_no_input("Do you want to update your weekly grocery expense?"):
            new_amount = get_float_input("Enter your new typical weekly grocery expense")
            if new_amount is not None:
                budget_config['expense_categories']['Groceries'][0]['amount'] = new_amount
    elif get_yes_no_input("Do you have a regular grocery expense?"):
        groceries_amount = get_float_input("Enter your typical weekly grocery expense")
        if groceries_amount is not None:
            budget_config['expense_categories']['Groceries'].append(
                {'name': 'Groceries', 'amount': groceries_amount, 'frequency': 'weekly', 'dates': [],
                 'expiry_date': None,
                 'category': 'Groceries'})


def manage_bills(budget_config, holidays):
    print("\n--- Manage Your Bills ---")
    current_bills = budget_config['expense_categories']['Bills']
    if current_bills:
        if get_yes_no_input("Do you want to modify or remove an existing bill?"):
            while True:
                print("Existing Bills:")
                for i, bill in enumerate(current_bills):
                    expiry_info = f", Expires: {bill['expiry_date'].strftime('%Y-%m-%d')}" if bill[
                        'expiry_date'] else ", No expiry"
                    print(f"  {i + 1}. {bill['name']}: ${bill['amount']:.2f} ({bill['frequency']}{expiry_info})")

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
                            if not current_bills:
                                print("No more bills left to modify.")
                                break
                            continue

                        new_name = input(
                            f"Enter new name for {selected_bill['name']} (or press Enter to keep '{selected_bill['name']}'): ")
                        if new_name:
                            selected_bill['name'] = new_name

                        new_amount = get_float_input(
                            f"Enter new amount for {selected_bill['name']} (or press Enter to keep '${selected_bill['amount']:.2f}'): ")
                        if new_amount is not None:
                            selected_bill['amount'] = new_amount

                        # New logic for updating schedule
                        if get_yes_no_input(
                                f"Do you want to update the payment schedule for {selected_bill['name']}? (Current: {selected_bill['frequency']} on {[d.strftime('%Y-%m-%d') for d in selected_bill['dates']] if selected_bill['dates'] else 'no specific dates'})"):
                            if get_yes_no_input(
                                    "Do you want to set a periodic schedule? (e.g., weekly, monthly, bi-monthly)"):
                                new_freq = get_frequency_input(f"How often do you pay {selected_bill['name']}?")
                                if new_freq:
                                    selected_bill['frequency'] = new_freq
                                    selected_bill['dates'] = []  # Reset dates for new periodic schedule
                                    if new_freq == 'bi-monthly':
                                        start_date = get_date_input(
                                            "Enter the new start date for this bi-monthly payment")
                                        selected_bill['dates'] = calculate_bi_monthly_dates_every_two_months(start_date,
                                                                                                             datetime(
                                                                                                                 datetime.now().year,
                                                                                                                 12,
                                                                                                                 31).date(),
                                                                                                             holidays)
                                    elif new_freq == "one-time":
                                        selected_bill['dates'].append(get_date_input(
                                            f"Enter the specific date for this one-time {selected_bill['name']} payment"))
                                    else:
                                        start_date = get_date_input(
                                            "Enter the new start date for this payment schedule")
                                        selected_bill['dates'] = get_recurring_dates(start_date,
                                                                                     datetime(datetime.now().year, 12,
                                                                                              31).date(),
                                                                                     selected_bill['frequency'],
                                                                                     holidays)
                            else:  # Manual dates
                                print("You've chosen to enter specific dates manually.")
                                new_dates = get_multiple_dates(
                                    f"Enter new specific payment dates for {selected_bill['name']}")
                                if new_dates:
                                    selected_bill['frequency'] = "manual"
                                    selected_bill['dates'] = new_dates
                                    print("Dates updated.")
                                else:
                                    print("No dates were entered. Keeping previous dates.")

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
            bill_expiry_date = None
            if get_yes_no_input(f"Does {bill_name} have an expiry date?"):
                bill_expiry_date = get_date_input(f"Enter the expiry date for {bill_name}")

            bill_frequency = None
            bill_dates = []

            if get_yes_no_input("Do you want to set a periodic schedule? (e.g., weekly, monthly, bi-monthly)"):
                bill_frequency = get_frequency_input(f"How often do you pay {bill_name}?")
                if bill_frequency == 'bi-monthly':
                    start_date = get_date_input("Enter the start date for this bi-monthly payment")
                    bill_dates = calculate_bi_monthly_dates_every_two_months(start_date,
                                                                             datetime(datetime.now().year, 12,
                                                                                      31).date(), holidays)
                elif bill_frequency == "one-time":
                    bill_dates.append(get_date_input(f"Enter the specific date for this one-time {bill_name} payment"))
                else:  # Handles weekly, bi-weekly, monthly, etc.
                    start_date = get_date_input("Enter the start date for this payment schedule")
                    bill_dates = get_recurring_dates(start_date, datetime(datetime.now().year, 12, 31).date(),
                                                     bill_frequency, holidays)
            else:
                print("You've chosen to enter specific dates manually.")
                bill_frequency = "manual"
                bill_dates = get_multiple_dates(f"Enter a specific payment date for {bill_name}")

            if bill_dates and bill_frequency not in ["weekly", "one-time", "bi-monthly"]:
                adjusted_bill_dates = []
                for b_date in bill_dates:
                    adjusted_date = b_date
                    while not is_business_day(adjusted_date, holidays):
                        adjusted_date -= timedelta(days=1)
                    adjusted_bill_dates.append(adjusted_date)
                bill_dates = adjusted_bill_dates

            current_bills.append({
                'name': bill_name,
                'amount': bill_amount,
                'frequency': bill_frequency,
                'dates': bill_dates,
                'expiry_date': bill_expiry_date,
                'category': 'Bills'
            })
            if not get_yes_no_input("Add another bill?"):
                break


def manage_streaming(budget_config, holidays):
    print("\n--- Manage Streaming Services ---")
    current_streaming = budget_config['expense_categories']['Streaming Services']
    if current_streaming:
        if get_yes_no_input("Do you want to modify or remove an existing streaming service?"):
            while True:
                print("Existing Streaming Services:")
                for i, service in enumerate(current_streaming):
                    expiry_info = f", Expires: {service['expiry_date'].strftime('%Y-%m-%d')}" if service[
                        'expiry_date'] else ", No expiry"
                    print(
                        f"  {i + 1}. {service['name']}: ${service['amount']:.2f} ({service['frequency']}{expiry_info})")
                try:
                    choice = input("Enter the number of the service to modify/remove, or 'done' to finish: ").lower()
                    if choice == 'done': break
                    idx = int(choice) - 1
                    if 0 <= idx < len(current_streaming):
                        selected_service = current_streaming[idx]
                        if get_yes_no_input(f"Do you want to remove {selected_service['name']}?"):
                            current_streaming.pop(idx)
                            print(f"{selected_service['name']} removed.")
                            if not current_streaming:
                                print("No more streaming services left to modify.")
                                break
                            continue

                        new_name = input(
                            f"Enter new name for {selected_service['name']} (or press Enter to keep '{selected_service['name']}'): ")
                        if new_name:
                            selected_service['name'] = new_name

                        new_amount = get_float_input(
                            f"Enter new monthly amount for {selected_service['name']} (or press Enter to keep '${selected_service['amount']:.2f}'): ")
                        if new_amount is not None:
                            selected_service['amount'] = new_amount

                        if get_yes_no_input(
                                f"Do you want to update the payment schedule for {selected_service['name']}? (Current: {selected_service['frequency']} on {[d.strftime('%Y-%m-%d') for d in selected_service['dates']] if selected_service['dates'] else 'no specific dates'})"):
                            if get_yes_no_input("Do you want to set a periodic schedule?"):
                                new_freq = get_frequency_input(f"How often do you pay {selected_service['name']}?")
                                if new_freq:
                                    selected_service['frequency'] = new_freq
                                    selected_service['dates'] = []
                                    if new_freq == 'bi-monthly':
                                        start_date = get_date_input(
                                            "Enter the new start date for this bi-monthly payment")
                                        selected_service['dates'] = calculate_bi_monthly_dates_every_two_months(
                                            start_date, datetime(datetime.now().year, 12, 31).date(), holidays)
                                    elif new_freq == "one-time":
                                        selected_service['dates'].append(get_date_input(
                                            f"Enter the specific date for this one-time {selected_service['name']} payment"))
                                    else:
                                        start_date = get_date_input(
                                            "Enter the new start date for this payment schedule")
                                        selected_service['dates'] = get_recurring_dates(start_date,
                                                                                        datetime(datetime.now().year,
                                                                                                 12, 31).date(),
                                                                                        selected_service['frequency'],
                                                                                        holidays)
                            else:  # Manual dates
                                print("You've chosen to enter specific dates manually.")
                                new_dates = get_multiple_dates(
                                    f"Enter new specific payment dates for {selected_service['name']}")
                                if new_dates:
                                    selected_service['frequency'] = "manual"
                                    selected_service['dates'] = new_dates
                                    print("Dates updated.")
                                else:
                                    print("No dates were entered. Keeping previous dates.")

                        if get_yes_no_input(
                                f"Do you want to update the expiry date for {selected_service['name']}? (current: {selected_service['expiry_date'].strftime('%Y-%m-%d') if selected_service['expiry_date'] else 'None'})"):
                            if get_yes_no_input("Does it now have an expiry date?"):
                                selected_service['expiry_date'] = get_date_input(
                                    f"Enter the new expiry date for {selected_service['name']}")
                            else:
                                selected_service['expiry_date'] = None

                        print(f"{selected_service['name']} updated.")
                    else:
                        print("Invalid service number.")
                except ValueError:
                    print("Invalid input. Please enter a number or 'done'.")
    if get_yes_no_input("Do you want to add a new streaming service?"):
        while True:
            service_name = input(
                "Enter the name of the streaming service (e.g., Netflix, Spotify) or 'done' to finish: ").lower()
            if service_name == 'done': break
            service_amount = get_float_input(f"Enter the monthly amount for {service_name}")
            service_expiry_date = None
            if get_yes_no_input(f"Does {service_name} have an expiry date?"):
                service_expiry_date = get_date_input(f"Enter the expiry date for {service_name}")

            service_frequency = None
            service_dates = []

            if get_yes_no_input("Do you want to set a periodic schedule?"):
                service_frequency = get_frequency_input(f"How often do you pay {service_name}?")
                if service_frequency == 'bi-monthly':
                    start_date = get_date_input("Enter the start date for this bi-monthly payment")
                    service_dates = calculate_bi_monthly_dates_every_two_months(start_date,
                                                                                datetime(datetime.now().year, 12,
                                                                                         31).date(), holidays)
                elif service_frequency == "one-time":
                    service_dates.append(
                        get_date_input(f"Enter the specific date for this one-time {service_name} payment"))
                else:  # Handles weekly, bi-weekly, monthly, etc.
                    start_date = get_date_input("Enter the start date for this payment schedule")
                    service_dates = get_recurring_dates(start_date, datetime(datetime.now().year, 12, 31).date(),
                                                        service_frequency, holidays)
            else:
                print("You've chosen to enter specific dates manually.")
                service_frequency = "manual"
                service_dates = get_multiple_dates(f"Enter a specific pay date for {service_name}")

            current_streaming.append(
                {'name': service_name, 'amount': service_amount, 'frequency': service_frequency, 'dates': service_dates,
                 'expiry_date': service_expiry_date, 'category': 'Streaming Services'})
            if not get_yes_no_input("Add another streaming service?"):
                break


def manage_misc_monthly(budget_config, holidays):
    """
    Manages miscellaneous monthly expenses, now with holiday adjustments for bi-monthly payments.
    """
    print("\n--- Manage Miscellaneous Monthly Expenses ---")
    current_misc = budget_config['expense_categories']['Misc Monthly']
    if current_misc:
        if get_yes_no_input("Do you want to modify or remove an existing miscellaneous monthly expense?"):
            while True:
                print("Existing Miscellaneous Monthly Expenses:")
                for i, misc in enumerate(current_misc):
                    expiry_info = f", Expires: {misc['expiry_date'].strftime('%Y-%m-%d')}" if misc[
                        'expiry_date'] else ", No expiry"
                    print(f"  {i + 1}. {misc['name']}: ${misc['amount']:.2f} ({misc['frequency']}{expiry_info})")
                try:
                    choice = input("Enter the number of the expense to modify/remove, or 'done' to finish: ").lower()
                    if choice == 'done': break
                    idx = int(choice) - 1
                    if 0 <= idx < len(current_misc):
                        selected_misc = current_misc[idx]
                        if get_yes_no_input(f"Do you want to remove {selected_misc['name']}?"):
                            current_misc.pop(idx)
                            print(f"{selected_misc['name']} removed.")
                            if not current_misc:
                                print("No more miscellaneous monthly expenses left to modify.")
                                break
                            continue

                        new_name = input(
                            f"Enter new name for {selected_misc['name']} (or press Enter to keep '{selected_misc['name']}'): ")
                        if new_name:
                            selected_misc['name'] = new_name

                        new_amount = get_float_input(
                            f"Enter new monthly amount for {selected_misc['name']} (or press Enter to keep '${selected_misc['amount']:.2f}'): ")
                        if new_amount is not None:
                            selected_misc['amount'] = new_amount

                        if get_yes_no_input(
                                f"Do you want to update the payment schedule for {selected_misc['name']}? (Current: {selected_misc['frequency']} on {[d.strftime('%Y-%m-%d') for d in selected_misc['dates']] if selected_misc['dates'] else 'no specific dates'})"):
                            if get_yes_no_input("Do you want to set a periodic schedule?"):
                                new_freq = get_frequency_input(f"How often do you pay {selected_misc['name']}?")
                                if new_freq:
                                    selected_misc['frequency'] = new_freq
                                    selected_misc['dates'] = []
                                    if new_freq == 'bi-monthly':
                                        start_date = get_date_input(
                                            "Enter the new start date for this bi-monthly payment")
                                        selected_misc['dates'] = calculate_bi_monthly_dates_every_two_months(start_date,
                                                                                                             datetime(
                                                                                                                 datetime.now().year,
                                                                                                                 12,
                                                                                                                 31).date(),
                                                                                                             holidays)
                                    elif new_freq == "one-time":
                                        selected_misc['dates'].append(get_date_input(
                                            f"Enter the specific date for this one-time {selected_misc['name']} payment"))
                                    else:
                                        start_date = get_date_input(
                                            "Enter the new start date for this payment schedule")
                                        selected_misc['dates'] = get_recurring_dates(start_date,
                                                                                     datetime(datetime.now().year, 12,
                                                                                              31).date(),
                                                                                     selected_misc['frequency'],
                                                                                     holidays)
                            else:  # Manual dates
                                print("You've chosen to enter specific dates manually.")
                                new_dates = get_multiple_dates(
                                    f"Enter new specific payment dates for {selected_misc['name']}")
                                if new_dates:
                                    selected_misc['frequency'] = "manual"
                                    selected_misc['dates'] = new_dates
                                    print("Dates updated.")
                                else:
                                    print("No dates were entered. Keeping previous dates.")

                        if get_yes_no_input(
                                f"Do you want to update the expiry date for {selected_misc['name']}? (current: {selected_misc['expiry_date'].strftime('%Y-%m-%d') if selected_misc['expiry_date'] else 'None'})"):
                            if get_yes_no_input("Does it now have an expiry date?"):
                                selected_misc['expiry_date'] = get_date_input(
                                    f"Enter the new expiry date for {selected_misc['name']}")
                            else:
                                selected_misc['expiry_date'] = None

                        print(f"{selected_misc['name']} updated.")
                    else:
                        print("Invalid expense number.")
                except ValueError:
                    print("Invalid input. Please enter a number or 'done'.")

    if get_yes_no_input("Do you want to add a new miscellaneous monthly expense?"):
        while True:
            misc_name = input("Enter the name of the miscellaneous expense or 'done' to finish: ").lower()
            if misc_name == 'done': break
            misc_amount = get_float_input(f"Enter the amount for {misc_name}")
            misc_expiry_date = None
            if get_yes_no_input(f"Does {misc_name} have an expiry date?"):
                misc_expiry_date = get_date_input(f"Enter the expiry date for {misc_name}")

            misc_frequency = None
            misc_dates = []

            if get_yes_no_input("Do you want to set a periodic schedule?"):
                misc_frequency = get_frequency_input(f"How often do you pay {misc_name}?")
                if misc_frequency == 'bi-monthly':
                    start_date = get_date_input("Enter the start date for this bi-monthly payment")
                    misc_dates = calculate_bi_monthly_dates_every_two_months(start_date,
                                                                             datetime(datetime.now().year, 12,
                                                                                      31).date(), holidays)
                elif misc_frequency == "one-time":
                    misc_dates.append(get_date_input(f"Enter the specific date for this one-time {misc_name} payment"))
                else:  # Handles weekly, bi-weekly, monthly, etc.
                    start_date = get_date_input("Enter the start date for this payment schedule")
                    misc_dates = get_recurring_dates(start_date, datetime(datetime.now().year, 12, 31).date(),
                                                     misc_frequency, holidays)
            else:
                print("You've chosen to enter specific dates manually.")
                misc_frequency = "manual"
                misc_dates = get_multiple_dates(f"Enter a specific pay date for {misc_name}")

            current_misc.append(
                {'name': misc_name, 'amount': misc_amount, 'frequency': misc_frequency, 'dates': misc_dates,
                 'expiry_date': misc_expiry_date, 'category': 'Misc Monthly'})
            if not get_yes_no_input("Add another miscellaneous monthly expense?"):
                break


def manage_one_time(budget_config):
    print("\n--- Manage One-Time Expenses ---")
    current_one_time = budget_config['expense_categories']['One-Time']
    if current_one_time:
        if get_yes_no_input("Do you want to modify or remove an existing one-time expense?"):
            while True:
                print("Existing One-Time Expenses:")
                for i, one_time in enumerate(current_one_time):
                    print(
                        f"  {i + 1}. {one_time['name']}: ${one_time['amount']:.2f} on {one_time['dates'][0].strftime('%Y-%m-%d')}")
                try:
                    choice = input("Enter the number of the expense to modify/remove, or 'done' to finish: ").lower()
                    if choice == 'done': break
                    idx = int(choice) - 1
                    if 0 <= idx < len(current_one_time):
                        selected_one_time = current_one_time[idx]
                        if get_yes_no_input(f"Do you want to remove {selected_one_time['name']}?"):
                            current_one_time.pop(idx)
                            print(f"{selected_one_time['name']} removed.")
                            if not current_one_time:
                                print("No more one-time expenses left to modify.")
                                break
                            continue

                        new_name = input(
                            f"Enter new name for {selected_one_time['name']} (or press Enter to keep '{selected_one_time['name']}'): ")
                        if new_name:
                            selected_one_time['name'] = new_name

                        new_amount = get_float_input(
                            f"Enter new amount for {selected_one_time['name']} (or press Enter to keep '${selected_one_time['amount']:.2f}'): ")
                        if new_amount is not None:
                            selected_one_time['amount'] = new_amount

                        new_date_str = input(
                            f"Enter the new date for {selected_one_time['name']} (or press Enter to keep '{selected_one_time['dates'][0].strftime('%Y-%m-%d')}'): ")
                        if new_date_str:
                            try:
                                selected_one_time['dates'][0] = datetime.strptime(new_date_str, "%Y-%m-%d").date()
                            except ValueError:
                                print("Invalid date format. Keeping original date.")

                        print(f"{selected_one_time['name']} updated.")
                    else:
                        print("Invalid expense number.")
                except ValueError:
                    print("Invalid input. Please enter a number or 'done'.")

    if get_yes_no_input("Do you want to add a new one-time expense?"):
        while True:
            one_time_name = input("Enter the name of the one-time expense or 'done' to finish: ").lower()
            if one_time_name == 'done': break
            one_time_amount = get_float_input(f"Enter the amount for {one_time_name}")
            one_time_date = get_date_input(f"Enter the date for {one_time_name}")
            current_one_time.append({'name': one_time_name, 'amount': one_time_amount, 'frequency': 'one-time',
                                     'dates': [one_time_date], 'expiry_date': None,
                                     'category': 'One-Time'})
            if not get_yes_no_input("Add another one-time expense?"):
                break


def manage_savings(budget_config, holidays):
    print("\n--- Manage Savings Transfers ---")
    current_savings_transfers = budget_config['savings_transfers']
    if current_savings_transfers:
        if get_yes_no_input("Do you want to modify or remove an existing savings transfer?"):
            while True:
                print("Existing Savings Transfers:")
                for i, transfer in enumerate(current_savings_transfers):
                    print(f"  {i + 1}. ${transfer['amount']:.2f} ({transfer['frequency']})")
                try:
                    choice = input("Enter the number of the transfer to modify/remove, or 'done' to finish: ").lower()
                    if choice == 'done': break
                    idx = int(choice) - 1
                    if 0 <= idx < len(current_savings_transfers):
                        selected_transfer = current_savings_transfers[idx]
                        if get_yes_no_input("Do you want to remove this savings transfer?"):
                            current_savings_transfers.pop(idx)
                            print("Savings transfer removed.")
                            if not current_savings_transfers:
                                print("No more savings transfers left to modify.")
                                break
                            continue

                        new_amount = get_float_input(
                            f"Enter new amount for transfer (or press Enter to keep '${selected_transfer['amount']:.2f}'): ")
                        if new_amount is not None:
                            selected_transfer['amount'] = new_amount

                        if get_yes_no_input(
                                f"Do you want to update the payment schedule for this transfer? (Current: {selected_transfer['frequency']} on {[d.strftime('%Y-%m-%d') for d in selected_transfer['dates']] if selected_transfer['dates'] else 'no specific dates'})"):
                            if get_yes_no_input("Do you want to set a periodic schedule?"):
                                new_freq = get_frequency_input("How often do you want to transfer to savings?")
                                if new_freq:
                                    selected_transfer['frequency'] = new_freq
                                    selected_transfer['dates'] = []
                                    if new_freq == 'bi-monthly':
                                        start_date = get_date_input(
                                            "Enter the new start date for this bi-monthly transfer")
                                        selected_transfer['dates'] = calculate_bi_monthly_dates_every_two_months(
                                            start_date, datetime(datetime.now().year, 12, 31).date(), holidays)
                                    elif new_freq == "one-time":
                                        selected_transfer['dates'].append(
                                            get_date_input(f"Enter the specific date for this one-time transfer"))
                                    else:
                                        start_date = get_date_input(
                                            "Enter the new start date for this transfer schedule")
                                        selected_transfer['dates'] = get_recurring_dates(start_date,
                                                                                         datetime(datetime.now().year,
                                                                                                  12, 31).date(),
                                                                                         new_freq, holidays)
                            else:  # Manual dates
                                print("You've chosen to enter specific dates manually.")
                                new_dates = get_multiple_dates("Enter new specific dates for this transfer")
                                if new_dates:
                                    selected_transfer['frequency'] = "manual"
                                    selected_transfer['dates'] = new_dates
                                    print("Dates updated.")
                                else:
                                    print("No dates were entered. Keeping previous dates.")
                        print("Savings transfer updated.")
                    else:
                        print("Invalid transfer number.")
                except ValueError:
                    print("Invalid input. Please enter a number or 'done'.")
    if get_yes_no_input("Do you want to add a new savings transfer?"):
        while True:
            savings_amount = get_float_input("Enter the amount you want to transfer to savings per period")

            savings_frequency = None
            s_dates = []

            if get_yes_no_input("Do you want to set a periodic schedule?"):
                savings_frequency = get_frequency_input("How often do you want to transfer to savings?")
                if savings_frequency == 'bi-monthly':
                    start_date = get_date_input("Enter the start date for this bi-monthly transfer")
                    s_dates = calculate_bi_monthly_dates_every_two_months(start_date,
                                                                          datetime(datetime.now().year, 12, 31).date(),
                                                                          holidays)
                elif savings_frequency == "one-time":
                    s_dates.append(get_date_input("Enter the specific date for this savings transfer"))
                else:  # Handles weekly, bi-weekly, monthly, etc.
                    start_date = get_date_input("Enter the start date for this transfer schedule")
                    s_dates = get_recurring_dates(start_date, datetime(datetime.now().year, 12, 31).date(),
                                                  savings_frequency, holidays)
            else:
                print("You've chosen to enter specific dates manually.")
                savings_frequency = "manual"
                s_dates = get_multiple_dates("Enter a savings transfer date")

            current_savings_transfers.append(
                {'amount': savings_amount, 'frequency': savings_frequency, 'dates': s_dates})
            if not get_yes_no_input("Add another savings transfer?"):
                break


def manage_income(budget_config, end_of_year, holidays):
    print("\n--- Income Information ---")
    current_income_amount = budget_config['income']['amount']
    current_income_freq = budget_config['income']['frequency']

    if current_income_amount > 0:
        print(f"Current income: ${current_income_amount:.2f} ({current_income_freq})")
        if get_yes_no_input("Do you want to update your income information?"):
            new_amount = get_float_input(
                f"Enter your new income amount after taxes (or press Enter to keep '${current_income_amount:.2f}'): ")
            if new_amount is not None:
                budget_config['income']['amount'] = new_amount

            new_freq = get_frequency_input(
                f"How often do you receive this income? (or press Enter to keep '{current_income_freq}'): ")
            if new_freq is not None:
                budget_config['income']['frequency'] = new_freq

            if new_freq == 'bi-monthly':
                if get_yes_no_input("Do you want to update the start date for this bi-monthly income?"):
                    start_date = get_date_input("Enter the start date for this bi-monthly income")
                    budget_config['income']['dates'] = calculate_bi_monthly_dates_every_two_months(start_date,
                                                                                                   end_of_year,
                                                                                                   holidays)
            elif new_freq == 'twice-monthly':
                budget_config['income']['dates'] = calculate_twice_monthly_dates(datetime.now().date(), end_of_year,
                                                                                 holidays)
            elif get_yes_no_input("Do you want to update the date of your next upcoming paycheck?"):
                budget_config['income']['dates'] = [get_date_input("Enter the date of your next upcoming paycheck")]
    else:
        budget_config['income']['amount'] = get_float_input("Enter your income amount after taxes")
        budget_config['income']['frequency'] = get_frequency_input("How often do you receive this income?")
        if budget_config['income']['frequency'] == 'bi-monthly':
            start_date = get_date_input("Enter the start date for this bi-monthly income")
            budget_config['income']['dates'] = calculate_bi_monthly_dates_every_two_months(start_date, end_of_year,
                                                                                           holidays)
        elif budget_config['income']['frequency'] == 'twice-monthly':
            budget_config['income']['dates'] = calculate_twice_monthly_dates(datetime.now().date(), end_of_year,
                                                                             holidays)
        else:
            budget_config['income']['dates'] = [get_date_input("Enter the date of your next upcoming paycheck")]

    if budget_config['income']['frequency'] != 'one-time' and budget_config['income']['frequency'] not in ['bi-monthly',
                                                                                                           'twice-monthly'] and \
            budget_config['income']['dates']:
        budget_config['income']['dates'] = get_recurring_dates(budget_config['income']['dates'][0], end_of_year,
                                                               budget_config['income']['frequency'], holidays)

    if not budget_config['income']['dates']:
        print("Warning: No pay dates were generated for the rest of the year. Please check your input.")
    else:
        print("\nCalculated Pay Dates for the rest of the year (adjusted for weekends/holidays):")
        for date in budget_config['income']['dates']:
            print(f"- {date.strftime('%Y-%m-%d')}")


# --- Modification Menu ---

def modify_budget_menu(budget_config, holidays, end_of_year):
    while get_yes_no_input("\nDo you want to modify any of your inputs?"):
        print("\n--- Select a Category to Modify ---")
        print("1. Income")
        print("2. Groceries")
        print("3. Bills")
        print("4. Streaming Services")
        print("5. Miscellaneous Monthly Expenses")
        print("6. One-Time Expenses")
        print("7. Savings Transfers")
        print("8. Finish and generate report")

        choice = input("Enter your choice (1-8): ")

        if choice == '1':
            manage_income(budget_config, end_of_year, holidays)
        elif choice == '2':
            manage_groceries(budget_config)
        elif choice == '3':
            manage_bills(budget_config, holidays)
        elif choice == '4':
            manage_streaming(budget_config, holidays)
        elif choice == '5':
            # FIX: Pass holidays to manage_misc_monthly
            manage_misc_monthly(budget_config, holidays)
        elif choice == '6':
            manage_one_time(budget_config)
        elif choice == '7':
            manage_savings(budget_config, holidays)
        elif choice == '8':
            print("Finishing modifications.")
            break
        else:
            print("Invalid choice. Please enter a number between 1 and 8.")


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

    manage_income(budget_config, end_of_year, holidays)
    manage_groceries(budget_config)
    manage_bills(budget_config, holidays)
    manage_streaming(budget_config, holidays)
    # FIX: Pass holidays to manage_misc_monthly
    manage_misc_monthly(budget_config, holidays)
    manage_one_time(budget_config)
    manage_savings(budget_config, holidays)

    # New modification menu after initial setup
    modify_budget_menu(budget_config, holidays, end_of_year)

    # New logic to pre-calculate all recurring dates
    all_expenses_to_process = []
    for category_list in budget_config['expense_categories'].values():
        for item in category_list:
            if item['frequency'] not in ['weekly', 'one-time', 'bi-monthly', 'manual'] and item['dates']:
                new_dates = get_recurring_dates(item['dates'][0], end_of_year, item['frequency'], holidays)
                item['dates'] = [d for d in new_dates if item['expiry_date'] is None or d <= item['expiry_date']]
        all_expenses_to_process.extend(category_list)

    all_savings_to_process = []
    for transfer in budget_config['savings_transfers']:
        if transfer['frequency'] not in ['weekly', 'one-time', 'bi-monthly', 'manual'] and transfer['dates']:
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
            category = item.get('category')

            should_apply_expense_this_week = False

            if expiry_date is not None and week_start > expiry_date:
                continue

            if frequency == 'weekly':
                should_apply_expense_this_week = True
            elif frequency in ['bi-weekly', 'monthly', 'bi-monthly', 'quarterly', 'yearly', 'one-time', 'manual']:
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
                    if week_start.month in [1, 4, 7, 10] and (week_start.day <= 7 or week_start.day >= 25):
                        should_apply_expense_this_week = True
                elif frequency == 'yearly':
                    if week_start.month == 1 and week_start.day <= 7:
                        should_apply_expense_this_week = True
                elif frequency == 'bi-monthly':
                    if (week_start.month - today.month) % 2 == 0 and week_start.day <= 7:
                        should_apply_expense_this_week = True

            if should_apply_expense_this_week:
                if category == 'Bills':
                    key_name = f"Bill: {item_name}"
                elif category == 'Streaming Services':
                    key_name = f"Streaming: {item_name}"
                elif category == 'Misc Monthly':
                    key_name = f"Misc Monthly: {item_name}"
                elif category == 'One-Time':
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
            elif s_frequency in ['bi-weekly', 'monthly', 'one-time', 'bi-monthly', 'manual']:
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

    new_expense_categories = {
        'Groceries': [],
        'Bills': [],
        'Streaming Services': [],
        'Misc Monthly': [],
        'One-Time': []
    }

    for item in all_expenses_to_process:
        category = item.get('category')
        if category in new_expense_categories:
            new_expense_categories[category].append(item)

    budget_config['expense_categories'] = new_expense_categories
    budget_config['savings_transfers'] = all_savings_to_process

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