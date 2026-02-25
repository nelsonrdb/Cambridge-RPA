from playwright.sync_api import sync_playwright
from playwright.sync_api import TimeoutError as PWTimeoutError
import os

BASE_URL = "https://xnet-apps.com/xa/victorias/"
# STATE_PATH = os.getenv("STATE_PATH", "/tmp/state.json")
STATE_PATH = os.getenv("STATE_PATH", "state.json")
USERNAME = "Examens"
PASSWORD = "7Lin8gua!"

def open_context(p, headless: bool = True):
    browser = p.chromium.launch(headless=headless)
    if os.path.exists(STATE_PATH):
        context = browser.new_context(storage_state=STATE_PATH)
    else:
        context = browser.new_context()
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

def ensure_logged_with_state(p, headless = True):
    browser, context, page = open_context(p, headless=headless)
    safe_goto(page, BASE_URL)

    if is_login_page(page):
        print("⚠️ state.json expiré → login auto + refresh state.json")
        login_and_refresh_state(page, context)

    return browser, context, page

def safe_goto(page, url):
    for attempt in range(3):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=90000)
            return
        except Exception:
            if attempt == 2:
                raise
            page.wait_for_timeout(1000)