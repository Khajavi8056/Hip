# -*- coding: utf-8 -*-
import os
import sys
import time
import json
import requests
from datetime import datetime
from dateutil.relativedelta import relativedelta
from logging.handlers import RotatingFileHandler
import logging
from colorama import Fore, Style, init

# **************************** تنظیمات اصلی ****************************
CLIENT_ID = "your_client_id_here"             # کلاینت آیدی cTrader
CLIENT_SECRET = "your_client_secret_here"     # کلاینت سکرت cTrader
ACCOUNT_ID = "your_account_id_here"           # آیدی حساب cTrader
SYMBOL_NAME = "EURUSD"                        # نام نماد مورد نظر
OUTPUT_FILE = "ctrader_data_2020-2022.json"   # نام فایل خروجی

# تنظیمات بازه زمانی
START_DATE = datetime(2020, 1, 1)             # تاریخ شروع (سال، ماه، روز)
END_DATE = datetime(2022, 12, 31)             # تاریخ پایان (سال، ماه، روز)

# تنظیمات API (مطابق مستندات رسمی cTrader)
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
MAX_DAYS_PER_REQUEST = 30                     # مطابق محدودیت API cTrader
# **********************************************************************

# تنظیمات اولیه رنگ‌ها
init(autoreset=True)

# ************************** پیکربندی سیستم لاگ‌گیری **************************
logger = logging.getLogger("CtraderDataCollector")
logger.setLevel(logging.DEBUG)

# Handler برای فایل لاگ
file_handler = RotatingFileHandler(
    'ctrader_collector.log',
    maxBytes=10*1024*1024,
    backupCount=5,
    encoding='utf-8'
)
file_formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(module)s | %(message)s')
file_handler.setFormatter(file_formatter)

# Handler برای کنسول
console_handler = logging.StreamHandler()
console_formatter = logging.Formatter(Fore.CYAN + '[%(asctime)s] %(message)s')
console_handler.setFormatter(console_formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)
# ***************************************************************************

