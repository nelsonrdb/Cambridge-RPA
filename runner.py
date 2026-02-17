import argparse
from playwright.sync_api import sync_playwright

from pathlib import Path

from auth import ensure_logged_with_state
from orders import extract_data
from session_name import add_sessionname
from get_passwords import main as extract_passwords

from export_csv import write_csv_same_columns, write_done_flag, remove_done_flag


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", "-d", default=None)
    args = parser.parse_args()

    csv_path = Path("/Users/nelsonrouxdebezieux/Desktop/Cambridge_automation/shared/orders.csv")
    outdir = csv_path.parent

    print("\n ===== Extracting data =====")
    with sync_playwright() as p:
        browser, context, page = ensure_logged_with_state(p, headless=False)

        try:
            data = extract_data(context, args.date)
            extract_passwords(context)

                
        finally:
            context.close()
            browser.close()

    print("\n ===== Export =====")

    # remove_done_flag(outdir)          
    write_csv_same_columns(data, csv_path)
    write_done_flag(outdir)
    add_sessionname(csv_path) 

if __name__ == "__main__":
    main()
