# -*- coding: utf-8 -*-
import os
import sys
import time
import json
import requests
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging
from colorama import Fore, Style, init

# **************************** تنظیمات اختصاصی شما ****************************
CLIENT_ID = "13033_M8IkwDf3bgxbXxqHNCUobKmtznaZzx3nCv46cMndmWpNtk6qfk"
CLIENT_SECRET = "nVxlPQ0VrNYhSosFD0rboL7wnowxSD3s1e4aFciGSeWymOjKeI"
ACCOUNT_ID = 4986419
SYMBOL_NAME = "EURUSD"
REDIRECT_URI = "https://connect.spotware.com/apps/13033/playground"
OUTPUT_FILE = "ctrader_historical_data.json"
# *****************************************************************************

# تنظیمات API
AUTH_URL = "https://connect.ctrader.com/oauth2/token"
BASE_API_URL = "https://api.ctrader.com/connect"
TIMEFRAMES = {
    "M1": "OneMinute",
    "M5": "FiveMinutes",
    "M15": "FifteenMinutes",
    "H1": "OneHour",
    "H4": "FourHours",
    "H12": "TwelveHours",
    "D1": "OneDay"
}
MAX_DAYS_PER_REQUEST = 30

init(autoreset=True)

logger = logging.getLogger("CtraderDataCollector")
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_formatter = logging.Formatter(Fore.CYAN + '[%(asctime)s] %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

class CtraderDataCollector:
    def __init__(self):
        self.session = requests.Session()
        self.access_token = None
        self.symbol_id = None

    def authenticate(self):
        """احراز هویت با اطلاعات شما"""
        try:
            logger.info(Fore.YELLOW + "در حال احراز هویت با سرور cTrader...")
            response = self.session.post(
                AUTH_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET
                },
                timeout=10
            )
            response.raise_for_status()
            self.access_token = response.json()["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
            logger.info(Fore.GREEN + "✓ احراز هویت موفقیت آمیز بود")
            return True
        except Exception as e:
            logger.error(Fore.RED + f"خطا در احراز هویت: {str(e)}")
            return False

    def get_symbol_id(self):
        """دریافت شناسه نماد EURUSD"""
        try:
            logger.info(Fore.YELLOW + f"در حال دریافت شناسه نماد {SYMBOL_NAME}...")
            response = self.session.get(
                f"{BASE_API_URL}/tradingaccounts/{ACCOUNT_ID}/symbols",
                timeout=10
            )
            response.raise_for_status()
            
            for symbol in response.json()["symbols"]:
                if symbol["name"].lower() == SYMBOL_NAME.lower():
                    self.symbol_id = symbol["id"]
                    logger.info(Fore.GREEN + f"✓ شناسه نماد یافت شد: {self.symbol_id}")
                    return True
            logger.error(Fore.RED + "✗ نماد مورد نظر یافت نشد")
            return False
        except Exception as e:
            logger.error(Fore.RED + f"خطا در دریافت شناسه نماد: {str(e)}")
            return False

    def fetch_historical_data(self, start_date, end_date):
        """دریافت داده‌های تاریخی با تنظیمات شما"""
        all_data = {}
        
        try:
            for timeframe, tf_value in TIMEFRAMES.items():
                logger.info(Fore.BLUE + f"در حال دریافت داده‌های {timeframe}...")
                data = []
                current_start = start_date
                
                while current_start < end_date:
                    current_end = min(current_start + relativedelta(days=MAX_DAYS_PER_REQUEST), end_date)
                    
                    params = {
                        "symbolId": self.symbol_id,
                        "timeframe": tf_value,
                        "from": int(current_start.timestamp() * 1000),
                        "to": int(current_end.timestamp() * 1000)
                    }
                    
                    response = self.session.get(
                        f"{BASE_API_URL}/marketdata/history",
                        params=params,
                        timeout=20
                    )
                    response.raise_for_status()
                    
                    candles = response.json().get("candles", [])
                    data.extend([{
                        "timestamp": c["timestamp"],
                        "datetime": datetime.utcfromtimestamp(c["timestamp"]/1000).isoformat() + "Z",
                        "open": c["open"],
                        "high": c["high"],
                        "low": c["low"],
                        "close": c["close"],
                        "volume": c["volume"]
                    } for c in candles])
                    
                    current_start = current_end + timedelta(seconds=1)
                    time.sleep(1.5)
                
                all_data[timeframe] = data
                logger.info(Fore.GREEN + f"✓ {len(data)} رکورد برای {timeframe} دریافت شد")
            
            return all_data
        except Exception as e:
            logger.error(Fore.RED + f"خطا در دریافت داده‌ها: {str(e)}")
            return None

    def save_data(self, data):
        """ذخیره داده‌ها با فرمت درخواستی"""
        try:
            output = {
                "meta": {
                    "account_id": ACCOUNT_ID,
                    "symbol": SYMBOL_NAME,
                    "client_id": CLIENT_ID,
                    "time_range": {
                        "start": data[list(data.keys())[0]][0]['datetime'],
                        "end": data[list(data.keys())[0]][-1]['datetime']
                    }
                },
                "data": data
            }
            
            with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
                json.dump(output, f, indent=4, ensure_ascii=False)
            
            logger.info(Fore.GREEN + f"✓ داده‌ها با موفقیت در {OUTPUT_FILE} ذخیره شدند")
            return True
        except Exception as e:
            logger.error(Fore.RED + f"خطا در ذخیره‌سازی: {str(e)}")
            return False

def main():
    collector = CtraderDataCollector()
    
    if not collector.authenticate():
        return
    
    if not collector.get_symbol_id():
        return
    
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2022, 12, 31)
    
    historical_data = collector.fetch_historical_data(start_date, end_date)
    
    if historical_data:
        collector.save_data(historical_data)

if __name__ == "__main__":
    main()
