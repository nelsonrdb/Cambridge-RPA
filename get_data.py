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
    "ID": '//*[@id="champ_nom_prenom"]',
    "EMAIL": "//*[@id='champ_cmsmb_id']/td[2]/div[2]/a",
    "EXAM_ID": "//*[@id='champ_detail']/td[2]/div[2]/table/tbody/tr[5]/td[2]",
    "EXAM_TYPE": "//*[@id='champ_detail']/td[2]/div[2]/table/tbody/tr[3]/td[2]",
    "LINGUASKILL_TYPE": '//*[@id="champ_detail"]/td[2]/div[2]/table/tbody/tr[4]/td[2]',
    "CANDIDATE_PASSWORD": '//*[@id="champ_wfs"]/td[2]/div[2]/table/tbody/tr[2]/td[4]',
}

def name_parsing(full_name):
    parts = full_name.split()

    surname_parts = []
    given_parts = []

    for p in parts:
        if p.upper() == p and not given_parts:
            surname_parts.append(p)
        else:
            given_parts.append(p)

    surname = None
    name = None

    if surname_parts:
        surname = " ".join(surname_parts)
    if given_parts:
        name = " ".join(given_parts)
    return surname, name


def parse_exam_id_block(text: str):
    if not text:
        return {"exam_date": None, "exam_hour": None}
    return {"exam_date": text[27:37], "exam_hour": text[-3:]}


def parse_identity_block(text: str):
    """
    Prend le bloc brut :
    'Nom, prénom\\nPOUSSIN Ruth-Charlene\\nDate de naissance\\n01/01/2001\\nPièce d'identité\\nN° d'identité\\n0101'
    et renvoie un dict propre.
    """
    if not text:
        return {"surname": None, "name": None, "date_of_birth": None, "id_number": None}

    lines = [l.strip() for l in text.splitlines() if l.strip()]

    full_name = None
    date_of_birth = None
    id_number = None

    for i, line in enumerate(lines):
        if line.startswith("Nom, prénom") and i + 1 < len(lines):
            full_name = lines[i + 1]

        elif line.startswith("Date de naissance") and i + 1 < len(lines):
            nxt = lines[i + 1]
            if "Pièce d'identité" not in nxt and "N°" not in nxt:
                date_of_birth = nxt

        elif (line.startswith("N° d'identité") or line.startswith("N° pièce d'identité")) and i + 1 < len(lines):
            nxt = lines[i + 1]
            if not (nxt.startswith("Pièce d'identité") or nxt.startswith("Nom, prénom") or nxt.startswith("Date de naissance")):
                id_number = nxt

    surname = None
    name = None
    if full_name:
        surname, name = name_parsing(full_name)

    return {
        "surname": surname,
        "name": name,
        "date_of_birth": date_of_birth,
        "id_number": id_number,
    }

def scrape(page, timeout=0.5):
    raw_data = {}

    timeout_ms = int(timeout * 1000)

    for field, xpath in XPATHS.items():
        try:
            elem_t0 = time.time()

            loc = page.locator(f"xpath={xpath}").first
            loc.wait_for(state="visible", timeout=timeout_ms)

            elapsed = time.time() - elem_t0

            # inner_text() = proche de Selenium .text (visible text)
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
    results = []

    ROWS_SEL = ".bc tr:visible"  # adapte si besoin
    BACK_BTN = 'button.btnListe[title*="Aller à la liste"]'

    total = page.locator(ROWS_SEL).count()
    print("Nb rows à traiter:", total)
    emails = []
    data = []
    for i in range(1, total):
        print("Row", i)
        try:
            rows = page.locator(ROWS_SEL)
            row = rows.nth(i)

            row.wait_for(state="visible")
            row_text = row.inner_text().strip().replace("\n", " ")[:120]

            cells = row.locator("td")
            vals = [cells.nth(j).inner_text().strip() for j in range(cells.count())]
            emails.append(vals[9])

            row.click()

            info = scrape(page)
            data.append(info)

            menu = page.locator("ul.drOs").first
            menu.wait_for(state="visible")

            contrats = menu.locator("a.drAff", has_text=re.compile(r"contrats", re.I)).first
            contrats.click()

            table_contrats = page.locator('table[cat="velcontrat"]').first
            table_contrats.wait_for(state="visible")

            nb = table_contrats.locator("tbody tr").count()
            print(f"[{i}] contrats = {nb} | row = {row_text}")
            results.append({"index": i, "row_text": row_text, "contracts_count": nb})

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

    print(emails)
    print("--------------------------")
    print(data)
    return results