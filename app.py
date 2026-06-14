import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Hafiz Hardware Lookup", page_icon="🔍", layout="centered")

st.title("🔍 Hafiz Hardware Store")
st.subheader("Live Salesman Price Desk")

@st.cache_data(ttl=600)
def load_synced_data():
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(BASE_DIR, "salesman_prices.xlsx")
        return pd.read_excel(file_path)
    except Exception:
        st.error("Pricing database synchronization in progress. Try again in 1 minute.")
        return pd.DataFrame()

df = load_synced_data()

if not df.empty:
    search_keyword = st.text_input("Type product keyword below:", placeholder="e.g., pipe, watti, bolt...", autocomplete="off")

    if search_keyword:
        results = df[df["Item Name"].str.contains(search_keyword, case=False, na=False)]

        if not results.empty:
            st.dataframe(
                results,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Stock Quantity": st.column_config.NumberColumn("In Stock", format="%d"),
                    "Purchase Price": st.column_config.NumberColumn("Cost Price (Bargain Floor)", format="Rs. %d"),
                    "Retail Price": st.column_config.NumberColumn("Selling Price", format="Rs. %d")
                }
            )
        else:
            st.warning("No matched inventory found.")
    else:
        st.info("💡 Input a search term to display the current retail rate.")
