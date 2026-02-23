import argparse
from playwright.sync_api import sync_playwright
from pathlib import Path
from auth import ensure_logged_with_state
from orders import extract_data
from session_name import add_sessionname
from get_passwords import main as extract_passwords
from export_csv import write_csv_same_columns, write_done_flag, remove_done_flag

def main():
    #parser = argparse.ArgumentParser()
    #parser.add_argument("--start_date", "-s", required=True)
    #parser.add_argument("--end_date", "-e", required=False)

    #args = parser.parse_args()
    csv_path = Path("/Users/nelsonrouxdebezieux/Documents/Cambridge-RPA/shared/orders.csv") #A MODIFIER POUR LE CLOUD

    print("\n ===== Extracting data =====")
    with sync_playwright() as p:
        browser, context, page = ensure_logged_with_state(p, headless=False)
        try:
            data = extract_data(context)#, args.start_date, args.end_date)
            emails = [x["email"] for x in data] #gérer le cas ou data est vide 
            passwords = extract_passwords(context, emails)
       
        finally:
            context.close()
            browser.close()

    print("\n ===== Export =====")
    #A TERME FAIRE QUE LES STATUT "CODE A ENVOYER"

    # remove_done_flag(outdir)          
    write_csv_same_columns(data, passwords, csv_path)
    # write_done_flag(outdir)
    add_sessionname(csv_path) 

if __name__ == "__main__":
    main()
