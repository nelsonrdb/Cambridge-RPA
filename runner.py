import argparse
from playwright.sync_api import sync_playwright

from pathlib import Path

from auth import ensure_logged_with_state
from orders import get_today_order_urls
from scrapper import main as scrape_order  
from session_name import add_sessionname

from export_csv import write_csv_same_columns, write_done_flag, remove_done_flag



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", "-d", default=None)
    args = parser.parse_args()

    csv_path = Path("/Users/nelsonrouxdebezieux/Desktop/Cambridge_automation/shared/orders.csv")
    outdir = csv_path.parent


    with sync_playwright() as p:
        browser, context, page = ensure_logged_with_state(p, headless=False)

        try:
            urls = get_today_order_urls(context, args.date)
            print("URLs trouvées:", len(urls))
                
        finally:
            context.close()
            browser.close()

    print("\n=== Lancement du scrapping Selenium ===")
    data = []
    for u in urls:
        print(f"\nScraping {u} ...")
        result = scrape_order(u)   
        data.append(result)

    print("\n ===== Export =====")

    remove_done_flag(outdir)          
    write_csv_same_columns(data, csv_path)
    write_done_flag(outdir)
    add_sessionname(csv_path)

if __name__ == "__main__":
    main()
