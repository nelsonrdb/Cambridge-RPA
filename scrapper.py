from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import json
import sys
import os
import subprocess
import time

CRM_URL = "https://xnet-apps.com/vs/commun/imprimer.php?ca=victorias&p=detail.php%3Fmode%3DC%26cat%3Dvelcmd%26id%3DCMD1504%26vueDest%3DI%26o%3Do0"

def create_driver():
    print("[INFO] Création du driver Chrome...")
    options = webdriver.ChromeOptions()
    # mets True quand tout marche pour le mode sans fenêtre
    options.add_argument("--headless=new")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.maximize_window()
    print("[INFO] Driver Chrome prêt.")
    return driver

LOGIN_URL = "https://xnet-apps.com/xa/victorias/"
TARGET_URL = "https://xnet-apps.com/vs/commun/imprimer.php?ca=victorias&p=detail.php%3Fmode%3DC%26cat%3Dvelcmd%26id%3DCMD19508%26fdo%3D1%26vueDest%3Dvlt%26o%3Do1"

XPATHS = {
    "ID": '//*[@id="champ_nom_prenom"]',
    "EMAIL": "//*[@id='champ_cmsmb_id']/td[2]/div[2]/a",
    "EXAM_ID": "//*[@id='champ_detail']/td[2]/div[2]/table/tbody/tr[5]/td[2]",
    "EXAM_TYPE": "//*[@id='champ_detail']/td[2]/div[2]/table/tbody/tr[3]/td[2]",
    "LINGUASKILL_TYPE": '//*[@id="champ_detail"]/td[2]/div[2]/table/tbody/tr[4]/td[2]',
    "CANDIDATE_PASSWORD": '//*[@id="champ_wfs"]/td[2]/div[2]/table/tbody/tr[2]/td[4]'
}

USERNAME = "Examens"
PASSWORD = "7Lin8gua!"


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
    # TODO: adapter si besoin selon le format réel du bloc
    return {"exam_date": text[27:37], "exam_hour": text[-3:]}


def parse_identity_block(text: str):
    """
    Prend le bloc brut :
    'Nom, prénom\\nPOUSSIN Ruth-Charlene\\nDate de naissance\\n  Pièce d'identité\\n ?'
    et renvoie un dict propre.
    """
    if not text:
        return {"surname": None, "name": None, "date_of_birth": None}

    lines = [l.strip() for l in text.splitlines() if l.strip()]

    full_name = None
    date_of_birth = None

    for i, line in enumerate(lines):
        if line.startswith("Nom, prénom") and i + 1 < len(lines):
            full_name = lines[i + 1]
        elif line.startswith("Date de naissance") and i + 1 < len(lines):
            date_of_birth = lines[i + 1] if "Pièce d'identité" not in lines[i + 1] else None

    name = None
    surname = None
    if full_name:
        surname, name = name_parsing(full_name)

    return {
        "surname": surname,
        "name": name,
        "date_of_birth": date_of_birth,
    }


def parse_password_block(text: str):
    if not text:
        return {"candidate_password": None}
    lines = [l.strip().strip('"') for l in text.splitlines() if l.strip()]
    password_line = next((l for l in lines if "Password" in l), None)
    if not password_line:
        return {"candidate_password": None}
    return {"candidate_password": password_line[-10:]}


def extract_order_data(driver, timeout=0.1):
    print("[INFO] Début de l'extraction des données...")
    t0 = time.time()
    wait = WebDriverWait(driver, timeout)
    raw_data = {}

    for field, xpath in XPATHS.items():
        print(f"[INFO]  → Recherche du champ '{field}' avec XPATH = {xpath}")
        try:
            elem_t0 = time.time()
            elem = wait.until(
                EC.visibility_of_element_located((By.XPATH, xpath))
            )
            elapsed = time.time() - elem_t0
            print(f"[OK]    Champ '{field}' trouvé en {elapsed:.1f}s")
            raw_data[field] = elem.text.strip()
        except TimeoutException:
            print(f"[WARN] Timeout ({timeout}s) sur le champ '{field}' (XPATH = {xpath})")
            raw_data[field] = None
        except Exception as e:
            print(f"[ERROR] Erreur sur le champ '{field}' : {e}")
            raw_data[field] = None

    print(f"[INFO] Extraction brute terminée en {time.time() - t0:.1f}s. Post-traitement...")

    data = {}

    identity_info = parse_identity_block(raw_data.get("ID") or "")
    data.update(identity_info)

    exam_detail = parse_exam_id_block(raw_data.get("EXAM_ID") or "")
    data.update(exam_detail)

    candidate_password = parse_password_block(raw_data.get("CANDIDATE_PASSWORD") or "")
    data.update(candidate_password)

    data["email"] = raw_data.get("EMAIL")
    data["exam_type"] = raw_data.get("EXAM_TYPE")
    data["linguaskill_type"] = raw_data.get("LINGUASKILL_TYPE")
    print("[INFO] Données extraites et parsées :")
    return data


