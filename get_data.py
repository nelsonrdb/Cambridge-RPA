import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from playwright.sync_api import TimeoutError as PWTimeoutError


BACK_BTN_XPATH = '//button[contains(@class,"btnListe") and contains(@title,"Aller à la liste")]'
ROWS_SEL = '.bc:visible table[cat="velcmd"] tbody tr.la'

import time
from playwright.sync_api import TimeoutError as PWTimeoutError

XPATHS = {
    "ID": '//*[@id="champ_cdtnom"]',
    "EMAIL": "//*[@id='champ_cmsmb_id']/td[2]/div[2]/a",
    "EXAM_ID": "//*[@id='champ_detail']/td[2]/div[2]/table/tbody/tr[5]/td[2]",
    "EXAM_TYPE": "//*[@id='champ_detail']/td[2]/div[2]/table/tbody/tr[3]/td[2]",
    "LINGUASKILL_TYPE": '//*[@id="champ_detail"]/td[2]/div[2]/table/tbody/tr[4]/td[2]',
    "CANDIDATE_PASSWORD": '//*[@id="champ_wfs"]/td[2]/div[2]/table/tbody/tr[2]/td[4]',
}

def parse_id(value, key):
    if value is None:
        return None

    value = str(value).strip()
    if value == "":
        return None

    if key == "surname":
        return value.upper()

    return " ".join(w[:1].upper() + w[1:].lower() for w in value.split())


def parse_exam_id_block(text: str):
    if not text:
        return {"exam_date": None, "exam_hour": None}
    return {"exam_date": text[27:37], "exam_hour": text[-3:]}

def parse_identity_block(text: str):
    if not text:
        return {"surname": None, "name": None, "date_of_birth": None, "id_number": None}

    lines = [l.replace("\xa0", " ").strip() for l in text.splitlines() if l.strip()]

    surname = None
    name = None
    date_of_birth = None
    id_number = None

    for i, line in enumerate(lines):
        if line.startswith("Nom") and i + 1 < len(lines):
            nxt = lines[i + 1]
            if nxt not in ("Prénom", "Date de naissance", "Pièce d'identité", "N° pièce d'identité", "N° d'identité"):
                surname = parse_id(nxt, "surname")

        elif (line.startswith("Prénom") or line.startswith("Prenom")) and i + 1 < len(lines):
            nxt = lines[i + 1]
            if nxt not in ("Nom", "Date de naissance", "Pièce d'identité", "N° pièce d'identité", "N° d'identité"):
                name = parse_id(nxt, "name")

        elif line.startswith("Date de naissance") and i + 1 < len(lines):
            nxt = lines[i + 1]
            if nxt not in ("Pièce d'identité", "N° pièce d'identité", "N° d'identité", "Nom", "Prénom"):
                date_of_birth = nxt

        elif (line.startswith("N° d'identité") or line.startswith("N° pièce d'identité")) and i + 1 < len(lines):
            nxt = lines[i + 1]
            if nxt not in ("Pièce d'identité", "Nom", "Prénom", "Date de naissance"):
                id_number = nxt
            
    res = {
        "surname": surname,
        "name": name,
        "date_of_birth": date_of_birth,
        "id_number": id_number,
    }
    return res 

def scrape(page, timeout=0.5):
    raw_data = {}
    timeout_ms = int(timeout * 1000)

    for field, xpath in XPATHS.items():
        try:
            loc = page.locator(f"xpath={xpath}").first
            loc.wait_for(state="visible", timeout=10000)
            raw_data[field] = loc.inner_text(timeout=timeout_ms).strip()
            
        except PWTimeoutError:
            raw_data[field] = None
        except Exception as e:
            raw_data[field] = None


    data = {}
    identity_info = parse_identity_block(raw_data.get("ID") or "")
    data.update(identity_info)    
    exam_detail = parse_exam_id_block(raw_data.get("EXAM_ID") or "")
    data.update(exam_detail)
    data["email"] = raw_data.get("EMAIL")
    data["exam_type"] = raw_data.get("EXAM_TYPE")
    data["linguaskill_type"] = raw_data.get("LINGUASKILL_TYPE")
    return data



def main(page):
    page.set_default_timeout(3000)

    ROWS_SEL = ".bc tr:visible"  # adapte si besoin
    BACK_BTN = 'button.btnListe[title*="Aller à la liste"]'

    total = page.locator(ROWS_SEL).count()
    print(total)
    data = []
    for i in range(2, total-1):
        try:
            rows = page.locator(ROWS_SEL)
            row = rows.nth(i)
            row.wait_for(state="visible")
            row.click()

            info = scrape(page)
            data.append(info)
            page.locator(BACK_BTN).click()
            page.locator(ROWS_SEL).first.wait_for(state="visible")

        except PWTimeoutError as e:
            print(f"[{i}] Timeout: {e}")
            try:
                page.keyboard.press("Escape")
                page.locator(BACK_BTN).click()
            except:
                pass

        except Exception as e:
            print(f"[{i}] Error: {e}")

    return data 