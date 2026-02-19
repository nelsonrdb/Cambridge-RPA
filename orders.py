import re
from datetime import datetime, date
from zoneinfo import ZoneInfo
from playwright.sync_api import TimeoutError as PWTimeoutError
from get_data import main as get_data


APPLY_FILTER_BTN = "button.fApp[onclick='fVa();'], button.fApp[title*='Appliquer le filtre']"
DATE_INF_SEL = "input[id^='sel_dt_creation_borne_inf']"
DATE_SUP_SEL = "input[id^='sel_dt_creation_borne_sup']"
PARIS = ZoneInfo("Europe/Paris")
ORDERS_URL = "https://xnet-apps.com/xa/victorias/" 


def parse_dt(text: str) -> datetime:
    s = " ".join(text.split())
    m = re.search(r"(\d{1,2}/\d{1,2}/\d{2,4})\s+(\d{1,2}:\d{2})", s)
    if not m:
        raise ValueError(f"Date/heure non reconnue: {text!r}")
    d, t = m.group(1), m.group(2)
    fmt = "%d/%m/%Y %H:%M" if len(d.split("/")[-1]) == 4 else "%d/%m/%y %H:%M"
    return datetime.strptime(f"{d} {t}", fmt).replace(tzinfo=PARIS)


def parse_day(date_str: str) -> date:
    if date_str:
        s = date_str.strip()
        for fmt in ("%d/%m/%y", "%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(s, fmt).date()
            
            except ValueError:
                pass
        raise ValueError(f"Format de date invalide: {date_str!r} (attendu: DD/MM/YY, DD/MM/YYYY ou YYYY-MM-DD)")
    return None


def ensure_logged(page):
    # garde-fou simple : si on retombe sur login, state expiré
    if page.locator("input[type='password']").count() > 0:
        raise RuntimeError("Session expirée → régénère state.json (save_state.py).")
    
def clear_all_filters(page): 
    page.get_by_title("Effacer le filtre (et afficher tous les éléments)").first.click()

def fill_status_filter(page): 
    sel = page.locator("#sel_etat_id_1choix_0")
    sel.wait_for(state="attached", timeout=3000)
    sel.select_option(label="Réglée")


def fill_date_filter(page, start_day, end_day):
    value = start_day.strftime("%d/%m/%Y") #on veut toutes les commandes après une certaine date
    try:
        label = page.locator("text=Date-heure création ≥").first
        label.wait_for(state="visible", timeout=1500)
    except PWTimeoutError:
        label = page.locator("text=≥").first
        label.wait_for(state="visible", timeout=1500)
        
    start_input = label.locator("xpath=following::input[1]").first
    start_input.click()
    start_input.fill(value)
    if end_day: 
        try:
            labell = page.locator("text=Date-heure création ≤").first
            labell.wait_for(state="visible", timeout=1500)
        except PWTimeoutError:
            labell = page.locator("text=≤").first
            labell.wait_for(state="visible", timeout=1500)
            
        start_input = labell.locator("xpath=following::input[1]").first
        start_input.click()
        start_input.fill(value)
    apply_filters(page)
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


def _force_clear_input(locator):
    locator.wait_for(state="visible", timeout=10_000)
    locator.click(force=True)

    locator.press("ControlOrMeta+A")
    locator.press("Backspace")
    locator.press("Delete")

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
    page.wait_for_load_state("networkidle")

def clear_prefilled_creation_date(page):
    inf = page.locator(DATE_INF_SEL).first
    if inf.count() > 0:
        _force_clear_input(inf)

    sup = page.locator(DATE_SUP_SEL).first
    if sup.count() > 0:
        _force_clear_input(sup)
    apply_filters(page)


def extract_data(context, start_str, end_str) -> list[str]:
    start_day = parse_day(start_str) 
    end_day = parse_day(end_str)

    page = context.new_page()
    page.goto(ORDERS_URL, wait_until="domcontentloaded")
    ensure_logged(page)
    page.wait_for_timeout(500)  
    page.locator("#btnVN").first.click()
    page.wait_for_timeout(500)  
    page.keyboard.type("Commandes", delay=30)
    page.keyboard.press("Enter")
    page.wait_for_timeout(500)


    clear_all_filters(page)
    fill_status_filter(page)
    fill_date_filter(page, start_day, end_day) 
    result = get_data(page)

    page.close()
    return result 