def main(target_url: str = TARGET_URL):
    print(f"[INFO] Lancement du scrapper sur URL : {target_url}")
    driver = create_driver()
    wait = WebDriverWait(driver, 20)

    try:
        print(f"[INFO] Ouverture de la page de login : {LOGIN_URL}")
        driver.get(LOGIN_URL)

        t0 = time.time()
        print("[INFO] Attente des champs login / password...")
        username_input = wait.until(
            EC.visibility_of_element_located((By.NAME, "login"))
        )
        password_input = driver.find_element(By.NAME, "pwd")
        login_button = driver.find_element(By.XPATH, "//*[@id='btnCnx']")
        print(f"[OK] Formulaire de login trouvé en {time.time() - t0:.1f}s")

        print("[INFO] Saisie des identifiants...")
        username_input.send_keys(USERNAME)
        password_input.send_keys(PASSWORD)
        login_button.click()
        print("[INFO] Login soumis, attente de redirection...")

        time.sleep(2)  # petit sleep pour laisser le temps à la session de se poser

        print(f"[INFO] Navigation vers la page de commande : {target_url}")
        driver.get(target_url)

        print("[INFO] Page de commande chargée, extraction des données...")
        order_data = extract_order_data(driver)

    finally:
        print("[INFO] Fermeture du driver...")
        driver.quit()
        print("[INFO] Driver fermé.")
    return order_data


def build_email_text(data: dict) -> str:
    exam_date = data.get("exam_date") or "[DATE]"
    exam_hour = data.get("exam_hour") or "[HEURE]"
    email = data.get("email") or "[EMAIL]"
    password = data.get("candidate_password") or "[MOT_DE_PASSE]"
    institution_id = "FR731"

    name = data.get("name") or ""
    surname = data.get("surname") or ""

    texte = f"""Bonjour, 

Vous vous êtes inscrit.e au Linguaskill supervisé à distance le {exam_date} à {exam_hour}. Votre session dure 4 heures.

Vos identifiants sont les suivants : 

            Username        {email}
            Password        {password}
            Institution ID  {institution_id}

"""
    return texte


def save_email_text(data: dict, output_dir: str = "./garbage") -> str:
    # On s'assure que le dossier existe
    os.makedirs(output_dir, exist_ok=True)

    content = build_email_text(data)

    surname = (data.get("surname") or "candidate").replace(" ", "_")
    name = (data.get("name") or "").replace(" ", "_")
    exam_date = (data.get("exam_date") or "date").replace("/", "-")

    filename = f"linguaskill_{surname}_{name}_{exam_date}.txt"
    filepath = os.path.join(output_dir, filename)

    print(f"[INFO] Écriture du fichier texte : {filepath}")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Veuillez saisir une URL en argument.")
        print("Exemple :")
        print('  python scrapper.py "https://xnet-apps.com/...."')
        sys.exit(1)

    url = sys.argv[1]
    print("\n=== DÉBUT DU SCRAP ===")
    print("Scrapping https://xnet-apps.com/xa/victorias/")

    result = main(url)

    print("\n=== RÉSULTAT BRUT ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    output_path = save_email_text(result)
    print(f"\n✅ Fichier texte généré : {output_path}")

    try:
        print("[INFO] Ouverture du fichier dans l'éditeur par défaut...")
        subprocess.run(["open", output_path])
    except Exception as e:
        print(f"Impossible d'ouvrir automatiquement le fichier : {e}")
