from playwright.sync_api import TimeoutError as PWTimeoutError
from time import time
from datetime import datetime
from zoneinfo import ZoneInfo

BACK_BTN = 'button.btnListe[title*="Aller à la liste"]'
ROWS_SEL = ".bc tbody tr[itemlb]:visible"  
XPATHS = {
    "ID": '//*[@id="champ_cdtnom"]',
    "EMAIL": "//*[@id='champ_cmsmb_id']/td[2]/div[2]/a",
    "EXAM_ID": "//*[@id='champ_detail']/td[2]/div[2]/table/tbody/tr[5]/td[2]",
    "EXAM_TYPE": "//*[@id='champ_detail']/td[2]/div[2]/table/tbody/tr[3]/td[2]",
    "LINGUASKILL_TYPE": '//*[@id="champ_detail"]/td[2]/div[2]/table/tbody/tr[4]/td[2]', 
    "XPATH_ONLINE_TUTOR": "//*[@id='champ_detail']/td[2]/div[2]/table/tbody/tr[last()]/td[2]", 
    "DT_CREATION": "//tr[@id='champ_dt_creation']//div[contains(@class,'affVal') and @p='dt_creation']", 
    "ORDER_NUMBER": '//*[@p="num_aff"]'}

# X-Net article (velart_id column) of each order type handled automatically.
LINGUASKILL_ARTICLE = "Inscriptions LINGUASKILL"
EST_ARTICLE = "English Skills Test (EST)"
HANDLED_ARTICLES = (LINGUASKILL_ARTICLE, EST_ARTICLE)

PARIS = ZoneInfo("Europe/Paris")

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
    gender = None
    nationality = None
    country_of_residence = None

    for i, line in enumerate(lines):
        if line.startswith("Nom") and i + 1 < len(lines):
            nxt = lines[i + 1]
            if nxt not in ("Prénom", "Date de naissance", "Genre", "Pièce d'identité", "N° pièce d'identité", "N° d'identité"):
                surname = parse_id(nxt, "surname")

        elif (line.startswith("Prénom") or line.startswith("Prenom")) and i + 1 < len(lines):
            nxt = lines[i + 1]
            if nxt not in ("Nom", "Date de naissance", "Genre", "Pièce d'identité", "N° pièce d'identité", "N° d'identité"):
                name = parse_id(nxt, "name")

        elif (line.startswith("Genre")) and i + 1 < len(lines):
            nxt = lines[i + 1]
            if nxt not in ("Nom", "Date de naissance", "Genre", "Pièce d'identité", "N° pièce d'identité", "N° d'identité"):
                gender = nxt

        elif line.startswith("Date de naissance") and i + 1 < len(lines):
            nxt = lines[i + 1]
            if nxt not in ("Pièce d'identité", "Genre", "N° pièce d'identité", "N° d'identité", "Nom", "Prénom"):
                date_of_birth = nxt

        elif (line.startswith("N° d'identité") or line.startswith("N° pièce d'identité")) and i + 1 < len(lines):
            nxt = lines[i + 1]
            if nxt not in ("Pièce d'identité", "Genre", "Nom", "Prénom", "Date de naissance"):
                id_number = nxt

        elif (line.startswith("Nationalité") or line.startswith("Nationalite")) and i + 1 < len(lines):
            nxt = lines[i + 1]
            if nxt not in ("Pièce d'identité", "Genre", "Nom", "Prénom", "Date de naissance", "N° d'identité", "Pays"):
                nationality = nxt

        # "Pays" = country of residence, distinct from "Nationalité" (a
        # candidate's nationality and country of residence can differ).
        elif line.startswith("Pays") and i + 1 < len(lines):
            nxt = lines[i + 1]
            if nxt not in ("Pièce d'identité", "Genre", "Nom", "Prénom", "Date de naissance", "N° d'identité", "Nationalité"):
                country_of_residence = nxt

    res = {
        "surname": surname,
        "name": name,
        "date_of_birth": date_of_birth,
        "id_number": id_number,
        "gender" : gender,
        "nationality" : nationality,
        "country_of_residence" : country_of_residence
    }
    return res

def scrape(page, timeout=0.5, is_est=False):
    raw_data = {}
    timeout_ms = int(timeout * 1000)

    for field, xpath in XPATHS.items():
        try:
            loc = page.locator(f"xpath={xpath}").first
            loc.wait_for(state="visible", timeout=10000)#anciennement 2000
            raw_data[field] = loc.inner_text(timeout=timeout_ms).strip()   
        except PWTimeoutError as e:
            print(str(e))
            raw_data[field] = None
        except Exception as e:
            print(str(e))
            raw_data[field] = None


    data = {}
    data["order_number"] = raw_data.get("ORDER_NUMBER").split("\n")[-1]
    identity_info = parse_identity_block(raw_data.get("ID") or "")
    data.update(identity_info)    
    if is_est:
        # EST has no exam date: the candidate gets ~3 months to take it
        # from the day the order is processed, so the session is dated
        # today (Paris time — the scheduled run is on UTC). The detail row
        # that holds the exam date for Linguaskill is the preparation
        # (online tutor) choice for EST.
        now = datetime.now(PARIS)
        data["exam_date"] = now.strftime("%d/%m/%Y")
        data["exam_hour"] = now.strftime("%H:%M")
        online_tutor_raw = raw_data.get("EXAM_ID")
    else:
        exam_detail = parse_exam_id_block(raw_data.get("EXAM_ID") or "")
        data.update(exam_detail)
        online_tutor_raw = raw_data.get("XPATH_ONLINE_TUTOR")
    data["email"] = raw_data.get("EMAIL")
    data["exam_type"] = raw_data.get("EXAM_TYPE")
    data["dt_creation"] = raw_data.get("DT_CREATION")
    data["linguaskill_type"] = raw_data.get("LINGUASKILL_TYPE")
    data["online_tutor"] = is_online_tutor(online_tutor_raw)
    data["scrapping_time"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    return data

def is_online_tutor(string):
    if not string:
        return None

    normalized = string.strip().lower()
    if "non" in normalized:
        return False
    if "oui" in normalized or "j'ai besoin" in normalized:
        return True

    print(f"Problème dans la récupération du online_tutor: {string!r}")
    return None
    
def set_statusWF(page): 
    while page.locator(ROWS_SEL).count() > 0: 
        rows = page.locator(ROWS_SEL)
        row = rows.nth(1)
        row.click()
        page.locator('a[title="Revenir ou aller à un statut workflow"]').click()
        page.locator('select[name="velcmdwftrid"]').selectOption('3')
        page.locator('button:has-text("Valider")').click()
        page.locator(BACK_BTN).click()
        page.locator(ROWS_SEL).first.wait_for(state="visible")
    print("Orders set à 'En cours' status")


    
def main(page):
    page.set_default_timeout(5000)
    data = []
    N = page.locator(ROWS_SEL).count()
    for i in range(N):
        try:
            rows = page.locator(ROWS_SEL)
            row = rows.nth(i)
            row.wait_for(state="visible")
            article = row.locator("td[data-p='velart_id']").inner_text()
            if article in HANDLED_ARTICLES:
                row.click()
                info = scrape(page, is_est=(article == EST_ARTICLE))
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