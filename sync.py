import os
import time
from playwright.sync_api import sync_playwright
import pandas as pd

# --- FIXED TARGET CONFIGURATION ---
PORTAL_URL = "https://hafizhardware.bahestech.com"
ITEMS_TABLE_URL = "https://hafizhardware.bahestech.com/admin/products" 

USERNAME = os.environ.get('STORE_USER')
PASSWORD = os.environ.get('STORE_PASS')

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
            # 1. Open the login page
            page.goto(PORTAL_URL, timeout=60000)
            page.wait_for_load_state("networkidle")
            
            # 2. Type login credentials and enter portal
            page.fill(USER_BOX, USERNAME)
            page.fill(PASS_BOX, PASSWORD)
            page.click(LOGIN_BTN)
            page.wait_for_load_state("networkidle")
            print("🔒 Logged in successfully.")
            
            # 3. Direct travel to the admin products listing table
            page.goto(ITEMS_TABLE_URL, timeout=60000)
            page.wait_for_load_state("networkidle")
            
            # Wait for the database table to fully render on the screen
            page.wait_for_selector("table", timeout=20000)
            print("📋 Admin product table found.")
            
            # 4. Grab the raw table content
            table_html = page.locator("table").first.inner_html()
            df_list = pd.read_html(f"<table>{table_html}</table>")
            raw_df = df_list[0]
            
            print("Detected Columns:", list(raw_df.columns))
            
            # --- INTELLIGENT COLUMN MATCHING ---
            # Automatically extracts product title and selling price keywords.
            # This completely drops sensitive purchase rates and quantities out of the script.
            name_col = [col for col in raw_df.columns if 'name' in str(col).lower() or 'product' in str(col).lower()][0]
            price_col = [col for col in raw_df.columns if 'sale' in str(col).lower() or 'price' in str(col).lower() and 'purchase' not in str(col).lower()][0]
            
            salesman_view = raw_df[[name_col, price_col]]
            salesman_view.columns = ["Item Name", "Retail Price"]
            
            # 5. Export clean sheet for the Streamlit app
            salesman_view.to_excel("salesman_prices.xlsx", index=False)
            print("✅ File 'salesman_prices.xlsx' created successfully!")
            
        except Exception as error_log:
            print(f"❌ Processing interruption: {error_log}")
        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    run_scraper()
            
