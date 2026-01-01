from playwright.sync_api import sync_playwright
from playwright.sync_api import TimeoutError as PWTimeoutError


BASE_URL = "https://xnet-apps.com/xa/victorias/"
STATE_PATH = "./state.json"

USERNAME = "Examens"
PASSWORD = "7Lin8gua!"


def open_context(p, headless: bool = False):
    browser = p.chromium.launch(headless=headless)
    context = browser.new_context(storage_state=STATE_PATH)
    page = context.new_page()
    return browser, context, page

def is_login_page(page) -> bool:
    return page.locator('input[name="pwd"], input[type="password"]').count() > 0

def login_and_refresh_state(page, context):
    page.wait_for_selector('input[name="login"]', state="visible", timeout=20000)
    page.fill('input[name="login"]', USERNAME)
    page.fill('input[name="pwd"]', PASSWORD)
    page.click("#btnCnx")

    # Attendre signe de succès
    try:
        page.wait_for_selector("text=Commandes", timeout=20000)
    except PWTimeoutError:
        raise RuntimeError("Login échoué (identifiants / 2FA / sélecteurs).")

    context.storage_state(path=STATE_PATH)

def ensure_logged_with_state(p, headless: bool = False):
    browser, context, page = open_context(p, headless=headless)

    page.goto(BASE_URL, wait_until="domcontentloaded")

    if is_login_page(page):
        print("⚠️ state.json expiré → login auto + refresh state.json")
        login_and_refresh_state(page, context)

    return browser, context, page