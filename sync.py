import os
import time
from playwright.sync_api import sync_playwright
import pandas as pd

# --- TARGET CONFIGURATION ---
# Change this URL path to the exact link where your store items table is located
PORTAL_URL = "https://hafizhardware.bahestech.com"
ITEMS_TABLE_URL = "https://hafizhardware.bahestech.com/your-actual-items-page-path"

# Retrieve encrypted secrets safely from the cloud vault
USERNAME = os.environ.get('STORE_USER')
PASSWORD = os.environ.get('STORE_PASS')

# Target element names found on the login page screen 
USER_BOX = "input[type='email']"      
PASS_BOX = "input[type='password']"   
LOGIN_BTN = "button[type='submit']"  

def run_scraper():
    print("🚀 Booting background cloud server browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 720})
        page = context.new_page()
        
        try:
            # 1. Reach login panel
            page.goto(PORTAL_URL, timeout=60000)
            page.wait_for_load_state("networkidle")
            
            # 2. Complete secure sign-in execution
            page.fill(USER_BOX, USERNAME)
            page.fill(PASS_BOX, PASSWORD)
            page.click(LOGIN_BTN)
            page.wait_for_load_state("networkidle")
            print("🔒 Successfully authenticated portal session.")
            
            # 3. Direct navigate to stock table display
            page.goto(ITEMS_TABLE_URL, timeout=60000)
            page.wait_for_load_state("networkidle")
            page.wait_for_selector("table", timeout=20000)
            
            # 4. Extract target data structure from HTML container
            table_html = page.locator("table").first.inner_html()
            df_list = pd.read_html(f"<table>{table_html}</table>")
            raw_data_frame = df_list[0]
            
            # 5. Filter out backend configurations/costs, save only client visibility data
            # NOTE: Change 'Item Name' and 'Retail Price' to match your portal's exact table headers
            salesman_filtered_view = raw_data_frame[["Item Name", "Retail Price"]]
            
            # Export structured file
            salesman_filtered_view.to_excel("salesman_prices.xlsx", index=False)
            print("✅ Extracted fresh records successfully.")
            
        except Exception as error_log:
            print(f"❌ Processing interruption: {error_log}")
        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    run_scraper()
