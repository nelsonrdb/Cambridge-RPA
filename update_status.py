from playwright.sync_api import sync_playwright
from auth import ensure_logged_with_state

BACK_BTN = 'button.btnListe[title*="Aller à la liste"]'

def go_to_commandes(page):
    page.wait_for_timeout(500)  
    page.locator("#btnVN").first.click()
    page.wait_for_timeout(500)  
    page.keyboard.type("Commandes", delay=30)
    page.wait_for_timeout(500)  
    page.keyboard.press("Enter")
    page.wait_for_timeout(500)

# Human-readable (French) explanation of each known manual-review reason,
# matched by substring against result["manual_review_reason"] — some
# reasons carry details after a known prefix (e.g. the ambiguous sessions).
MANUAL_REASONS = [
    ("entry_code_candidate", "Entry code détecté dans l'historique du client (code XXXXX-XXXXX ou 'entrypoints') — à inscrire à la main."),
    ("non_france_nationality_or_residence", "Nationalité ou pays de résidence différent de France — seuls les candidats France/France sont inscrits automatiquement."),
    ("unrecognised_exam_type_or_product", "Formule d'examen ou produit (Linguaskill/EST, General/Business) non reconnu — impossible de déterminer la session."),
    ("Unrecognised product", "Produit non reconnu (ni Linguaskill ni EST)."),
    ("Unrecognised linguaskill_type", "Type General/Business non reconnu."),
    ("no_test_credits_remaining", "Plus de crédits de test Cambridge pour une des compétences de la session."),
    ("existing_cambridge_candidate_found_but_no_password_on_file", "Compte Cambridge déjà existant pour cet email, mais aucun mot de passe trouvé dans X-Net — impossible de communiquer les accès."),
    ("Ambiguous 'Search Existing' match", "Plusieurs comptes Cambridge trouvés pour cet email — impossible de choisir le bon."),
    ("ambiguous_existing_est_sessions", "Plusieurs sessions EST existent déjà pour ce candidat et cette formule — risque de doublon."),
    ("Cannot map gender", "Genre du candidat non reconnu."),
    ("could not be confirmed", "La session a été soumise sur Cambridge mais sa création n'a pas pu être confirmée — vérifier sur Cambridge."),
    ("not found in session entries after save", "Candidat enregistré mais introuvable dans la session ensuite — vérifier sur Cambridge avant de réinscrire."),
    ("EST session form has no end date", "Le formulaire de session EST n'a pas de date de fin."),
    ("Session not found", "Session introuvable sur Cambridge."),
    ("login failed", "Échec de connexion à Cambridge."),
    ("CAMBRIDGE_USERNAME", "Identifiants Cambridge manquants dans la configuration."),
    ("bounced back to the login page", "Session Cambridge expirée / connexion refusée."),
]


def manual_review_comment(reason) -> str:
    reason = str(reason or "").strip()
    for key, message in MANUAL_REASONS:
        if key in reason:
            return f"Mis en MANUEL par l'automate : {message}"
    # Unknown/technical error (e.g. a Playwright timeout): keep only its
    # first line — the rest is a long call log.
    first_line = reason.splitlines()[0][:300] if reason else "raison inconnue"
    return f"Mis en MANUEL par l'automate : erreur technique — {first_line}"


def _present(value) -> bool:
    return isinstance(value, str) and value.strip() != ""


def success_comment(info_dic) -> str:
    lines = []
    if _present(info_dic.get("est_valid_from")) and _present(info_dic.get("est_valid_until")):
        lines.append(f"Test à passer entre le {info_dic['est_valid_from']} et le {info_dic['est_valid_until']}")
    elif _present(info_dic.get("exam_date")) and _present(info_dic.get("exam_hour")):
        lines.append(f"Date / Heure d'Examen - Le {info_dic['exam_date']} à {info_dic['exam_hour']}")
    lines += [
        f"Username : {info_dic['email']}",
        f"Password : {info_dic['password']}",
        "Institution : FR731",
    ]
    return "\n".join(lines)


def set_status_and_comment(page, info_dic): 
    page.wait_for_timeout(1000)
    try:
        page.get_by_text("Statut WF", exact=False).click(timeout=3000)
    except:
        page.locator('button.btn.btn-default.btn-sm.mrBtn.noPicto').click()
        page.wait_for_timeout(500)
        try:
            page.get_by_text("Statut WF", exact=False).click(timeout=3000)
        except:
            raise Exception("Bouton 'Statut WF' introuvable")
    if info_dic["success"]: 
        page.wait_for_timeout(500)
        locator = page.locator('#champ_velcmdwftrid select')
        locator.select_option(label="MAIL A ENVOYER")
        textarea = page.locator('textarea[name="wfcmt"]')

        textarea.fill(success_comment(info_dic))
    else:
        page.locator('select[name="velcmdwftrid"]').select_option('MANUEL')
        page.locator('textarea[name="wfcmt"]').fill(
            manual_review_comment(info_dic.get("manual_review_reason"))
        )
    
    page.locator('button:has-text("Valider")').click()
    page.locator(BACK_BTN).click()



def go_to_order(page, order_number):
    search_input = page.locator('input[name="_rr"]')
    search_input.wait_for(state="visible")
    page.wait_for_timeout(500)
    search_input.type(order_number, delay=100)
    page.wait_for_timeout(500)
    page.keyboard.press("Enter") 


#FONCTION DEV MODE
#order_list = {order_number : [email, password, sucess_bool]}
def main(order_info, headless=True):
        with sync_playwright() as p:
            _, _, page = ensure_logged_with_state(p, headless=headless)
            try:
                go_to_commandes(page)
                for order, info in order_info.items():
                    go_to_order(page, order)
                    set_status_and_comment(page, info)
            except Exception as e:
                print("Exception : ", str(e))

        print("CMS Workflow commenté")

if __name__ == "__main__":
    sample_dic = {'AD226-0004':{"email": "charlotte.aux.fraises@gmail.com", "password" : "AFZEFSL314", "sucess" : "True"}}
    main(sample_dic, headless=False)


               