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

def set_status_and_comment(page, info_dic): 
    page.wait_for_timeout(1000)
    try:
        page.get_by_text("Statut WF", exact=False).click(timeout=3000)
    except:
        page.locator('button.btn.btn-default.btn-sm.mrBtn.noPicto').click()
        page.wait_for_timeout(500)
        try:
            page.get_by_text("Statut WF", exact=False).click(timeout=3000)
        except:
            raise Exception("Bouton 'Statut WF' introuvable")
    if info_dic["success"]: 
        page.wait_for_timeout(500)
        locator = page.locator('#champ_velcmdwftrid select')
        locator.select_option(label="Clôturer Session")
        textarea = page.locator('textarea[name="wfcmt"]')

        textarea.fill( 
            f"Username : {info_dic["email"]}\n"
            f"Password : {info_dic["password"]}\n"
            f"Institution : FR731"
        )
    else:
        page.locator('select[name="velcmdwftrid"]').select_option('MANUEL')
    
    page.locator('button:has-text("Valider")').click()
    page.locator(BACK_BTN).click()



def go_to_order(page, order_number):
    search_input = page.locator('input[name="_rr"]')
    search_input.wait_for(state="visible")
    page.wait_for_timeout(500)
    search_input.type(order_number, delay=100)
    page.wait_for_timeout(500)
    page.keyboard.press("Enter") 


#FONCTION DEV MODE
#order_list = {order_number : [email, password, sucess_bool]}
def main(order_info, headless=True):
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

if __name__ == "__main__":
    sample_dic = {'AD226-0004':{"email": "charlotte.aux.fraises@gmail.com", "password" : "AFZEFSL314", "sucess" : "True"}}
    main(sample_dic, headless=False)


               