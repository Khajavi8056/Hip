import os
import subprocess
import sys
import requests
import json
from datetime import datetime, timedelta

# نصب پیش‌نیازها
def install_requirements():
    try:
        print("Installing required libraries...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
        print("All libraries installed successfully!")
    except Exception as e:
        print("Error during installation:", e)
        sys.exit(1)

# تنظیمات اولیه
CLIENT_ID = "12908_yJI2u1U0U3EtTwmNKWbcNUGYK1FScECHN1wkMoYW5Wtjh1SQcX"
CLIENT_SECRET = "RCGFdieLNwFSC2gw720KiJpOcifXf7F8e6FVsl9oeJ1aypNv5w"
REDIRECT_URI = "https://connect.spotware.com/apps/12908/playground"
AUTH_URL = "https://connect.spotware.com/oauth2/token"
BASE_URL = "https://api.spotware.com/connect/tradingaccounts"

# تنظیمات داده
SYMBOL = "EURUSD"
TIMEFRAMES = ["D1", "H4", "H1", "M15", "M5", "M1"]
START_DATE = "2018-01-01"
END_DATE = "2023-01-01"

# دریافت Access Token
def get_access_token():
    try:
        data = {
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET
        }
        response = requests.post(AUTH_URL, data=data)
        response.raise_for_status()
        return response.json()["access_token"]
    except requests.exceptions.RequestException as e:
        print("Error during authentication:", e)
        sys.exit(1)

# دریافت داده‌های تاریخی
def get_historical_data(access_token, symbol, timeframe, start_date, end_date):
    headers = {"Authorization": f"Bearer {access_token}"}
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    result = []

    while start < end:
        next_start = start + timedelta(days=30)  # درخواست 30 روزه
        params = {
            "symbolName": symbol,
            "timeframe": timeframe,
            "startTime": start.isoformat() + "Z",
            "endTime": next_start.isoformat() + "Z"
        }
        url = f"{BASE_URL}/history/ohlc"
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            result.extend(response.json().get("candles", []))
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data for {timeframe}:", e)
        start = next_start
    return result

# دریافت داده‌های عمق بازار (Market Depth)
def get_market_depth(access_token, symbol):
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"{BASE_URL}/marketdepth"
    params = {"symbolName": symbol}
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json().get("depthEntries", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching market depth for {symbol}:", e)
        return []

# ذخیره داده‌ها در فرمت JSON
def save_to_json(data, filename):
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
        print(f"Data saved to {filename} successfully!")
    except Exception as e:
        print(f"Error saving data to {filename}:", e)

# اجرای کامل
def main():
    try:
        # نصب پیش‌نیازها
        install_requirements()

        # احراز هویت
        token = get_access_token()
        all_data = {}

        # جمع‌آوری داده‌ها برای همه تایم‌فریم‌ها
        for timeframe in TIMEFRAMES:
            print(f"Fetching historical data for {SYMBOL} - {timeframe}")
            historical_data = get_historical_data(token, SYMBOL, timeframe, START_DATE, END_DATE)
            all_data[timeframe] = {"historical_data": historical_data}

        # دریافت عمق بازار
        print(f"Fetching market depth for {SYMBOL}")
        market_depth_data = get_market_depth(token, SYMBOL)
        all_data["market_depth"] = market_depth_data

        # ذخیره در فایل JSON
        save_to_json(all_data, "historical_data_with_market_depth.json")

    except Exception as e:
        print("An error occurred during execution:", e)

# اجرای اسکریپت
if __name__ == "__main__":
    main()
