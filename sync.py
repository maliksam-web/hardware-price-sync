import os
import time
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
    print("🚀 Booting heavy-load background cloud browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 720})
        page = context.new_page()

        try:
            # 1. Login
            page.goto(PORTAL_URL, timeout=90000)
            page.wait_for_selector(USER_BOX, timeout=20000)
            page.fill(USER_BOX, USERNAME)
            page.fill(PASS_BOX, PASSWORD)
            page.click(LOGIN_BTN)
            page.wait_for_load_state("networkidle")
            print("🔒 Logged in successfully.")

            # 2. Open products page
            print("⏳ Navigating to products dashboard...")
            page.goto(ITEMS_TABLE_URL, timeout=180000)
            page.wait_for_selector("table", timeout=60000)

            # 3. Increase "entries per page" to the largest option available
            try:
                select_element = page.locator("select").first
                options = select_element.locator("option").all_text_contents()
                print(f"📐 Page-size options found: {options}")

                best_value = None
                best_num = -1
                for opt in options:
                    opt_clean = opt.strip()
                    if opt_clean.lower() == "all":
                        best_value = opt_clean
                        break
                    if opt_clean.replace(",", "").isdigit():
                        num = int(opt_clean.replace(",", ""))
                        if num > best_num:
                            best_num = num
                            best_value = opt_clean

                if best_value:
                    select_element.select_option(label=best_value)
                    print(f"✅ Set entries per page to: {best_value}")
                    page.wait_for_timeout(3000)
            except Exception as e:
                print(f"⚠️ Could not adjust page size: {e}")

            # 4. Loop through every pagination page and collect rows
            all_rows = []
            page_num = 1
            previous_first_name = None

            while True:
                print(f"📜 Scraping page {page_num}...")
                page.wait_for_timeout(2000)

                table_html = page.locator("table").first.inner_html()
                df_list = pd.read_html(f"<table>{table_html}</table>")
                raw_df = df_list[0]

                if "Name" in raw_df.columns:
                    raw_df = raw_df[raw_df["Name"] != "Name"]
                    raw_df = raw_df.dropna(subset=["Name"])

                current_first_name = raw_df["Name"].iloc[0] if len(raw_df) > 0 else None

                # If table content hasn't changed from the previous page, wait longer and re-read
                if page_num > 1 and current_first_name == previous_first_name:
                    print("   ⏳ Table not yet updated, waiting longer...")
                    page.wait_for_timeout(4000)
                    table_html = page.locator("table").first.inner_html()
                    df_list = pd.read_html(f"<table>{table_html}</table>")
                    raw_df = df_list[0]
                    if "Name" in raw_df.columns:
                        raw_df = raw_df[raw_df["Name"] != "Name"]
                        raw_df = raw_df.dropna(subset=["Name"])
                    current_first_name = raw_df["Name"].iloc[0] if len(raw_df) > 0 else None

                all_rows.append(raw_df)
                previous_first_name = current_first_name
                print(f"   -> {len(raw_df)} rows collected on this page (first item: {current_first_name}).")

                # Check the "Next" pagination button
                next_li = page.locator("li.paginate_button.next, .paginate_button.next").first
                if next_li.count() == 0:
                    print("⚠️ No next button found. Ending pagination.")
                    break

                classes = next_li.get_attribute("class") or ""
                if "disabled" in classes:
                    print("✅ Reached the last page.")
                    break

                next_li.click()
                page_num += 1

                if page_num > 250:
                    print("⚠️ Safety cap reached, stopping pagination loop.")
                    break

            # 5. Combine, dedupe, and save
            full_df = pd.concat(all_rows, ignore_index=True)
            print(f"📋 Total rows collected across all pages (before dedupe): {len(full_df)}")

            salesman_view = full_df[["Name", "Quantity", "Purchase Price", "Sale Price"]].copy()
            salesman_view.columns = ["Item Name", "Stock Quantity", "Purchase Price", "Retail Price"]
            salesman_view = salesman_view.dropna(subset=["Item Name"])
            salesman_view = salesman_view.drop_duplicates(subset=["Item Name"], keep="first")

            salesman_view.to_excel("salesman_prices.xlsx", index=False)
            print(f"✅ 'salesman_prices.xlsx' fully populated with {len(salesman_view)} hardware rates!")

        except Exception as error_log:
            print(f"❌ Processing interruption: {error_log}")
            if not os.path.exists("salesman_prices.xlsx"):
                df_err = pd.DataFrame([{
                    "Item Name": "System updating, please check back shortly.",
                    "Stock Quantity": 0,
                    "Purchase Price": 0,
                    "Retail Price": 0
                }])
                df_err.to_excel("salesman_prices.xlsx", index=False)
        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    run_scraper()
