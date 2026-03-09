from playwright.sync_api import TimeoutError as PWTimeoutError

BACK_BTN = 'button.btnListe[title*="Aller à la liste"]'
ROWS_SEL = ".bc tbody tr[itemlb]:visible"  
XPATHS = {
    "ID": '//*[@id="champ_cdtnom"]',
    "EMAIL": "//*[@id='champ_cmsmb_id']/td[2]/div[2]/a",
    "EXAM_ID": "//*[@id='champ_detail']/td[2]/div[2]/table/tbody/tr[5]/td[2]",
    "EXAM_TYPE": "//*[@id='champ_detail']/td[2]/div[2]/table/tbody/tr[3]/td[2]",
    "LINGUASKILL_TYPE": '//*[@id="champ_detail"]/td[2]/div[2]/table/tbody/tr[4]/td[2]', 
    "XPATH_ONLINE_TUTOR": "//*[@id='champ_detail']/td[2]/div[2]/table/tbody/tr[last()]/td[2]", 
    "DT_CREATION": "//tr[@id='champ_dt_creation']//div[contains(@class,'affVal') and @p='dt_creation']"}

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

        elif (line.startswith("Nationalité") or line.startswith("Nationalite") and i+1 < len(lines)): 
            nxt = lines[i+1]
            if nxt not in ("Pièce d'identité", "Genre", "Nom", "Prénom", "Date de naissance", "N° d'identité"):
                nationality = nxt

    res = {
        "surname": surname,
        "name": name,
        "date_of_birth": date_of_birth,
        "id_number": id_number,
        "gender" : gender, 
        "nationality" : nationality
    }
    return res 

def scrape(page, timeout=0.5):
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
    identity_info = parse_identity_block(raw_data.get("ID") or "")
    data.update(identity_info)    
    exam_detail = parse_exam_id_block(raw_data.get("EXAM_ID") or "")
    data.update(exam_detail)
    data["email"] = raw_data.get("EMAIL")
    data["exam_type"] = raw_data.get("EXAM_TYPE")
    data["dt_creation"] = raw_data.get("DT_CREATION")
    data["linguaskill_type"] = raw_data.get("LINGUASKILL_TYPE")
    data["online_tutor"] = is_online_tutor(raw_data.get("XPATH_ONLINE_TUTOR"))
    return data

def is_online_tutor(string): 
    if string: 
        if string == "Non merci, je n'ai pas besoin de la préparation": 
            return False
        elif string == 'J\'ai besoin de la préparation "Linguaskill Course" Online Tutor':
            return True
        else : 
            print("Problème dans la récupération du online_tutor")
            return None
    else:
        return None
    
def main(page):
    page.set_default_timeout(5000)
    data = []
    for i in range(page.locator(ROWS_SEL).count()):
        try:
            rows = page.locator(ROWS_SEL)
            row = rows.nth(i)
            row.wait_for(state="visible")
            if row.locator("td[data-p='velart_id']").inner_text() == "LINGUASKILL Anywhere":
                row.click()
                info = scrape(page) #traiter le cas ou c'est pas des PAS un LINGUASKILL GENERAL
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