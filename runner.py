from playwright.sync_api import sync_playwright
from auth import ensure_logged_with_state
from orders import extract_data
from get_passwords import main as extract_passwords
from export_csv import create_dataframe
import argparse
import pandas as pd

def main(headless=True):
    with sync_playwright() as p:
        browser, context, _ = ensure_logged_with_state(p, headless=headless)
        try:
            data = extract_data(context)
            if len(data)>0: 
                emails = [x["email"] for x in data]
                passwords = extract_passwords(context, emails)
                #create_dataframe(data, passwords).to_csv("shared/orders.csv", index=False)
                return create_dataframe(data, passwords)
            else : 
                print("Aucune nouvelle commande à été trouvée dans le CMS")
                return pd.DataFrame(columns = ["order_number", 'surname', 'name', 'date_of_birth', 'id_number', 'exam_date', 'exam_hour', 'email', 'exam_type', 'dt_creation', 'linguaskill_type', 'online_tutor', 'password_cms', 'password_generated', 'password', 'is_entry_code', 'session_name'])
            
        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Lance Playwright avec une fenêtre visible (headless=False)."
    )
    args = parser.parse_args()

    main(headless=not args.headed)