import csv
import datetime
import decimal
import pathlib
import os
import glob
import logging

from actual import Actual
from actual.exceptions import UnknownFileId, ActualError
from actual.queries import get_or_create_account, reconcile_transaction

# --- Configuration (Environment Variables) ---
ACTUAL_BUDGET_URL = os.environ.get("ACTUAL_BUDGET_URL")
ACTUAL_BUDGET_PASSWORD = os.environ.get("ACTUAL_BUDGET_PASSWORD")
CSV_FILE_PATH = os.environ.get("CSV_FILE_PATH")
BUDGET_NAME = os.environ.get("BUDGET_NAME") or "CSV Import"
ACCOUNT_NAME_DEFAULT = os.environ.get("ACCOUNT_NAME_DEFAULT")

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helper Functions ---

def load_csv_data(file: pathlib.Path) -> list[dict]:
    data = []
    with open(file, encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip header row if present
        for row in reader:
            try:
                date_str = row[1]
                amount_str = row[7]
                payee = row[4]
                category = ""  # row[6]
                notes = row[11] if len(row) > 11 else ""

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
                logging.error(f"Error processing row: {row} from file {file.name}. Skipping. Error: {e}")
                continue

    return data

def process_csv_file(file_path: pathlib.Path, actual: Actual):
    try:
        added_transactions = []
        row_number = 1
        for row in load_csv_data(file_path):
            logging.info(f"Processing row {row_number} from {file_path.name}: {row}")

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
                    logging.info(f"Added or modified {t} from file {file_path.name}")
            except ActualError as e:
                logging.error(f"Error reconciling transaction (row {row_number}): {row} from file {file_path.name}. Error: {e}")
                continue

            row_number += 1

        actual.commit()
        logging.info(f"Transactions from {file_path.name} imported successfully!")
    except Exception as e:
        logging.exception(f"A general error occurred while processing {file_path.name}: {e}")


def main():
    if not ACTUAL_BUDGET_PASSWORD:
        raise ValueError("ACTUAL_BUDGET_PASSWORD environment variable must be set.")
    if not CSV_FILE_PATH:
        raise ValueError("CSV_FILE_PATH environment variable must be set.")
    if not ACCOUNT_NAME_DEFAULT:
        raise ValueError("ACCOUNT_NAME_DEFAULT environment variable must be set.")

    try:
        with Actual(
            base_url=ACTUAL_BUDGET_URL,
            password=ACTUAL_BUDGET_PASSWORD
        ) as actual:
            try:
                actual.set_file(BUDGET_NAME)
                actual.download_budget()
            except UnknownFileId:
                logging.error(f"Budget '{BUDGET_NAME}' not found. Please create it manually in Actual.")
                return

            for file_pattern in CSV_FILE_PATH.split(','):
                files = glob.glob(file_pattern.strip())
                for file_path_str in files:
                    file_path = pathlib.Path(file_path_str)

                    if file_path.is_file():
                        process_csv_file(file_path, actual)
                    else:
                        logging.warning(f"{file_path_str} is not a valid file.")

    except Exception as e:
        logging.exception(f"A general error occurred: {e}")


if __name__ == "__main__":
    main()