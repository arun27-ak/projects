import json
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
# ============================================================
# 1. COINGECKO API URL
# ============================================================
URL = (
    "https://api.coingecko.com/api/v3/coins/markets"
    "?vs_currency=inr"
    "&order=market_cap_desc"
    "&per_page=10"
    "&page=1"
    "&sparkline=false"
    "&price_change_percentage=24h"
)
# ============================================================
# 2. START SELENIUM / CHROME
# ============================================================
print("Starting Selenium...")
options = webdriver.ChromeOptions()
# Chrome will be visible
options.add_argument("--start-maximized")
# Prevent unnecessary notifications
options.add_argument("--disable-notifications")
driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)
# ============================================================
# 3. OPEN COINGECKO API
# ============================================================
print("Opening CoinGecko...")
driver.get(URL)
# Wait for the API response to load
time.sleep(5)
# ============================================================
# 4. READ JSON FROM THE PAGE
# ============================================================
try:
    page_text = driver.find_element(
        "tag name",
        "body"
    ).text
    print("Data received from CoinGecko!")
except Exception as error:
    print("Could not read data.")
    print(error)
    driver.quit()
    exit()
# ============================================================
# 5. CLOSE CHROME
# ============================================================
driver.quit()
print("Selenium browser closed.")
# ============================================================
# 6. CONVERT JSON TEXT TO PYTHON DATA
# ============================================================
try:
    data = json.loads(page_text)
except json.JSONDecodeError:
    print("The response is not valid JSON.")
    print(page_text)
    exit()
# ============================================================
# 7. CHECK DATA
# ============================================================
if not isinstance(data, list):
    print("Unexpected response from CoinGecko.")
    print(data)
    exit()
# ============================================================
# 8. EXTRACT TOP 10 CRYPTOCURRENCIES
# ============================================================
crypto_data = []
timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
for i, coin in enumerate(data[:10], start=1):
    crypto_data.append({
        "Rank": i,
        "Coin": coin.get("name"),
        "Symbol": coin.get("symbol", "").upper(),
        "Price (INR)": coin.get("current_price"),
        "24h Change (%)": coin.get("price_change_percentage_24h"),
        "Market Cap (INR)": coin.get("market_cap"),
        "24h High (INR)": coin.get("high_24h"),
        "24h Low (INR)": coin.get("low_24h"),
        "Timestamp": timestamp
    })
# ============================================================
# 9. CREATE DATAFRAME
# ============================================================
df = pd.DataFrame(crypto_data)
# ============================================================
# 10. DISPLAY DATA
# ============================================================
print()
print("=" * 80)
print("             CRYPTOCURRENCY PRICE TRACKER")
print("=" * 80)
print()
print(df.to_string(index=False))
# ============================================================
# 11. SAVE CURRENT DATA
# ============================================================
current_file = "crypto_prices.csv"
df.to_csv(
    current_file,
    index=False
)
print()
print("Current data saved to:")
print(current_file)
# ============================================================
# 12. SAVE HISTORICAL DATA
# ============================================================
history_file = "crypto_history.csv"
try:
    old_data = pd.read_csv(history_file)
    combined_data = pd.concat(
        [old_data, df],
        ignore_index=True
    )
except FileNotFoundError:
    combined_data = df
combined_data.to_csv(
    history_file,
    index=False
)
print("Historical data saved to:")
print(history_file)
# ============================================================
# 13. FINISHED
# ============================================================
print()
print("=" * 80)
print("                    PROJECT COMPLETED")
print("=" * 80)
print()
print("Total coins collected:", len(df))
print()