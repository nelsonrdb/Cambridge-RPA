import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from playwright.sync_api import TimeoutError as PWTimeoutError

load_dotenv()

INSTITUTION = os.getenv("CAMBRIDGE_INSTITUTION", "FR731")
BASE_URL = "https://www.metritests.com/metrica/"
ENTRY_URL = BASE_URL  # the site's plain entry page — no institution param
SESSIONS_URL = f"{BASE_URL}sessions.aspx?institution={INSTITUTION}"

DATA_DIR = os.getenv("DATA_DIR", ".")
STATE_PATH = os.getenv("CAMBRIDGE_STATE_PATH", os.path.join(DATA_DIR, "cambridge_state.json"))
USERNAME = os.getenv("CAMBRIDGE_USERNAME")
PASSWORD = os.getenv("CAMBRIDGE_PASSWORD")


VIEWPORT = {"width": 1600, "height": 1000}

# Render kills the whole container (no traceback, just a restart) when it
# exceeds its memory limit, and Chromium is by far the biggest consumer.
# --disable-dev-shm-usage: Docker's /dev/shm is tiny, Chromium otherwise
# spills shared memory in ways that count against the container.
CHROMIUM_ARGS = [
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-extensions",
]

# Nothing in the flow depends on images, fonts or media; skipping them
# keeps each Metrica page (already heavy ASP.NET WebForms) much lighter.
# CSS is kept: visibility checks rely on it.
_BLOCKED_RESOURCES = {"image", "media", "font"}
# Third-party telemetry (Google Analytics/Tag Manager, Application
# Insights) fires on every page and keeps the network busy for nothing.
_BLOCKED_HOSTS = ("google-analytics.com", "googletagmanager.com", "visualstudio.com", "applicationinsights")


def _block_heavy_resources(route):
    if route.request.resource_type in _BLOCKED_RESOURCES or any(
        host in route.request.url for host in _BLOCKED_HOSTS
    ):
        route.abort()
    else:
        route.continue_()


def open_context(p, headless: bool = True):
    # "--start-maximized" + viewport=None only maximizes a real window in
    # headed mode; headless has no window to maximize, which left elements
    # positioned outside a near-empty viewport. Always set an explicit
    # viewport instead so layout is consistent in both modes.
    launch_args = CHROMIUM_ARGS + (["--start-maximized"] if not headless else [])
    browser = p.chromium.launch(headless=headless, args=launch_args)
    if os.path.exists(STATE_PATH):
        context = browser.new_context(storage_state=STATE_PATH, viewport=VIEWPORT)
    else:
        context = browser.new_context(viewport=VIEWPORT)
    context.route("**/*", _block_heavy_resources)
    page = context.new_page()
    return browser, context, page


def is_login_page(page) -> bool:
    return page.get_by_label("Password").count() > 0


def login_and_refresh_state(page, context):
    if not USERNAME or not PASSWORD:
        raise RuntimeError(
            "CAMBRIDGE_USERNAME / CAMBRIDGE_PASSWORD are not set (see .env)."
        )

    # A stale/expired cambridge_state.json loaded into this context can
    # leave old session cookies behind that conflict with a fresh login —
    # seen live: login appears to succeed (the "Sessions" link briefly
    # shows up) but the very next navigation bounces back to the login
    # page. This site also seems to allow only one active session per
    # account, which makes a leftover cookie especially likely to clash.
    # Clear cookies first so a fresh login starts from a clean slate.
    context.clear_cookies()

    # Start from the site's plain entry page, like a real user would —
    # not a deep link with the institution baked into the query string.
    # The Institution ID field is filled explicitly instead.
    page.goto(ENTRY_URL, wait_until="domcontentloaded")
    page.get_by_label("Username").fill(USERNAME)
    page.get_by_label("Password").fill(PASSWORD)
    page.get_by_label("Institution ID").fill(INSTITUTION)
    page.get_by_role("button", name="Log in").click()

    try:
        page.get_by_role("link", name="Sessions").wait_for(state="visible", timeout=6000)
    except PWTimeoutError:
        # Surface whatever the site actually says instead of a generic
        # timeout — could be bad credentials, wrong institution ID, an
        # account lockout, a maintenance banner, etc.
        error_text = page.locator(
            ".validation-summary-errors, .field-validation-error, "
            "[class*='error'], [class*='alert']"
        ).all_inner_texts()
        error_text = [t.strip() for t in error_text if t.strip()]
        still_on_login = is_login_page(page)
        raise RuntimeError(
            "Cambridge login failed. "
            f"Still on login page: {still_on_login}. "
            f"URL: {page.url}. "
            f"Page error message(s): {error_text or 'none found'}."
        )

    context.storage_state(path=STATE_PATH)


def ensure_logged_in(p, headless: bool = True):
    browser, context, page = open_context(p, headless=headless)
    page.goto(ENTRY_URL, wait_until="domcontentloaded")

    if is_login_page(page):
        login_and_refresh_state(page, context)

    page.goto(SESSIONS_URL, wait_until="domcontentloaded")

    # Login can look like it succeeded (the "Sessions" link briefly
    # visible right after submitting) and still bounce back to the login
    # page on the very next navigation — seen live with a stale cookie.
    # One retry with a fully clean context resolves it; if it doesn't,
    # something else is genuinely wrong and this should fail loudly.
    if is_login_page(page):
        login_and_refresh_state(page, context)
        page.goto(SESSIONS_URL, wait_until="domcontentloaded")
        if is_login_page(page):
            raise RuntimeError(
                "Logged in but got bounced back to the login page when "
                f"navigating to {SESSIONS_URL}. URL: {page.url}."
            )

    return browser, context, page


if __name__ == "__main__":
    with sync_playwright() as p:
        browser, context, page = ensure_logged_in(p, headless=False)
        print("Logged in:", page.url)
        browser.close()
