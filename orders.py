from playwright.sync_api import TimeoutError as PWTimeoutError
from get_data import main as get_data


APPLY_FILTER_BTN = "button.fApp[onclick='fVa();'], button.fApp[title*='Appliquer le filtre']"
DATE_INF_SEL = "input[id^='sel_dt_creation_borne_inf']"
DATE_SUP_SEL = "input[id^='sel_dt_creation_borne_sup']"
ORDERS_URL = "https://xnet-apps.com/xa/victorias/" 

def ensure_logged(page):
    # garde-fou simple : si on retombe sur login, state expiré
    if page.locator("input[type='password']").count() > 0:
        raise RuntimeError("Session expirée → régénère state.json (save_state.py).")
    
def clear_all_filters(page, timeout= 10_000):
    locator = page.get_by_title("Effacer le filtre (et afficher tous les éléments)")
    if locator.count() == 0:
        return False

    btn = locator.first
    try:
        btn.wait_for(state="visible", timeout=timeout)
    except Exception:
        return False

    btn.scroll_into_view_if_needed()
    btn.click(timeout=timeout)
    return True

def fill_status_filter(page): 
    sel = page.locator("#sel_etat_id_1choix_0")
    sel.wait_for(state="visible", timeout=15000)
    sel.select_option(label="Réglée")

def fill_status_workflow_filter(page):
    sel = page.locator('div[xa-crit="velcmdwft_id"] select')
    sel.wait_for(state="visible", timeout=15000)
    sel.select_option(label="Code accès à envoyer")

def fill_date_filter(page, start_day, end_day):
    try:
        label = page.locator("text=Date-heure création ≥").first
        label.wait_for(state="visible", timeout=1500)
    except PWTimeoutError:
        label = page.locator("text=≥").first
        label.wait_for(state="visible", timeout=1500)
        
    start_input = label.locator("xpath=following::input[1]").first
    start_input.click()
    start_input.fill(start_day)
    if end_day: 
        try:
            labell = page.locator("text=Date-heure création ≤").first
            labell.wait_for(state="visible", timeout=1500)
        except PWTimeoutError:
            labell = page.locator("text=≤").first
            labell.wait_for(state="visible", timeout=1500)
            
        start_input = labell.locator("xpath=following::input[1]").first
        start_input.click()
        start_input.fill(end_day)
    apply_filters(page)
    page.wait_for_timeout(2000)

def apply_filters(page):
    btn = page.locator(APPLY_FILTER_BTN).first
    btn.wait_for(state="visible", timeout=10_000)
    btn.click()
    page.wait_for_load_state("networkidle")

def extract_data(context):#
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
    fill_status_workflow_filter(page)
    apply_filters(page)
    result = get_data(page)

    page.close()
    return result 
