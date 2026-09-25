from playwright.sync_api import TimeoutError as PWTimeoutError
from get_data import main as get_data, ROWS_SEL, wait_for_row_count_stable


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
    sel.select_option(label="Réglée", timeout=15000)

# Orders under either of these X-Net workflow statuses are picked up for
# Cambridge registration.
HANDLED_WORKFLOW_STATUSES = ("Code accès à envoyer", "Validé Manuellement")

def fill_status_workflow_filter(page, status_label):
    # Selecting "Réglée" just before makes X-Net redraw the whole filter
    # panel: this <select> is replaced by a new one that stays briefly
    # hidden/disabled (seen live on Render: resolved but "waiting for
    # element to be visible and enabled"). select_option() waits for
    # visible+enabled itself and re-resolves the locator, so give it an
    # explicit timeout instead of the page default (get_data.main() used
    # to leave that at 5s after the first status pass).
    sel = page.locator('div[xa-crit="velcmdwft_id"] select')
    sel.wait_for(state="visible", timeout=15000)
    sel.select_option(label=status_label, timeout=15000)

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
    """Apply the filters and wait until X-Net has actually swapped in the
    new result list. networkidle alone is not enough: seen live, the
    previous list (e.g. 200 unfiltered rows, or the previous status's
    rows) stays on screen for a moment after it resolves, and get_data
    would then count rows that are about to disappear."""
    # query_selector returns immediately: Locator.element_handle() would
    # wait (30s) for a visible row, and seen live on Render after a fresh
    # login the list was mid-redraw here, with no visible row at all.
    old_handle = page.query_selector(ROWS_SEL)

    btn = page.locator(APPLY_FILTER_BTN).first
    btn.wait_for(state="visible", timeout=10_000)
    btn.click(timeout=10_000)
    page.wait_for_load_state("networkidle")

    if old_handle is not None:
        try:
            page.wait_for_function("el => !el.isConnected", arg=old_handle, timeout=15_000)
        except PWTimeoutError:
            print("[WARN] old order list still attached after applying filters", flush=True)
    wait_for_row_count_stable(page)

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


    result = []
    for status_label in HANDLED_WORKFLOW_STATUSES:
        clear_all_filters(page)
        fill_status_filter(page)
        fill_status_workflow_filter(page, status_label)
        apply_filters(page)
        result.extend(get_data(page))

    page.close()
    return result 
