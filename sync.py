import os
import json
from playwright.sync_api import sync_playwright
import pandas as pd

PORTAL_URL = "https://hafizhardware.bahestech.com"
ITEMS_TABLE_URL = "https://hafizhardware.bahestech.com/admin/products" 

USERNAME = os.environ.get('STORE_USER')
PASSWORD = os.environ.get('STORE_PASS')

USER_BOX = "input[placeholder='Enter E-mail']"      
PASS_BOX = "input[placeholder='Enter Password']"   
LOGIN_BTN = "button:has-text('Login'), input[type='submit']"  

def run_scraper():
    print("🚀 Booting real-time network data interceptor...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 720})
        page = context.new_page()
        
        # Container to hold the raw product data stream when detected
        captured_data = []

        # This listener watches background network traffic for product lists
        def handle_response(response):
            # Checks if the background network request path contains product keywords
            if "product" in response.url.lower() and ("json" in response.headers.get("content-type", "") or "javascript" in response.headers.get("content-type", "")):
                try:
                    data = response.json()
                    # Standard structural checks for datatable payloads
                    if isinstance(data, list):
                        captured_data.extend(data)
                    elif isinstance(data, dict) and "data" in data:
                        captured_data.extend(data["data"])
                except Exception:
                    pass

        # Attach our background traffic listener
        page.on("response", handle_response)

        try:
            # 1. Log into your Bahes Tech portal session
            page.goto(PORTAL_URL, timeout=60000)
            page.wait_for_selector(USER_BOX, timeout=15000)
            page.fill(USER_BOX, USERNAME)
            page.fill(PASS_BOX, PASSWORD)
            page.click(LOGIN_BTN)
            page.wait_for_load_state("networkidle")
            
            # 2. Go to your products list path
            page.goto(ITEMS_TABLE_URL, timeout=60000)
            page.wait_for_load_state("networkidle")
            print("📡 Monitoring data channels...")
            
            # 3. Process the live background stream data matrix
            if captured_data:
                raw_df = pd.DataFrame(captured_data)
                print("Intercepted keys:", list(raw_df.columns))
                
                # Match properties dynamically from your backend API database keys
                name_key = [k for k in raw_df.columns if 'name' in str(k).lower() or 'title' in str(k).lower()][0]
                price_key = [k for k in raw_df.columns if 'sale' in str(k).lower() or 'price' in str(k).lower() and 'purchase' not in str(k).lower()][0]
                
                salesman_view = raw_df[[name_key, price_key]]
                salesman_view.columns = ["Item Name", "Retail Price"]
                
                # Save data rows instantly
                salesman_view.to_excel("salesman_prices.xlsx", index=False)
                print(f"✅ Success! Processed {len(salesman_view)} items directly via background data feed.")
            else:
                # Fallback if API layout is restricted: Read visual components
                print("⚠️ Direct API stream hidden. Reverting to automated page reader parsing...")
                table_html = page.locator("table").first.inner_html()
                df_list = pd.read_html(f"<table>{table_html}</table>")
                raw_df = df_list[0]
                
                salesman_view = raw_df.iloc[:, [1, 5]] # Grabs Name and Sale Price positions directly
                salesman_view.columns = ["Item Name", "Retail Price"]
                salesman_view.to_excel("salesman_prices.xlsx", index=False)
                print(f"✅ Extracted visually rendered rows instead.")
                
        except Exception as error_log:
            print(f"❌ Execution alert: {error_log}")
            # Ensure workspace stays operational with safe placeholder
            if not os.path.exists("salesman_prices.xlsx"):
                pd.DataFrame([{"Item Name": "Sync running...", "Retail Price": 0}]).to_excel("salesman_prices.xlsx", index=False)
        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    run_scraper()
    
