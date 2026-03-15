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

def set_status_and_comment(page, info): 
    page.wait_for_timeout(500)
    menu_button = page.locator('button.btn.btn-default.btn-sm.mrBtn.noPicto')
    menu_button.click()
    page.locator('a[title="Revenir ou aller à un statut workflow"]').click()
    if info[2]:
        page.wait_for_timeout(2000)

        page.locator('select[name="velcmdwftrid"]').select_option('24')
        textarea = page.locator('textarea[name="wfcmt"]')

        textarea.fill(
            f"Username : {info[0]}\n"
            f"Password : {info[1]}\n"
            f"Institution : FR731"
        )
    else:
        page.locator('select[name="velcmdwftrid"]').select_option('3')
    
    # page.locator('button:has-text("Valider")').click()
    page.locator(BACK_BTN).click()



def go_to_order(page, order_number):
    search_input = page.locator('input[name="_rr"]')
    search_input.wait_for(state="visible")
    page.wait_for_timeout(500)
    search_input.type(order_number, delay=100)
    page.wait_for_timeout(500)
    page.keyboard.press("Enter") 


#FONCTION DEV MODE
# order_list = {order_number : [email, password, sucess_bool]}
def main(order_info, headless=False):
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

if __name__ =="__main__": 
    main({"26-0780": ['rdbnelson@gmail.com', 'hello world', True], "26-0777": ["rdbnelson@gmail.com", 'hello word', True]})








                
                  