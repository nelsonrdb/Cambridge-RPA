import pandas as pd
import secrets
import string
import re
from playwright.sync_api import TimeoutError as PWTimeout

ORDERS_URL = "https://xnet-apps.com/xa/victorias/" 

def generate_password_8() -> str:
    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    digits = string.digits
    
    password_chars = [
        secrets.choice(lower),
        secrets.choice(upper),
        secrets.choice(digits),
    ]
    
    all_chars = lower + upper + digits
    password_chars += [secrets.choice(all_chars) for _ in range(5)]
    
    secrets.SystemRandom().shuffle(password_chars)
    
    return "".join(password_chars)

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
            pwd, is_entry_code = get_password_for_email(page, email)
            if pwd:
                res[email] = [pwd, pd.NA, pwd, is_entry_code]
            else: 
                pwd = generate_password_8()
                res[email] = [pd.NA, pwd, pwd, is_entry_code]             
    finally: 
        page.close()
    return res

def get_password_for_email(page, email):
    password = None
    entry_code_detected_bool = False

    try:
        page.get_by_title("Effacer le filtre (et afficher tous les éléments)").first.click(timeout=15000)

        page.locator("#sel_email_contient_0").click(timeout=15000)
        page.locator("#sel_email_contient_0").fill(email, timeout=15000)

        btn = page.get_by_title("Appliquer le filtre")
        btn.click(timeout=15000, no_wait_after=True)

        page.locator(
            f'table.zL tbody tr:has(td[data-p="email"] span:text("{email}"))'
        ).first.click(timeout=15000)

        page.locator('a.drAff[zzrelsid="617"]').click(timeout=15000)

        rows = page.locator('table.zL[cat="velcmd"] tbody > tr')
        rows.first.wait_for(state="visible", timeout=15000)  # plus fiable que wait_for_timeout(500)

        if rows.count() >= 2:
            password = None 
            entry_code_detected_bool = False
            row2 = rows.nth(1)
            row2.click(timeout=15000)
            page.locator('#champ_wfs td.champ table.zzList').wait_for(state="visible", timeout=15000)
            wfs_rows = page.locator(
                'xpath=//*[@id="champ_wfs"]//td[contains(@class,"champ")]'
                '//table[contains(@class,"zzList")]//tbody/tr[td]'
            )
            n = wfs_rows.count()

            password = None
            for idx in range(n):
                row = wfs_rows.nth(idx)

                try:
                    text = row.locator("td").nth(3).inner_text(timeout=15000).strip()
                except PWTimeout:
                    continue

                temp = return_password(text)
                if temp:
                    password = temp
                    break

                try:
                    if entry_code_detected(page):
                        entry_code_detected_bool = True
                        print("Entry code detected")
                except Exception as e:
                    print(f"entry_code_detected() error: {e}")


    except Exception as e:
        print(f"get_password_for_email error for {email}: {e}")
        return (None, False)
    
    finally:
        try:
            page.get_by_title("Aller à la liste [←]").first.click(timeout=15000, no_wait_after=True)
        except Exception as e:
            print(f"back to list failed: {e}")
    return (password, entry_code_detected_bool)

def entry_code_detected(page): 
    table = page.locator("table.zzList")
    fourth_col_texts = table.locator("tbody > tr > td:nth-child(4)").all_inner_texts()

    CODE_RE = re.compile(r"(?i)\b([A-Z0-9]{5}-[A-Z0-9]{5})\b")

    for s in fourth_col_texts:
        s = s.replace("\xa0", " ")  
        if "entrypoints" in re.sub(r"\s+", "", s).lower():
            return True
        if CODE_RE.search(s):
            return True
    return False

def return_password(txt):
    if not isinstance(txt, str) or not txt.strip():
        return None

    for raw in txt.replace("\xa0", " ").splitlines():
        line = raw.strip()
        if not line:
            continue
        tokens = [t for t in line.replace(":", " ").split() if t]

        if tokens and tokens[0].lower() == "password":
            return tokens[-1] if len(tokens) >= 2 else None

    return None

