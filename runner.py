import argparse
from playwright.sync_api import sync_playwright
from pathlib import Path
from auth import ensure_logged_with_state
from orders import extract_data
from session_name import add_sessionname
from get_passwords import main as extract_passwords
from export_csv import create_dataframe

def main():
    with sync_playwright() as p:
        browser, context, _ = ensure_logged_with_state(p)
        try:
            data = extract_data(context)
            emails = [x["email"] for x in data] #gérer le cas ou data est vide 
            passwords = extract_passwords(context, emails)
       
        finally:
            context.close()
            browser.close()

    # remove_done_flag(outdir)          
    # write_done_flag(outdir)
    return create_dataframe(data, passwords)

if __name__ == "__main__":
    main()
