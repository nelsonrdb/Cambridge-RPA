import re
from playwright.sync_api import TimeoutError as PWTimeoutError
import pandas as pd
import secrets
import string

def generate_password_7() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(7))

ORDERS_URL = "https://xnet-apps.com/xa/victorias/" 

def main(context, mail_list): 
    page = context.new_page()
    page.goto(ORDERS_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(500)  
    page.locator("#btnVN").first.click()
    page.keyboard.type("Clients", delay=30)
    page.keyboard.press("Enter")

    res = {}
    try:
        for email in mail_list:
            pwd = get_password_for_email(page, email)
            if pwd:
                res[email] = [pwd, pd.NA, pwd]
            else: 
                pwd = generate_password_7()
                res[email] = [pd.NA, pwd, pwd]             
    finally: 
        page.close()
    return res

def get_password_for_email(page, email):
    try:
        page.get_by_title("Effacer le filtre (et afficher tous les éléments)").first.click()

        page.locator("#sel_email_contient_0").click()
        page.locator("#sel_email_contient_0").fill(email)
        page.get_by_title("Appliquer le filtre").click()

        page.locator(
            f'table.zL tbody tr:has(td[data-p="email"] span:text("{email}"))'
        ).first.click()

        page.locator('a.drAff[zzrelsid="617"]').click()

        rows = page.locator('table.zL[cat="velcmd"] tbody > tr')
        page.wait_for_timeout(500)
        if rows.count() < 2:
            return None

        row2 = rows.nth(1) 
        row2.click()
        page.wait_for_timeout(500)

        password_paths = [
            'xpath=//*[@id="champ_wfs"]/td[2]/div[2]/table/tbody/tr[2]/td[4]',
            'xpath=//*[@id="champ_wfs"]/td[2]/div[2]/table/tbody/tr[3]/td[4]',
        ]

        try : 
            for path in password_paths:
                text = page.locator(path).inner_text(timeout=500)
                lines = text.splitlines()
                if len(lines) == 3:
                    return lines[1].split()[-1].strip()
        except Exception as e: 
            print("Ligne 1 : ", lines[1])
            print(str(e))
        return None

    finally:
        try : 
            page.get_by_title("Aller à la liste [←]").first.click()
        except Exception as e : 
            print(str(e))





