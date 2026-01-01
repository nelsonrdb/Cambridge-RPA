import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE_URL = "https://xnet-apps.com/xa/victorias/"
USERNAME = "Examens"
PASSWORD = "7Lin8gua!"

def main():
    if not USERNAME or not PASSWORD:
        raise SystemExit("❌ Mets XNET_USERNAME et XNET_PASSWORD en variables d'environnement.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.goto(BASE_URL, wait_until="domcontentloaded")

        page.locator('[name="login"]').wait_for(state="visible", timeout=15000)

        page.locator('[name="login"]').fill(USERNAME)
        page.locator('[name="pwd"]').fill(PASSWORD)

        page.locator("#btnCnx").click()

        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except PlaywrightTimeoutError:
            pass


        if page.locator('[name="login"]').count() > 0:
            print("⚠️ Le champ login est encore présent. Login peut avoir échoué (ou redirection lente/2FA).")

        context.storage_state(path="./state.json")
        print("✅ state.json sauvegardé")

        context.close()
        browser.close()

if __name__ == "__main__":
    main()