import pandas as pd
import secrets
import string
import re


ORDERS_URL = "https://xnet-apps.com/xa/victorias/" 


import string
import secrets

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
        password = None
        entry_code_detected_bool = False 
        if rows.count() >= 2:
            row2 = rows.nth(1) 
            row2.click()
            page.wait_for_timeout(500)

            n = page.locator('xpath=//*[@id="champ_wfs"]/td[2]/div[2]/table/tbody/tr').count()
            password = None 
            try : 
                for i in range(2, n+1):
                    text = page.locator(f'xpath=//*[@id="champ_wfs"]/td[2]/div[2]/table/tbody/tr[{i}]/td[4]').inner_text(timeout=500)
                    temp = return_password(text)
                    if temp: 
                        password = temp
                        break 
            except Exception as e: 
                print(str(e))
        try: 
            if entry_code_detected(page):
                entry_code_detected_bool = True 
                print("Entry code detected")
        except Exception as e: 
            print(str(e))
        return (password, entry_code_detected_bool)
    except Exception as e:
        print(str(e))

    finally:
        try : 
            page.get_by_title("Aller à la liste [←]").first.click()
        except Exception as e : 
            print(str(e))


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
