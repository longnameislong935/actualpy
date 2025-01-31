import csv
import datetime
import decimal
import pathlib
import os
import argparse

from actual import Actual
from actual.exceptions import UnknownFileId, ActualError
from actual.queries import get_or_create_account, reconcile_transaction

# --- Configuration (Environment Variables) ---
ACTUAL_BUDGET_URL = os.environ.get("ACTUAL_BUDGET_URL")
ACTUAL_BUDGET_PASSWORD = os.environ.get("ACTUAL_BUDGET_PASSWORD")
CSV_FILE_PATH = os.environ.get("CSV_FILE_PATH")
BUDGET_NAME = os.environ.get("BUDGET_NAME") or "CSV Import"
ACCOUNT_NAME_DEFAULT = os.environ.get("ACCOUNT_NAME_DEFAULT")
base_url="https://budget.local.boxxynet.com"

# --- Helper Functions ---

def load_csv_data(file: pathlib.Path) -> list[dict]:
    data = []
    with open(file, encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            try:
                # *** KEY CHANGE: Map columns by index (ADJUST THESE TO YOUR CSV) ***
                #column 0 is the first column in the file
                date_str = row[1]
                amount_str = row[7]
                payee = row[4]
                category = row[6]
                notes = row[11] if len(row) > 4 else ""

                amount = decimal.Decimal(amount_str)
                date = datetime.datetime.strptime(date_str, "%d-%m-%Y").date()  # DD-MM-YYYY format

                data.append({
                    "Account": ACCOUNT_NAME_DEFAULT,  # Default account
                    "Payee": payee,
                    "Notes": notes,
                    "Category": category,
                    "Cleared": False,
                    "Date": date,
                    "Amount": amount,
                })

            except (ValueError, IndexError) as e:
                print(f"Error processing row: {row}. Skipping. Error: {e}")
                continue

    return data


def main():
    file = pathlib.Path(CSV_FILE_PATH)

    if not ACTUAL_BUDGET_PASSWORD:
        raise ValueError("ACTUAL_BUDGET_PASSWORD environment variable must be set.")
    if not CSV_FILE_PATH:
        raise ValueError("CSV_FILE_PATH environment variable must be set.")
    if not ACCOUNT_NAME_DEFAULT:
        raise ValueError("ACCOUNT_NAME_DEFAULT environment variable must be set.")

    # *** URL Configuration using actual.ini ***
    # 1. Create actual.ini in your home directory (or .actualrc)
    # 2. Add the following lines, replacing with your URL:
    #    [actual]
    #    url = https://your_actual_budget_url  <- Replace with your URL

    try:
        with Actual(
            base_url=ACTUAL_BUDGET_URL,
            password=ACTUAL_BUDGET_PASSWORD
        ) as actual:
            try:
                actual.set_file(BUDGET_NAME)
                actual.download_budget()
            except UnknownFileId:
                actual.create_budget(BUDGET_NAME)
                actual.upload_budget()

            added_transactions = []
            for row in load_csv_data(file):
                account_name, payee, notes, category, cleared, date, amount = (
                    row["Account"],
                    row["Payee"],
                    row["Notes"],
                    row["Category"],
                    row["Cleared"],
                    row["Date"],
                    row["Amount"],
                )

                account = get_or_create_account(actual.session, account_name)
                try:
                    t = reconcile_transaction(
                        actual.session,
                        date,
                        account,
                        payee,
                        notes,
                        category,
                        amount,
                        cleared=cleared,
                        already_matched=added_transactions,
                    )
                    added_transactions.append(t)
                    if t.changed():
                        print(f"Added or modified {t}")
                except ActualError as e:  # Corrected exception catch
                    print(f"Error reconciling transaction: {row}. Error: {e}")
                    continue

            actual.commit()
            print("Transactions imported successfully!")

    except Exception as e:
        print(f"A general error occurred: {e}")


if __name__ == "__main__":
    main()
