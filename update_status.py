from playwright.sync_api import sync_playwright
from auth import ensure_logged_with_state
from playwright.sync_api import expect

BACK_BTN = 'button.btnListe[title*="Aller à la liste"]'



def go_to_commandes(page):
    page.locator("#btnVN").first.click()
    page.wait_for_timeout(500)  
    page.keyboard.type("Commandes", delay=30)
    page.keyboard.press("Enter")
    page.wait_for_timeout(500)

def set_status_and_comment(page, order_info): 
    page.locator('a[title="Revenir ou aller à un statut workflow"]').click()
    if order_info["is_enrolled"]:
        page.locator('select[name="velcmdwftrid"]').selectOption('24')
        textarea = page.locator('textarea[name="wfcmt"]')

    textarea.fill(
        f"Username : {order_info['email']}\n"
        f"Password : {order_info['password']}\n"
        f"Institution : FR731"
    )
    else:
        page.locator('select[name="velcmdwftrid"]').selectOption('3')
    
    page.locator('button:has-text("Valider")').click()
    page.locator(BACK_BTN).click()



def go_to_order(page, order_number):
    search_input = page.locator('input[name="_rr"]')
    search_input.wait_for(state="visible")
    search_input.fill(order_number)
    page.keyboard.press("Enter") 
            
    
#FONCTION DEV MODE
# order_list = {order_number : [email, password, sucess_bool]}
def main(headless=False, order_list):
        with sync_playwright() as p:
            browser, context, page = ensure_logged_with_state(p, headless=headless)
            try:
                go_to_commandes(page)
                for order in order_list:
                    go_to_order(page, order_info[])
                    set_status_and_comment(page, order_info)

        print("CMS Workflow commenté")








                
                  