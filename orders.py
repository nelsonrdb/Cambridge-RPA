import re
from datetime import datetime, date
from zoneinfo import ZoneInfo
from playwright.sync_api import TimeoutError as PWTimeoutError


APPLY_FILTER_BTN = "button.fApp[onclick='fVa();'], button.fApp[title*='Appliquer le filtre']"
DATE_INF_SEL = "input[id^='sel_dt_creation_borne_inf']"
DATE_SUP_SEL = "input[id^='sel_dt_creation_borne_sup']"
PARIS = ZoneInfo("Europe/Paris")
ORDERS_URL = "https://xnet-apps.com/xa/victorias/"  # ou URL directe "Commandes" si tu l'as


def parse_dt(text: str) -> datetime:
    s = " ".join(text.split())
    m = re.search(r"(\d{1,2}/\d{1,2}/\d{2,4})\s+(\d{1,2}:\d{2})", s)
    if not m:
        raise ValueError(f"Date/heure non reconnue: {text!r}")
    d, t = m.group(1), m.group(2)
    fmt = "%d/%m/%Y %H:%M" if len(d.split("/")[-1]) == 4 else "%d/%m/%y %H:%M"
    return datetime.strptime(f"{d} {t}", fmt).replace(tzinfo=PARIS)


def parse_day(date_str: str) -> date:
    """
    Accepte plusieurs formats:
      - "DD/MM/YY"  ex: "23/12/25"
      - "DD/MM/YYYY" ex: "23/12/2025"
      - "YYYY-MM-DD" ex: "2025-12-23"
    """
    s = date_str.strip()
    for fmt in ("%d/%m/%y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        
        except ValueError:
            pass
    raise ValueError(f"Format de date invalide: {date_str!r} (attendu: DD/MM/YY, DD/MM/YYYY ou YYYY-MM-DD)")


def ensure_logged(page):
    # garde-fou simple : si on retombe sur login, state expiré
    if page.locator("input[type='password']").count() > 0:
        raise RuntimeError("Session expirée → régénère state.json (save_state.py).")


def fill_date_filter(page, target_day):
    # on filtre "Date-heure création ≥" au début de la journée cible
    print("Target day de la fonction fill_date_filter: ",target_day)
    value = target_day.strftime("%d/%m/%y") 
    label = page.locator("text=Date-heure création ≥").first
    start_input = label.locator("xpath=following::input[1]").first
    start_input.click()
    start_input.fill(value)
    apply_filters(page)


    # idéalement remplacer par un wait sur un loader / refresh si tu as un sélecteur
    page.wait_for_timeout(2000)


def get_row_locators(page):
    candidates = [
        page.locator("table tbody tr"),
        page.locator("[role='rowgroup'] [role='row']"),
        page.locator("[role='row']"),
    ]
    for loc in candidates:
        if loc.count() > 0:
            return loc
    return candidates[0]

def is_linguaskill_anywhere(row) -> bool:
    try:
        cell = row.locator('td[data-p="velart_id"] span').first
        text = cell.inner_text().strip()
        return text == "LINGUASKILL Anywhere"
    except Exception:
        return False

def extract_order_url_from_row(row) -> str | None:
    # On lit l'attribut "itemid" sur la ligne, par ex: "CMD19713"
    itemid = row.get_attribute("itemid")
    if not itemid:
        print("Aucun itemid sur cette ligne, on la saute.")
        return None

    url = (
        "https://xnet-apps.com/vs/commun/imprimer.php"
        "?ca=victorias"
        "&p=detail.php%3Fmode%3DC%26cat%3Dvelcmd"
        f"%26id%3D{itemid}%26fdo%3D1%26vueDest%3Dvlt%26o%3Do1"
    )
    return url

def _force_clear_input(locator):
    locator.wait_for(state="visible", timeout=10_000)
    locator.click(force=True)

    locator.press("ControlOrMeta+A")
    locator.press("Backspace")
    locator.press("Delete")

    # Double sécurité : force la value côté DOM + events
    locator.evaluate(
        """el => {
            el.value = '';
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        }"""
    )

def apply_filters(page):
    btn = page.locator(APPLY_FILTER_BTN).first
    btn.wait_for(state="visible", timeout=10_000)
    btn.click()
    # Attendre que le rafraîchissement soit fini (adaptable selon ton appli)
    page.wait_for_load_state("networkidle")

def clear_prefilled_creation_date(page):
    inf = page.locator(DATE_INF_SEL).first
    if inf.count() > 0:
        _force_clear_input(inf)

    sup = page.locator(DATE_SUP_SEL).first
    if sup.count() > 0:
        _force_clear_input(sup)
    
    apply_filters(page)





# def extract_order_url_from_row(row, page) -> str | None:
#     num_cell = row.locator("text=/\\b\\d{2}-\\d{3,}\\b/").first
#     num_cell.click(force=True, timeout=5000)
#     # row.click(force=True, timeout=5000)

#     panel = page.locator("div.drBloc.scrB[style*='display: block']")
#     btn = panel.locator("a[onclick*='imprimer']").nth(0)

#     with page.expect_popup() as popup_info:
#         btn.click(force=True)
#         popup = popup_info.value
#         popup.wait_for_load_state()
#         url = popup.url
#         popup.close()

#         try:
#             back_btn = page.locator('button.btnListe[title*="Aller à la liste [←]"]').first
#             back_btn.click()
#             page.wait_for_load_state()
#         except Exception as e:
#             print(f"Impossible de revenir à la liste des commandes : {e}")

#     return url

# FAIRE BOUCLE WHILE POUR TROUVER TOUTES LES BONNES LIGNES

def get_today_order_urls(context, date_str) -> list[str]:
    """
    Retourne les URLs des commandes pour une journée donnée.
    - si date_str est fourni -> cette journée
    - sinon -> aujourd'hui (Europe/Paris)
    """
    target_day = parse_day(date_str) 
    print("Target day =", target_day)

    page = context.new_page()
    page.goto(ORDERS_URL, wait_until="domcontentloaded")
    ensure_logged(page)

    page.locator("#btnVN").click()
    page.locator("text=Commandes >> visible=true").first.click()

    page.get_by_text("Commandes", exact=True).first.wait_for(state="visible", timeout=30_000)
    print("Page Commandes ouverte | URL =", page.url)

    page.wait_for_timeout(2000)

    clear_prefilled_creation_date(page)

    #fill_date_filter(page, target_day)
    fill_date_filter(page, target_day) #PROBLEME DANS CETTE FONCTION PARFOIS IL ME SEMBLE 
    rows = get_row_locators(page)

    urls = []
    print("Nombre de lignes trouvées : ", rows.count())
    for i in range(rows.count()):
        row = rows.nth(i)

        try:
            dt = parse_dt(row.inner_text())
            print(dt.date())
        except Exception:
            continue

        if dt.date() != target_day:
            continue
    
        if not is_linguaskill_anywhere(row):
            continue

        url = extract_order_url_from_row(row)
        if url:
            urls.append(url)
        
    seen = set()
    urls = [u for u in urls if not (u in seen or seen.add(u))]

    page.close()
    return urls