class CtraderDataCollector:
    def __init__(self):
        self.session = requests.Session()
        self.access_token = None
        self.symbol_id = None
        self.total_requests = 0
        self.start_time = None
        self.data = {
            "meta": {
                "symbol": SYMBOL_NAME,
                "account_id": ACCOUNT_ID,
                "date_range": {
                    "start": START_DATE.isoformat() + "Z",
                    "end": END_DATE.isoformat() + "Z"
                },
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "api_version": "2.1",
                "timeframes": list(TIMEFRAMES.keys())
            },
            "ohlcv": {},
            "market_depth": {}
        }

    def _print_progress(self, current, total, elapsed):
        """نمایش پیشرفت با نوار گرافیکی"""
        progress = current / total
        bar = '█' * int(50 * progress) + '-' * (50 - int(50 * progress))
        eta = (elapsed / current) * (total - current) if current > 0 else 0
        sys.stdout.write(
            f"\r{Fore.YELLOW}پیشرفت: |{bar}| "
            f"{progress:.1%} | زمان سپری شده: {self._format_time(elapsed)} "
            f"| زمان باقیمانده: {self._format_time(eta)}"
        )
        sys.stdout.flush()

    def _format_time(self, seconds):
        """فرمت‌دهی زمان به صورت خوانا"""
        return time.strftime("%H:%M:%S", time.gmtime(seconds)) if seconds >= 0 else "--:--:--"

    def _test_api_connection(self):
        """تست اتصال به API"""
        try:
            logger.info(Fore.BLUE + "بررسی اتصال به cTrader API...")
            response = self.session.get(f"{BASE_API_URL}/ping", timeout=10)
            if response.status_code == 200:
                logger.info(Fore.GREEN + "✓ اتصال به API با موفقیت برقرار شد")
                return True
            logger.error(Fore.RED + f"✗ خطا در اتصال API | کد وضعیت: {response.status_code}")
            return False
        except Exception as e:
            logger.critical(Fore.RED + f"✗ خطای بحرانی در اتصال: {str(e)}")
            return False

    def _get_access_token(self):
        """دریافت توکن دسترسی با تلاش مجدد"""
        for attempt in range(3):
            try:
                logger.info(Fore.BLUE + "دریافت توکن دسترسی...")
                response = self.session.post(
                    AUTH_URL,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": CLIENT_ID,
                        "client_secret": CLIENT_SECRET
                    },
                    timeout=15
                )
                response.raise_for_status()
                self.access_token = response.json()["access_token"]
                self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
                logger.info(Fore.GREEN + "✓ احراز هویت با موفقیت انجام شد")
                return True
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    retry_after = int(e.response.headers.get('Retry-After', 60))
                    logger.warning(f"⏳ محدودیت نرخ | تلاش مجدد پس از {retry_after} ثانیه...")
                    time.sleep(retry_after)
                else:
                    logger.error(Fore.RED + f"✗ خطای احراز هویت: {e.response.text}")
                    return False
            except Exception as e:
                logger.error(Fore.RED + f"✗ خطای ناشناخته در احراز هویت: {str(e)}")
                return False
        return False

    def _resolve_symbol(self):
        """تبدیل نام نماد به شناسه"""
        try:
            logger.info(Fore.BLUE + f"جستجوی شناسه برای نماد {SYMBOL_NAME}...")
            response = self.session.get(
                f"{BASE_API_URL}/tradingaccounts/{ACCOUNT_ID}/symbols",
                timeout=10
            )
            response.raise_for_status()
            
            for symbol in response.json()["symbols"]:
                if symbol["name"].lower() == SYMBOL_NAME.lower():
                    self.symbol_id = symbol["id"]
                    logger.info(Fore.GREEN + f"✓ شناسه نماد پیدا شد: {self.symbol_id}")
                    return True
            logger.error(Fore.RED + "✗ نماد پیدا نشد")
            return False
        except Exception as e:
            logger.error(Fore.RED + f"✗ خطا در دریافت شناسه نماد: {str(e)}")
            return False

    def _fetch_ohlcv(self, timeframe):
        """دریافت داده‌های تاریخی"""
        data = []
        current_start = START_DATE
        total_days = (END_DATE - START_DATE).days
        processed_days = 0
        
        logger.info(Fore.BLUE + f"شروع دریافت داده‌های {timeframe}...")
        
        while current_start < END_DATE:
            try:
                # مدیریت نرخ درخواست
                if self.total_requests >= 25:
                    logger.warning("⏳ نزدیک به محدودیت نرخ - مکث 60 ثانیه")
                    time.sleep(60)
                    self.total_requests = 0

                current_end = min(current_start + relativedelta(days=MAX_DAYS_PER_REQUEST), END_DATE)
                
                params = {
                    "symbolId": self.symbol_id,
                    "timeframe": TIMEFRAMES[timeframe],
                    "from": int(current_start.timestamp() * 1000),
                    "to": int(current_end.timestamp() * 1000),
                    "pageSize": 5000
                }

                response = self.session.get(
                    f"{BASE_API_URL}/marketdata/history",
                    params=params,
                    timeout=20
                )
                self.total_requests += 1

                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"⏳ محدودیت نرخ - تلاش مجدد پس از {retry_after} ثانیه")
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()
                
                candles = response.json().get("candles", [])
                for candle in candles:
                    data.append({
                        "ts": candle["timestamp"],
                        "dt": datetime.utcfromtimestamp(candle["timestamp"]/1000).isoformat() + "Z",
                        "o": candle["open"],
                        "h": candle["high"],
                        "l": candle["low"],
                        "c": candle["close"],
                        "v": candle["volume"]
                    })
                
                processed_days += (current_end - current_start).days
                elapsed = time.time() - self.start_time
                self._print_progress(processed_days, total_days, elapsed)
                
                current_start = current_end + relativedelta(seconds=1)
                time.sleep(1.5)

            except Exception as e:
                logger.error(Fore.RED + f"✗ خطا در دریافت داده‌ها: {str(e)}")
                break

        return data

    def _fetch_market_depth(self):
        """دریافت عمق بازار"""
        try:
            logger.info(Fore.BLUE + "دریافت عمق بازار...")
            response = self.session.get(
                f"{BASE_API_URL}/marketdata/depth/{self.symbol_id}",
                params={"levels": 10},
                timeout=15
            )
            response.raise_for_status()
            
            return {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "bids": [[entry["price"], entry["volume"]] for entry in response.json()["bids"]],
                "asks": [[entry["price"], entry["volume"]] for entry in response.json()["asks"]]
            }
        except Exception as e:
            logger.error(Fore.RED + f"✗ خطا در دریافت عمق بازار: {str(e)}")
            return None

    def _save_data(self):
        """ذخیره داده‌ها با اعتبارسنجی"""
        try:
            # اعتبارسنجی نهایی
            valid = True
            for tf in TIMEFRAMES:
                if not self.data["ohlcv"].get(tf):
                    logger.error(Fore.RED + f"✗ داده‌ای برای تایم‌فریم {tf} یافت نشد")
                    valid = False
            
            if valid:
                with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
                    json.dump(self.data, f, indent=4, ensure_ascii=False)
                logger.info(Fore.GREEN + f"✓ داده‌ها با موفقیت در {OUTPUT_FILE} ذخیره شدند")
                return True
            logger.error(Fore.RED + "✗ ذخیره‌سازی به دلیل داده‌های ناقص انجام نشد")
            return False
        except Exception as e:
            logger.error(Fore.RED + f"✗ خطا در ذخیره‌سازی: {str(e)}")
            return False

    def run(self):
        """گردش کار اصلی"""
        self.start_time = time.time()
        
        logger.info(Fore.BLUE + "\n" + "="*60)
        logger.info(Fore.BLUE + f"شروع فرآیند جمع‌آوری داده‌های {SYMBOL_NAME}")
        logger.info(Fore.BLUE + f"بازه زمانی: {START_DATE.date()} تا {END_DATE.date()}")
        logger.info(Fore.BLUE + "="*60)

        # مراحل اجرا
        steps = [
            ("بررسی اتصال API", self._test_api_connection),
            ("احراز هویت", self._get_access_token),
            ("تبدیل نام نماد", self._resolve_symbol),
        ]

        for step_name, step_func in steps:
            if not step_func():
                logger.error(Fore.RED + f"✗ توقف فرآیند در مرحله: {step_name}")
                return

        # دریافت داده‌های تاریخی
        for timeframe in TIMEFRAMES:
            self.data["ohlcv"][timeframe] = self._fetch_ohlcv(timeframe)
            time.sleep(2)

        # دریافت عمق بازار
        self.data["market_depth"] = self._fetch_market_depth()

        # ذخیره‌سازی نهایی
        if self._save_data():
            logger.info(Fore.GREEN + "\n" + "="*60)
            logger.info(Fore.GREEN + "✓ فرآیند با موفقیت تکمیل شد")
            logger.info(Fore.GREEN + "="*60)
        else:
            logger.error(Fore.RED + "\n" + "="*60)
            logger.error(Fore.RED + "✗ فرآیند با خطا به پایان رسید")
            logger.error(Fore.RED + "="*60)

if __name__ == "__main__":
    collector = CtraderDataCollector()
    collector.run()
