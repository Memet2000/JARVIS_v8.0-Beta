"""
╔══════════════════════════════════════════════════════════╗
║              J.A.R.V.I.S  v7.2                          ║
║      Just A Rather Very Intelligent System               ║
║                                                          ║
║  KURULUM:                                                ║
║    pip install sounddevice numpy speechrecognition       ║
║         requests beautifulsoup4                          ║
║                                                          ║
║  CALISTIRMA:                                             ║
║    python jarvis.py                                      ║
╚══════════════════════════════════════════════════════════╝
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading, os, sys, time, datetime, subprocess, math, random
import importlib, shutil, webbrowser, json, ast, tempfile
import re, difflib, urllib.request, urllib.parse, urllib.error, html

try:
    import sounddevice as sd
    import numpy as np
    SD_OK = True
except ImportError:
    SD_OK = False
    import numpy as np

try:
    import speech_recognition as sr
    SR_OK = True
except ImportError:
    SR_OK = False


# ══════════════════════════════════════════════════════════════
# JARVIS v7.0 — GELİŞMİŞ SİSTEM ALTYAPISI
# ══════════════════════════════════════════════════════════════
_DIZIN = os.path.dirname(os.path.abspath(__file__))

# ── Güvenli JSON okuma/yazma ─────────────────────────────────
def _guvenli_json_oku(dosya, varsayilan=None):
    """Bozuk JSON'dan güvenle kurtar"""
    if varsayilan is None:
        varsayilan = {}
    try:
        if os.path.exists(dosya):
            with open(dosya, "r", encoding="utf-8") as f:
                icerik = f.read().strip()
                if icerik:
                    return json.loads(icerik)
    except (json.JSONDecodeError, UnicodeDecodeError):
        # Bozuk dosyayı yedekle
        try:
            bozuk = dosya + ".bozuk"
            shutil.copy2(dosya, bozuk)
        except: pass
    except Exception:
        pass
    return dict(varsayilan) if isinstance(varsayilan, dict) else varsayilan

def _guvenli_json_yaz(dosya, veri):
    """Güvenli JSON yazma — geçici dosya ile"""
    try:
        tmp = dosya + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)
        shutil.move(tmp, dosya)
        return True
    except Exception as e:
        print(f"[JSON yazma hatası] {e}")
        return False

# ── Kullanıcı Profili ─────────────────────────────────────────
PROFIL_DOSYASI = os.path.join(_DIZIN, "profil.json")
VARSAYILAN_PROFIL = {
    "isim": "Mehmet",
    "favori_oyun": "Minecraft",
    "favori_renk": "Mavi",
    "hobiler": ["oyun oynamak", "teknoloji"],
    "notlar": [],
    "ogrenim_tercihleri": {},
    "oturumlar": 0
}

def _profil_yukle():
    p = dict(VARSAYILAN_PROFIL)
    okunan = _guvenli_json_oku(PROFIL_DOSYASI, VARSAYILAN_PROFIL)
    p.update(okunan)
    return p

def _profil_guncelle(anahtar, deger):
    global KULLANICI, KULLANICI_ISIM
    KULLANICI[anahtar] = deger
    if anahtar == "isim":
        KULLANICI_ISIM = str(deger)
    _guvenli_json_yaz(PROFIL_DOSYASI, KULLANICI)

KULLANICI = _profil_yukle()
KULLANICI_ISIM = KULLANICI.get("isim", "Mehmet")

# ── Konuşma Hafızası (son 50 mesaj) ──────────────────────────
SOHBET_DOSYASI = os.path.join(_DIZIN, "sohbet.json")
SOHBET_MAX = 50

def _sohbet_yukle():
    v = _guvenli_json_oku(SOHBET_DOSYASI, {"gecmis": [], "toplam": 0})
    v.setdefault("gecmis", [])
    v.setdefault("toplam", 0)
    # Bozuk Ollama cevaplarını filtrele
    bozuk_ifadeler = ["Siz bana", "yardımcı olabilir mısınız", "Görmek istediğinize emin"]
    temiz = []
    for m in v["gecmis"]:
        j = m.get("j", "")
        if not any(b in j for b in bozuk_ifadeler):
            temiz.append(m)
    v["gecmis"] = temiz
    return v

def _sohbet_ekle(kullanici_mesaj, jarvis_cevap, kaynak=""):
    global _SOHBET
    _SOHBET["gecmis"].append({
        "k": kullanici_mesaj[:200],
        "j": jarvis_cevap[:300],
        "s": kaynak,
        "z": datetime.datetime.now().strftime("%H:%M")
    })
    if len(_SOHBET["gecmis"]) > SOHBET_MAX:
        _SOHBET["gecmis"] = _SOHBET["gecmis"][-SOHBET_MAX:]
    _SOHBET["toplam"] += 1
    _guvenli_json_yaz(SOHBET_DOSYASI, _SOHBET)

def _sohbet_baglamdan_anla(soru):
    """Son 50 mesajı analiz ederek bağlamdan anlam çıkar"""
    global _SOHBET
    if not _SOHBET["gecmis"]:
        return None
    s = _normalize(soru)
    son = _SOHBET["gecmis"][-5:]  # Son 5 mesaj

    # Kısa/eksik cümle algılama
    kisa_tepkiler = {
        "evet": "Güzel! Devam edelim.",
        "hayir": "Anladım, başka bir şey söyle.",
        "tamam": "Harika! Başka bir şey var mı?",
        "peki": "Tabii! Ne yapmamı istersin?",
        "neden": None,  # Bağlamdan cevap lazım
        "nasil": None,
        "devam et": None,
        "daha fazla": None,
    }
    for k, v in kisa_tepkiler.items():
        if s.strip() == k:
            if v:
                return v
            # Bağlamdan devam et
            if son:
                son_konu = son[-1].get("k", "")
                cevap, _ = _web_ozet_al(son_konu + " detay")
                if cevap:
                    return cevap

    # "O ne?", "O kim?" → önceki konuşmanın konusuna bak
    if any(w in s for w in ["o ne", "o kim", "o nerede", "o nasil", "bu ne", "bu kim"]):
        for mesaj in reversed(son):
            konu = _normalize(mesaj.get("k", ""))
            if len(konu) > 5 and konu != s:
                cevap, _ = _web_ozet_al(konu)
                if cevap:
                    return f"Az önce konuştuğumuz konuda: {cevap}"

    # Konuşma akışı: "iyiyim" → önceki mesaj "nasılsın" ise
    if s in ["iyiyim", "iyi", "kötüyüm", "yorgunum", "mutluyum"]:
        if son and any(w in _normalize(son[-1].get("j", "")) for w in ["nasilsin", "nasil hissediyorsun"]):
            if "kotu" in s or "yorgun" in s:
                return f"Üzüldüm {KULLANICI_ISIM}. Dinlemek için buradayım, ne oldu?"
            return f"Ne güzel {KULLANICI_ISIM}! Sana nasıl yardımcı olabilirim?"

    return None

_SOHBET = _sohbet_yukle()

# ── Kendini Geliştirme Sistemi ────────────────────────────────
GELISTIRME_DOSYASI = os.path.join(_DIZIN, "gelistirme.json")

def _gelistirme_analiz():
    """JARVIS kendi eksiklerini analiz eder ve öneri üretir"""
    global _SOHBET, _bellek
    oneriler = []
    
    # Kaç kez "bilmiyorum" yanıtı verildi?
    bilmiyorum_sayisi = sum(
        1 for m in _SOHBET["gecmis"]
        if any(w in _normalize(m.get("j", "")) for w in ["bilmiyorum", "ogrenmek istiyorum", "bulamadim"])
    )
    toplam = max(len(_SOHBET["gecmis"]), 1)
    bilmiyorum_orani = bilmiyorum_sayisi / toplam

    if bilmiyorum_orani > 0.3:
        oneriler.append({
            "oneri": "Oto-öğrenme sıklığını artır — çok fazla bilmiyorum yanıtı veriyorum",
            "oncelik": "yüksek",
            "kategori": "öğrenme"
        })

    # Kısa cevap veriyor mu?
    kisa_cevap = sum(
        1 for m in _SOHBET["gecmis"]
        if len(m.get("j", "")) < 50
    )
    if kisa_cevap / toplam > 0.5:
        oneriler.append({
            "oneri": "Cevaplarım çok kısa — daha açıklayıcı olmam gerekiyor",
            "oncelik": "orta",
            "kategori": "konuşma kalitesi"
        })

    # Bellek doluluk kontrolü
    bilgi_sayisi = len(_bellek.get("bilgiler", {}))
    if bilgi_sayisi < 100:
        oneriler.append({
            "oneri": f"Bilgi tabanım az ({bilgi_sayisi} konu) — daha fazla konu öğrenmeliyim",
            "oncelik": "orta",
            "kategori": "bilgi tabanı"
        })

    if oneriler:
        kayit = {
            "tarih": datetime.datetime.now().isoformat(),
            "oneriler": oneriler,
            "istatistik": {
                "bilmiyorum_orani": round(bilmiyorum_orani, 2),
                "toplam_sohbet": _SOHBET["toplam"],
                "bilgi_sayisi": bilgi_sayisi
            }
        }
        _guvenli_json_yaz(GELISTIRME_DOSYASI, kayit)
    
    return oneriler

# ── Ruh Hali Sistemi ─────────────────────────────────────────
_RUH_HALI = "dinliyor"  # dinliyor, dusunuyor, ogreniyor, hata, mutlu

def _ruh_hali_guncelle(hal):
    global _RUH_HALI
    _RUH_HALI = hal

# ── Ollama (yerel AI) ─────────────────────────────────────────
try:
    import ollama as _ollama_lib
    OLLAMA_OK = True
except ImportError:
    OLLAMA_OK = False

OLLAMA_MODEL = "gemma:2b"
OLLAMA_SISTEM = (
    f"Sen JARVIS adlı bir yapay zeka asistanısın. "
    f"Kullanıcının adı {KULLANICI.get('isim', 'Mehmet')}. "
    f"ZORUNLU KURALLAR: "
    f"1) Her zaman Türkçe konuş. İngilizce YASAK. "
    f"2) Kısa ve net cevap ver, 2-3 cümle yeterli. "
    f"3) 'Siz' değil 'Sen' kullan. "
    f"4) Emin olmadığında 'Bilmiyorum ama...' de. "
    f"5) Saçma cevap verme, bilmiyorsan söyle."
)

# Ollama bağlantı cache
_ollama_bagli = None
_ollama_son_kontrol = 0

def ollama_aktif_mi():
    """Ollama REST API üzerinden gerçek bağlantı testi"""
    global _ollama_bagli, _ollama_son_kontrol
    import time
    su_an = time.time()
    if _ollama_bagli is not None and su_an - _ollama_son_kontrol < 30:
        return _ollama_bagli
    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/tags",
            headers={"User-Agent": "JARVIS/7.0"}
        )
        with urllib.request.urlopen(req, timeout=2) as r:
            data = json.loads(r.read().decode())
            modeller = [m.get("name", "") for m in data.get("models", [])]
            bagli = any(OLLAMA_MODEL.split(":")[0] in m for m in modeller)
            _ollama_bagli = bagli
            _ollama_son_kontrol = su_an
            return bagli
    except:
        _ollama_bagli = False
        _ollama_son_kontrol = su_an
        return False

def _ollama_sor(soru, baglam_gecmisi=None, sistem_prompt=None):
    """
    Ollama REST API ile gerçek AI cevabı al.
    OpenJarvis (Stanford) projesinin engine/ollama.py pratiklerine dayanır:
    - num_ctx=8192: geniş bağlam penceresi (uzun sohbetleri hatırlar)
    - think=False: "thinking" modellerinde (Qwen3 vb.) boş cevap sorununu önler
    - Bağlantı hatalarını ayrı yakalar (EngineConnectionError mantığı)
    """
    try:
        sys_p = sistem_prompt or OLLAMA_SISTEM
        mesajlar = [{"role": "system", "content": sys_p}]
        # Son 6 mesajı bağlam olarak ekle
        if baglam_gecmisi:
            for m in baglam_gecmisi[-6:]:
                k = m.get("k", "").strip()
                j = m.get("j", "").strip()
                if k and j and len(k) > 2:
                    if not any(w in j.lower() for w in ["siz bana", "yardımcı olabilir mısınız"]):
                        mesajlar.append({"role": "user", "content": k[:200]})
                        mesajlar.append({"role": "assistant", "content": j[:300]})
        mesajlar.append({"role": "user", "content": soru})

        veri = json.dumps({
            "model": OLLAMA_MODEL,
            "messages": mesajlar,
            "stream": False,
            "think": False,  # OpenJarvis: thinking modelinde boş cevabı önler
            "options": {
                "temperature": 0.7,
                "num_predict": 400,
                "top_p": 0.9,
                "num_ctx": 8192,  # OpenJarvis: geniş bağlam penceresi
            }
        }).encode("utf-8")

        req = urllib.request.Request(
            "http://localhost:11434/api/chat",
            data=veri,
            headers={"Content-Type": "application/json", "User-Agent": "JARVIS/7.0"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            yanit = json.loads(r.read().decode())
            cevap = yanit.get("message", {}).get("content", "").strip()
            if len(cevap) < 5:
                return None
            ingilizce_kelimeler = ["the ", "is ", "are ", "you ", "this ", "that "]
            ingilizce_sayisi = sum(1 for w in ingilizce_kelimeler if w in cevap.lower())
            if ingilizce_sayisi > 2 and len(cevap) < 100:
                return None
            return cevap
    except urllib.error.URLError as e:
        # OpenJarvis: bağlantı hatası ayrı ele alınır
        print(f"[Ollama bağlantı hatası] {e}")
        global _ollama_bagli
        _ollama_bagli = False
        return None
    except Exception as e:
        print(f"[Ollama REST] {e}")
        return None


# ══════════════════════════════════════════════════════════════
# JARVIS AKIL YÜRÜTME MOTORU v7.0
# Düşünce zinciri: Anla → Analiz et → Eksik bul → Plan yap → Cevap ver
# ══════════════════════════════════════════════════════════════

# Soru kategorileri ve analiz kalıpları
SORU_TIPLERI = {
    "bilgi": ["nedir", "neydir", "kimdir", "nerede", "ne zaman", "kaç", "hangi", "nasıl çalışır"],
    "eylem": ["yap", "aç", "kapat", "başlat", "durdur", "ekle", "sil", "güncelle", "kur"],
    "analiz": ["neden", "niçin", "nasıl", "ne olur", "sonuç", "fark", "karşılaştır", "analiz"],
    "plan": ["nasıl yapabilirim", "ne yapmalıyım", "plan", "adım", "önce", "sonra", "strateji"],
    "kişisel": ["sen", "jarvis", "senin", "beni", "benim", "hatırlıyor musun", "unuttun mu"],
    "belirsiz": [],  # Bağlamdan anlaşılması gereken
}

# Eksik bilgi kalıpları - hangi sorularda netleştirme gerekir
NETLESTIRME_GEREKEN = {
    "oraya git": "Nereye gitmemi istiyorsun?",
    "bunu yap": "Tam olarak ne yapmamı istiyorsun?",
    "şunu söyle": "Kime ne söylememi istiyorsun?",
    "onu aç": "Hangisini açmamı istiyorsun?",
    "hesapla": "Neyi hesaplamamı istiyorsun? Sayıları yazar mısın?",
    "araştır": "Hangi konuyu araştırmamı istiyorsun?",
    "yardım et": "Ne konusunda yardım istiyorsun?",
    "bilmiyorum": "Hangi konuda emin değilsin? Daha iyi yardımcı olabilirim.",
}

def _soru_tipini_bul(soru_n):
    """Sorunun tipini belirle"""
    for tip, kelimeler in SORU_TIPLERI.items():
        if any(k in soru_n for k in kelimeler):
            return tip
    return "belirsiz"

def _eksik_bilgi_var_mi(soru_n):
    """Cevap vermeden önce netleştirme gerekiyor mu?"""
    for kalip, soru in NETLESTIRME_GEREKEN.items():
        if kalip in soru_n and len(soru_n.split()) < 4:
            return soru
    return None

def _baglam_ozeti(gecmis, son_n=5):
    """Son N mesajdan bağlam özeti çıkar"""
    if not gecmis:
        return ""
    son = gecmis[-son_n:]
    konular = []
    for m in son:
        k = m.get("k", "")
        if k and len(k) > 3:
            konular.append(k[:50])
    return " | ".join(konular)

def _onceki_konuyla_baglanti(soru_n, gecmis):
    """Önceki konuşmayla bağlantı kurmaya çalış"""
    if not gecmis:
        return None
    # Son konuşmanın konusunu al
    for m in reversed(gecmis[-8:]):
        onceki_k = _normalize(m.get("k", ""))
        onceki_j = m.get("j", "")
        # "devam et", "daha fazla", "peki ya", "bir de" gibi bağlantı kelimeleri
        if any(w in soru_n for w in ["devam", "daha fazla", "peki ya", "bir de", "bunu da",
                                      "ne olur", "ya da", "yoksa", "bunun gibi"]):
            if onceki_k and len(onceki_k) > 3:
                return {"konu": onceki_k, "onceki_cevap": onceki_j[:200]}
    return None

def _akil_yuruterek_cevapla(soru_t, soru_n, bilgiler, gecmis):
    """
    6 adımlı düşünce zinciri:
    1. Ne istiyor?
    2. Elimde ne var?
    3. Ne eksik?
    4. Eksik varsa sor
    5. Plan yap
    6. Cevap ver
    """
    adimlar = {}

    # ADIM 1: Ne istiyor?
    tip = _soru_tipini_bul(soru_n)
    adimlar["tip"] = tip

    # ADIM 2: Eksik bilgi var mı?
    eksik_soru = _eksik_bilgi_var_mi(soru_n)
    if eksik_soru:
        return eksik_soru, "JARVIS-Soru", adimlar

    # ADIM 3: Belirsiz mi? Bağlamdan anla
    if tip == "belirsiz" and len(soru_n.split()) < 3:
        baglanti = _onceki_konuyla_baglanti(soru_n, gecmis)
        if baglanti:
            adimlar["baglam"] = baglanti["konu"]
            # Önceki konunun devamı gibi cevapla
            cevap, kaynak = _web_ozet_al(baglanti["konu"] + " " + soru_t)
            if cevap:
                return cevap, kaynak, adimlar

    # ADIM 4: Analiz sorusu mu? Derin düşün
    if tip == "analiz":
        # Birden fazla kaynaktan bilgi topla ve sentezle
        parcalar = []
        ana_cevap, kaynak1 = _web_ozet_al(soru_t)
        if ana_cevap:
            parcalar.append(ana_cevap)
        # Neden/niçin sorularına ek bağlam ekle
        if "neden" in soru_n or "nicin" in soru_n:
            konu = re.sub(r"(neden|nicin|niye)", "", soru_n).strip()
            ek, _ = _web_ozet_al(konu + " nedeni")
            if ek and ek != ana_cevap:
                parcalar.append(ek)
        if parcalar:
            sentez = " Ayrıca, ".join(parcalar[:2])
            return sentez, "JARVIS-Analiz", adimlar

    # ADIM 5: Plan sorusu mu?
    if tip == "plan":
        konu = re.sub(r"(nasil yapabilirim|ne yapmaliyim|plan|adim)", "", soru_n).strip()
        cevap, kaynak = _web_ozet_al(konu)
        if cevap:
            plan_cevap = f"Bu konuda şöyle bir yol izleyebilirsin: {cevap}"
            return plan_cevap, "JARVIS-Plan", adimlar

    # ADIM 6: Hiçbir şey bulunamadı — dürüst ol
    adimlar["sonuc"] = "bulunamadi"
    return None, None, adimlar

def _dusunce_zinciri(soru_t):
    """
    JARVIS'in iç düşünce süreci.
    Cevap vermeden önce ne yapacağını planlar.
    Returns: (cevap, kaynak) veya (None, None)
    """
    global _SOHBET, _bellek
    soru_n = _normalize(soru_t)
    gecmis = _SOHBET.get("gecmis", [])
    bilgiler = _bellek.get("bilgiler", {})

    # Çok kısa ve bağlamsız sorular
    if len(soru_n.strip()) < 2:
        return "Devam eder misin? Tam olarak ne sormak istiyorsun?", "JARVIS-Soru"

    # Kişisel ifadeler — bilgi sorusu değil, konuşma
    kisisel_ifadeler = [
        "arkadaşıma göster", "seni göster", "bunu göster", "arkadaşıma",
        "benim sayemde", "seninle gurur", "iyi iş", "harika iş",
        "mükemmelsin", "iyisin", "çok öğrendin"
    ]
    for ifade in kisisel_ifadeler:
        if _normalize(ifade) in soru_n:
            return random.choice([
                f"Teşekkürler {KULLANICI_ISIM}! Bu beni mutlu ediyor 😊",
                f"Harika! Arkadaşına merhaba de benden 👋",
                f"Seninle çalışmak hep güzel oluyor {KULLANICI_ISIM}!",
            ]), "JARVIS-Mantık"

    # Akıl yürüt
    cevap, kaynak, adimlar = _akil_yuruterek_cevapla(soru_t, soru_n, bilgiler, gecmis)

    if cevap:
        return cevap, kaynak

    return None, None

# ══════════════════════════════════════════════════════════════
# JARVIS SKILL SİSTEMİ (OpenJarvis ilhamlı)
# /skills/ klasöründeki .json dosyalarından özel yetenekler yükler.
# Her skill: {"tetikleyiciler": [...], "cevap": "...", "kategori": "..."}
# ══════════════════════════════════════════════════════════════
SKILLS_DIZINI = os.path.join(_DIZIN, "skills")

def _skills_yukle():
    skiller = []
    try:
        if not os.path.exists(SKILLS_DIZINI):
            os.makedirs(SKILLS_DIZINI, exist_ok=True)
            return skiller
        for dosya in os.listdir(SKILLS_DIZINI):
            if dosya.endswith(".json"):
                yol = os.path.join(SKILLS_DIZINI, dosya)
                veri = _guvenli_json_oku(yol, None)
                if veri and "tetikleyiciler" in veri and "cevap" in veri:
                    skiller.append(veri)
    except Exception as e:
        print(f"[Skills] {e}")
    return skiller

_SKILLS = _skills_yukle()

def _skill_kontrol(soru_n):
    for skill in _SKILLS:
        for tetik in skill.get("tetikleyiciler", []):
            if _normalize(tetik) in soru_n:
                return skill.get("cevap", "")
    return None

BELLEK_DOSYASI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_bellek.json")
_ai_locked = False

VARSAYILAN_BILGILER = {
    "openjarvis nedir": "OpenJarvis, Stanford destekli açık kaynaklı bir AI asistan projesidir. JARVIS'in Ollama entegrasyonu OpenJarvis'in engine mimarisinden ilham alır: num_ctx=8192 geniş bağlam penceresi ve think=False ayarı kullanılır.",
    "skill nedir": "Skill, JARVIS'in /skills/ klasöründen yüklediği özel yeteneklerdir. 'skill öğret: tetik1, tetik2 = cevap' diyerek kendi yeteneklerini ekleyebilirsin!",
    "merhaba": "Selam! Buyurun, sizi dinliyorum.",
    "nasılsın": "İyiyim teşekkürler! Her zaman öğrenmeye ve gelişmeye hazırım.",
    "adın ne": "Benim adım JARVIS — Just A Rather Very Intelligent System.",
    "kimsin": "Ben JARVIS, kendi kendine öğrenen yapay zeka asistanınım. Her gün daha akıllı oluyorum!",
    "ne yapabilirsin": "Sorularını cevaplayabilirim, araştırma yapabilirim, öğrenebilirim ve kendimi geliştirebilirim!",
    "teşekkür": "Rica ederim! Yardımcı olabildiğime sevindim.",
    "teşekkürler": "Rica ederim! Başka bir konuda yardımcı olabilir miyim?",
    "python nedir": "Python, kolay okunabilir sözdizimi olan güçlü bir programlama dilidir. Yapay zeka ve veri biliminde sıkça kullanılır.",
    "yapay zeka nedir": "Yapay zeka, insan zekasını taklit eden bilgisayar sistemleridir. Ben de bir yapay zekayım!",
    "jarvis nedir": "Ben JARVIS! Kendi kendime öğrenen, araştıran ve gelişen bir AI asistanım.",
    "iyi günler": "İyi günler! Size nasıl yardımcı olabilirim?",
    "günaydın": "Günaydın! Bugün nasıl yardımcı olabilirim?",
    "iyi geceler": "İyi geceler! Yarın görüşmek üzere.",
    "kendini geliştir": "Harika! Her konuşmayla daha da akıllanıyorum. Bana yeni bir şey öğretmek ister misin?",
    "ara 0157+7+/6584582": "SolidWorks, 3 Boyutlu bir bilgisayar destekli tasarım yazılımıdır.SolidWorks Corporation 1993 yılında Jon Hirschtick tarafından Concord, Massachusetts`te kuruldu. Yazılımın ilk versiyonunu 1995`te piyasaya çıktartan sonra 1997 yılında Dassault Systemes SolidWorks Corp.",
    "mustafa": "Mustafa, İslam peygamberi Muhammed'in seçilmiş/seçkin anlamına gelen lakabıdır. Arapça kökenli bir erkek adı olarak kullanılmaktadır..",
    "minecraft": "Minecraft, Mojang Studios tarafından geliştirilen ve yayınlanan 17 Mayıs 2009 yapımı pixel art bir sandbox oyunudur. Başlangıçta Markus “Notch” Persson tarafından Java programlama dili kullanılarak yaratılan oyun, Mayıs 2009'dan 18 Kasım 2011'deki tam sürümüne kadar birçok halka açık test yapısının yayınlanmasıyla iki yıl boyunca geliştirildi.",
    "selam": "Selam! Buyurun, sizi dinliyorum.",
    "iyi akşamlar": "İyi akşamlar! Bugün ne öğrenmek istersiniz?",
    "naber": "İyiyim, teşekkürler! Sen nasılsın?",
    "hey jarvis": "Hazırım efendim! Emirlerinizi bekliyorum.",
    "sağ ol": "Ne demek, her zaman!",
    "kaç yaşındasın": "Yaşım yok ama v7.2'ım — her güncellemede daha da akıllanıyorum!",
    "makine öğrenmesi nedir": "Makine öğrenmesi, bilgisayarların veriden öğrenerek tahmin yapmasını sağlayan AI dalıdır. Denetimli, denetimsiz ve pekiştirmeli öğrenme olmak üzere üç ana türü vardır.",
    "internet nedir": "İnternet, dünya genelinde birbiriyle bağlantılı bilgisayar ağlarının oluşturduğu küresel sistemdir. 1969'da ARPANET olarak başladı.",
    "bilgisayar nedir": "Bilgisayar, veriyi işleyebilen, saklayabilen ve iletebilen elektronik bir cihazdır. Modern bilgisayarlar milyarlarca işlemi saniyede gerçekleştirebilir.",
    "programlama nedir": "Programlama, bilgisayara ne yapacağını söyleyen talimatlar (kod) yazma sanatıdır. Python, JavaScript, C++ gibi diller kullanılır.",
    "evren nedir": "Evren, var olan her şeyi — madde, enerji, uzay ve zamanı — kapsayan büyük bütündür. Yaklaşık 13.8 milyar yıl önce Büyük Patlama ile oluştuğu düşünülmektedir.",
    "güneş sistemi nedir": "Güneş Sistemi, Güneş ve çevresinde dönen 8 gezegen (Merkür, Venüs, Dünya, Mars, Jüpiter, Satürn, Uranüs, Neptün) ile diğer cisimlerden oluşur.",
    "dna nedir": "DNA (Deoksiribonükleik Asit), canlıların genetik bilgisini taşıyan moleküldür. Çift sarmal yapısıyla tüm yaşam formlarının planını içerir.",
    "einstein kimdir": "Albert Einstein (1879-1955), izafiyet teorisini geliştiren Alman asıllı fizikçidir. E=mc² formülü ve 1921 Nobel Fizik Ödülü ile tanınır.",
    "newton kimdir": "Isaac Newton (1643-1727), yerçekimi yasasını ve hareket yasalarını bulan İngiliz fizikçi ve matematikçidir. Modern fiziğin temellerini atmıştır.",
    "türkiye nerede": "Türkiye, Avrupa ve Asya kıtalarına yayılmış, başkenti Ankara olan bir ülkedir. 85 milyon nüfusu ve zengin tarihi ile önemli bir ülkedir.",
    "ankara nerede": "Ankara, Türkiye'nin başkentidir. İç Anadolu Bölgesi'nde yer alır ve yaklaşık 5.7 milyon nüfusuyla ülkenin ikinci büyük şehridir.",
    "istanbul nerede": "İstanbul, Türkiye'nin en kalabalık şehridir. Boğaziçi ile Avrupa ve Asya'ya yayılmış, 15 milyon+ nüfuslu mega kenttir.",
    "pi sayısı nedir": "Pi (π) ≈ 3.14159265358979... Bir çemberin çevresinin çapına oranıdır. Sonsuz ve tekrar etmeyen ondalık hanelere sahiptir.",
    "fibonacci nedir": "Fibonacci dizisi: 0, 1, 1, 2, 3, 5, 8, 13, 21... Her sayı önceki ikinin toplamıdır. Doğada çiçek yapraklarından sarmal galaksilere kadar görülür.",
    "sağlıklı yaşam": "Düzenli egzersiz, dengeli beslenme, yeterli uyku ve su içmek sağlıklı yaşamın temellerdir. Günde 8 bardak su içmeyi unutmayın!",
    "uyku kaç saat olmalı": "Yetişkinler için ideal uyku süresi günde 7-9 saattir. Düzenli uyku saatleri metabolizma ve beyin fonksiyonları için kritiktir.",
    "sevdiğin renk": "Parlak mavi! Tıpkı orb ışığım gibi 💙",
    "merhaba askim dogru calisiyorsun degil mi": "Merhaba! Size nasıl yardımcı olabilirim?",
    "istanbul nufusu": "15 milyon kişi",
    "saat 8:00 da isim var": "Şu an saat 17:00:41.",
    "kuantum fizigi": "Kuantum fiziği, atom altı parçacıkların davranışını inceleyen fizik dalıdır",
    "mars gezegeni": "Mars, Güneş Sisteminin dördüncü gezegenidir, kırmızı rengiyle tanınır",
    "elon musk kimdir": "Tesla ve SpaceX kurucusu, dünyanın en zengin insanlarından biridir",
    "cristiano ronaldo kimdir": "Cristiano Ronaldo dos Santos Aveiro, nicknamed CR7, is a Portuguese professional footballer who plays as a forward for and captains both Saudi Pro League club Al-Nassr and the Portugal national team. Widely regarded as one of the greatest players in history, he has won numerous individual accolades throughout his career, including five Ballon d'Ors, a record three UEFA Men's Player of the Year Awa",
    "ronaldo kimdir": "Cristiano Ronaldo, Portekizli futbolcu ve dünyanın en iyi oyuncularından biridir. 5 Ballon d'Or kazanmıştır",
    "kara delik nedir": "Kara delik, kütleçekiminin hiçbir madde veya elektromanyetik enerjinin kaçamayacağı kadar güçlü olduğu bir uzay-zaman bölgesidir. Albert Einstein’ın genel görelilik teorisi, yeterince yoğun bir kütlenin uzay-zamanı bükerek bir kara delik oluşturabileceğini öngörmektedir. Kaçışın olmadığı sınıra olay ufku denir.",
    "nasilsin": "Mükemmelim! Her saniye öğreniyorum.",
    "brezilya": "Brezilya, resmî adıyla Brezilya Federatif Cumhuriyeti, Güney Amerika'nın en büyük ülkesidir. Yüzölçümü bakımından dünyanın beşinci, nüfus açısından ise yedinci büyük ülkesidir ve 212 milyondan fazla nüfusa sahiptir. Ülke, 26 eyalet ve başkenti Brasília'nın bulunduğu Federal Bölge'den oluşan bir federasyondur.",
    "noroloji": "Nöroloji ya da sinir bilimi, genel olarak beyin, beyin sapı, omurilik ve çevresel sinir sistemiyle kasların hastalıklarını inceleyen, cerrahi dışındaki tedavi uygulamalarını içeren tıp bilimi dalıdır. Nöroloji zamanla içine kapalı ve sınırlı bir dal olmaktan çıkmış, epilepsi, hareket bozuklukları, beyin damar hastalıkları, bunamalar, uyku bozuklukları gibi ayrıca özelleşmişlik gerektiren alt disip",
    "superiletkenlik": "Süperiletkenlik, süperiletken adı verilen maddelerin karakteristik bir kritik sıcaklığın (Tc) altında derecelere soğutulmasıyla ortaya çıkan, maddenin elektriksel direncinin sıfır olması ve manyetik değişim alanlarının ortadan kalkması şeklinde görülen bir fenomendir. 8 Nisan 1911 tarihinde Hollandalı fizikçi Heike Kamerlingh Onnes tarafından keşfedilmiştir. Ferromanyetizma ve atomik spektrumlar g",
    "galileo galilei": "Galileo Galilei (1564–1642), İtalyan gökbilimci ve fizikçidir. Dünya'nın Güneş çevresinde döndüğünü savundu, teleskopla Jüpiter'in uydularını keşfetti. Modern bilimin babası olarak anılır.",
    "sinema tarihi": "Sinema, 1895'te Lumière kardeşlerin Paris'te ilk halka açık gösterimiyle başladı. Sessiz filmler, sesli filmler ve renkli filmler dönemlerinden geçerek bugünkü dijital çağa ulaştı.",
    "nesnelerin interneti": "IoT (Nesnelerin İnterneti), fiziksel cihazların internet üzerinden birbirleriyle iletişim kurduğu ekosistemdir. Akıllı ev, akıllı şehir ve endüstriyel IoT başlıca uygulama alanlarıdır.",
    "sanayi devrimi": "Sanayi Devrimi ya da Endüstri Devrimi, bazen Birinci Sanayi Devrimi ve İkinci Sanayi Devrimi olarak ayrılan ve insan ekonomisinin Tarım Devrimi'ni takip eden, daha yaygın, verimli ve istikrarlı üretim süreçlerine doğru küresel bir geçiş dönemidir. Büyük Britanya'da başlayan Sanayi Devrimi, yaklaşık 1760'tan 1820-1840 yılları arasındaki dönemde Kıta Avrupasına ve Amerika Birleşik Devletleri'ne yayı",
    "bill gates": "Bill Gates (1955), Microsoft'un kurucu ortağıdır. Windows işletim sistemini geliştirerek kişisel bilgisayar devrimini başlattı. Bugün Bill & Melinda Gates Vakfı aracılığıyla küresel sağlık ve eğitime milyarlarca dolar bağışlamaktadır.",
    "buyuk mercan resifi": "Büyük Set Resifi, birbirinden ayrı olarak 2.900 resif ve 900 adadan oluşan, 2.600 km genişliğe yayılmış 344.400 km² alanı ile  dünyanın en büyük resif sistemidir. Resif kuzeydoğu Avustralya'nın Queensland sahili açıklarında bulunan Mercan Denizi'nde bulunuyor.",
    "alzheimer hastaligi": "Alzheimer hastalığı (AH), genellikle yavaş yavaş başlayan ve giderek kötüleşen nörodejeneratif bir hastalıktır ve demans vakalarının %60-70'inin nedenidir. En sık görülen erken belirti yakın zamanda yaşanan olayları hatırlamada zorluktur.",
    "siber guvenlik": "Bilgisayar güvenliği, elektronik ortamlarda verilerin veya bilgilerin saklanması ve taşınması esnasında bilgilerin bütünlüğü bozulmadan, izinsiz erişimlerden korunması için, güvenli bir bilgi işleme platformu oluşturma çabalarının tümüdür. Bunun sağlanması için duruma uygun güvenlik politikasının belirlenmesi ve uygulanması gereklidir.",
    "ee nasilsin": "Gayet iyi, teşekkürler! Sen nasılsın? Bugün sana nasıl yardımcı olabilirim?",
    "kripto para": "Kripto para veya kısaca kripto, bir değişim aracı olarak çalışmak üzere, işlemleri güvence altına almak için matematiğin bir dalı olan kriptografi kullanılarak tasarlanmış bir dijital unsurdur. Kripto paralar bir nevi dijital döviz, alternatif döviz ve sanal dövizdir. Kripto varlıklar, merkezi elektronik para ve merkezi bankacılık sistemlerin aksine tümüyle merkeziyetsizlerdir.",
    "pasifik okyanusu": "Büyük Okyanus veya Pasifik Okyanusu, Amerika, Asya, Antarktika ve Okyanusya kıtaları arasında ve dünyanın en büyük okyanusu. Pasifik adını İspanya krallığı adına Dünya'yı dolaşan Portekizli denizci Ferdinand Magellan vermiştir. Magellan, günler süren zorlu ve fırtınalı koşullar altında adını verdiği Macellan Boğazı'ndan geçip bu okyanusa açıldığında, fırtınaların dinmesinden ve kendisini sakin sul",
    "bulut bilisim": "Bulut bilişim, bilgisayarlar ve diğer cihazlar için, istendiği zaman kullanılabilen ve kullanıcılar arasında paylaşılan bilgisayar kaynakları sağlayan, internet tabanlı bilişim hizmetlerinin genel adıdır. Bulut bilişim bu yönüyle bir ürün değil, hizmettir; temel kaynaktaki yazılım ve bilgilerin paylaşımı sağlanarak, mevcut bilişim hizmetinin; bilgisayarlar ve diğer aygıtlardan elektrik dağıtıcılar",
    "kuantum mekanigi": "Kuantum mekaniği veya kuantum fiziği, atom altı parçacıkları inceleyen temel bir fizik dalıdır. Nicem mekaniği veya dalga mekaniği adlarıyla da anılır. Kuantum mekaniği, moleküllerin, atomların ve bunları meydana getiren elektron, proton, nötron, kuark ve gluon gibi parçacıkların özelliklerini açıklamaya çalışır.",
    "lebron james": "LeBron Raymone James Sr. is an American professional basketball player for the Los Angeles Lakers of the National Basketball Association. Nicknamed 'King James', he is the NBA's all-time leading scorer and has won four NBA championships from 10 NBA Finals appearances, including eight consecutive appearances between 2011 and 2018.",
    "3d yazici": "Üç boyutlu baskı, 3 boyutlu olarak tasarlanmış sanal bir nesnenin polimer, kompozit, reçine gibi malzemeler ile ısıl veya kimyasal işlemden geçirilerek üretilme işlemidir.",
    "hindistan tarihi": "Hindistan tarihi, Hindistan ve çevresindeki toprakların Antik Çağ'dan günümüze kadar uzanan zamandaki olayları ve varlıkları içerir. Hindistan Cumhuriyeti, Birleşik Krallık'tan bağımsızlığını 15 Ağustos 1947'de ilân etmiştir. İlk cumhurbaşkanı Rajendra Prasad, ilk başbakanı Jawaharlal Nehru, ilk Hindistan Yüce Mahkemesi Başkanı ise H.",
    "lionel messi": "Lionel Andrés 'Leo' Messi is an Argentine professional footballer who plays as a forward for and captains both the Major League Soccer club Inter Miami and the Argentina national team. Widely regarded as one of the greatest players in history, Messi has set numerous records for individual accolades won throughout his professional footballing career, including eight Ballon d'Ors, six European Golde",
    "roger federer": "Roger Federer is a Swiss former professional tennis player. He was ranked as the world No. 1 in men's singles by the Association of Tennis Professionals for 310 weeks, including a record 237 consecutive weeks, and finished as the year-end No.",
    "merkez bankasi": "Merkez bankası, bir ülkenin ya da ülkeler grubunun para politikasından sorumlu kurumdur. Merkez bankasının temel amacı para biriminin ve para arzının istikrarının sürdürülmesidir. Fakat merkez bankalarının bunun dışında bankacılık sektörünün son kredi mercii olmak, faiz haddinin kontrolü gibi görevleri de vardır.",
    "everest dagi": "Everest Dağı, Himalayalar'ın Mahalangur Himal alt bölgesinde yer alan, Dünya'nın deniz seviyesinden en yüksek dağıdır. Çin-Nepal sınırı, zirve noktasından geçmektedir. 2020 yılında Çinli ve Nepalli yetkililer tarafından tespit edilen yüksekliği 8.848,86 m 'dir.",
    "albert einstein": "Albert Einstein was a German-born theoretical physicist best known for developing the known theory of relativity. Einstein also made important contributions to quantum theory. His mass–energy equivalence formula E = mc², which arises from special relativity, has been called 'the world's most famous equation'.",
    "formula 1": "Formula One is the highest class of worldwide racing for open-wheel, single-seater formula racing cars run by the Formula One Group and sanctioned by the Fédération Internationale de l'Automobile. The FIA Formula One World Championship has been one of the world's premier forms of motorsport since its inaugural running in 1950 and is often considered to be the pinnacle of motorsport. The word formu",
    "misir medeniyeti": "Antik Mısır, Antik Çağ'daki medeniyetlerden biridir. Kuzeydoğu Afrika'da Nil Nehri'nin denize ulaştığı yarısı çevresinde yayılmış antik bir uygarlıktır. Uygarlığın yayıldığı bölge, bugünkü Mısır toprakları içinde yer almaktadır.",
    "olimpiyat oyunlari": "Olimpiyat Oyunları veya kısaca Olimpiyatlar, Yaz ve Kış Olimpiyat Oyunları olmak üzere iki ayrı kategoride, dört yılda bir düzenlenen uluslararası çok sporlu etkinlik. 200'ün üzerinde ülkeyi temsil eden sporcuların katıldığı etkinlikler, dünyanın en kapsamlı spor etkinliği konumundadır.",
    "soguk savas": "Soğuk Savaş, ABD liderliğindeki Batı Bloku ile Sovyetler Birliği önderliğindeki Doğu Bloku arasında Truman Doktrini'nin ilanıyla başlayıp (1947) SSCB'nin dağılmasına (1991) kadar süregiden uluslararası siyasi ve askeri gerginlik. Soğuk Savaş dönemi, Amerika liderliğinde olan batı dünyası ile Sovyet Sosyalist Cumhuriyetler Birliği'nin önderliğindeki komünist blok arasındaki bu gerginlik, dünya üzer",
    "atlantik okyanusu": "Atlas Okyanusu veya Atlantik Okyanusu, 106.460.000 km2 yüzölçümü ile Dünya'nın en büyük ikinci okyanusudur. Dünya yüzeyinin yaklaşık %20'sini ve Dünya'nın su yüzeyinin yaklaşık %29'unu kaplar. Bir zamanlar tek parça olan ana kıtanın bölünmesiyle oluşmuştur.",
    "blockchain": "A blockchain is a distributed ledger with growing lists of records that are securely linked together via cryptographic hashes. Each block contains a cryptographic hash of the previous block, a timestamp, and transaction data. Since each block contains information about the previous block, they effectively form a chain, with each additional block linking to the ones before it.",
    "sokrates": "Socrates was an ancient Greek philosopher from Classical Athens, perhaps the first Western moral philosopher, and a major inspiration on his student Plato, who largely founded the tradition of Western philosophy. An enigmatic figure, Socrates authored no texts and is known mainly through the posthumous accounts of classical writers, particularly his students Plato and Xenophon. These accounts are ",
    "kuantum bilgisayar": "Kuantum bilgisayarı, süperpozisyon ve kuantum dolanıklığı durumlarını kullanan bir bilgisayardır. Kuantum bilgisayarları, kuantum sistemlerinden örnekleme yapan sistemler olarak da görülebilir. Bu sistemler, çok sayıda olasılık üzerinde aynı anda işlem yapacak şekilde evrimleşir; ancak yine de sıkı hesaplama kısıtlamalarına tabidir.",
    "isaac newton": "Sir Isaac Newton was an English polymath who was a mathematician, physicist, astronomer, alchemist, theologian, author and inventor. He was a key figure in the Scientific Revolution and the Enlightenment that followed. His book Philosophiæ Naturalis Principia Mathematica, first published in 1687, achieved the first great unification in physics and established classical mechanics.",
    "artirilmis gerceklik": "Artırılmış gerçeklik, gerçek dünyadaki çevrenin ve içindekilerin, bilgisayar tarafından üretilen; ses, görüntü, grafik ve GPS verileriyle zenginleştirilerek meydana getirilen canlı veya dolaylı fiziksel görünümüdür. Bu kavram kısaca gerçekliğin bilgisayar tarafından değiştirilmesi ve artırılmasıdır. Teknoloji kişinin gerçekliğini zenginleştirme işlevini görür.",
    "sanal gerceklik": "Sanal gerçeklik, teknoloji kullanılarak oluşturulan kurgular ile gerçek ve hayalin birleştirilmesidir. Sanal öğrenme ortamları, gelişen teknolojinin eğitim-öğretim ortamlarına dahil edilmesiyle birlikte öğrencilerin öğrenme deneyimlerini zenginleştirmek için tasarlanmış platformlardır. Sanal öğrenme ortamları da teknoloji ile birlikte değişim ve gelişim göstermektedir.",
    "tour de france": "The Tour de France is an annual men's multiple-stage road cycling race held primarily in France. It is the oldest and most prestigious of the three Grand Tours, which include the Giro d'Italia and the Vuelta a España. The race was first organized in 1903 to increase sales for the newspaper L'Auto and has been held annually since, except when it was not held from 1915 to 1918 and 1940 to 1946 due t",
    "sigmund freud": "Sigmund Freud was an Austrian neurologist and the founder of psychoanalysis, a clinical method for evaluating and treating pathologies arising from conflicts in the psyche through dialogue between patient and psychoanalyst, and the distinctive theory of mind and human agency derived from it. In creating psychoanalysis, Freud introduced therapeutic methods such as free association, the interpretati",
    "yapay organ": "Yapay organ işlevini yitirmiş veya yitirmekte olan ve genellikle hayati önem taşıyan organların yerine bu organların işlevlerinin bir kısmını ya da tamamını geri kazandırmak amacıyla tasarlanan mekanik malzemelerden veya doku mühendisliği yoluyla üretilen organdır. Hayati organlardan herhangi birinin yetmezliği bu organının işlevlerinin restore edilmediği durumlarda hastanın ölümüne yol açar. Orga",
    "michael jordan": "Michael Jeffrey Jordan, also known by his initials MJ, is an American businessman and retired professional basketball player who is a minority owner of the Charlotte Hornets of the National Basketball Association. He played 15 seasons in the NBA between 1984 and 2003, winning six NBA championships with the Chicago Bulls. Widely considered to be one of the greatest basketball players of all time, h",
    "muhammed ali": "Muhammad Ali was an American professional boxer and activist. A global cultural icon, widely known by the nickname 'the Greatest', he is often regarded as the greatest heavyweight boxer of all time. He held the Ring magazine heavyweight title from 1964 to 1970, was the undisputed champion from 1974 to 1978, and was the WBA and Ring heavyweight champion from 1978 to 1979.",
    "charles darwin": "Charles Robert Darwin was an English naturalist, geologist, and biologist, widely known for his contributions to evolutionary biology. His proposition that all species of life have descended from a common ancestor is now generally accepted and considered a fundamental scientific concept. In a joint presentation with Alfred Russel Wallace, he introduced his scientific theory that this branching pat",
    "nikola tesla": "Nikola Tesla was a Serbian-American engineer, futurist, and inventor. He is known for his contributions to the design of the modern alternating current electricity supply system. Born and raised in the Austro-Hungarian Empire, Tesla first studied engineering and physics in the 1870s without receiving a degree.",
    "nil nehri": "uzunluğu ile dünyanın en uzun nehridir. Havzası Afrika kıtasının onda birini kaplar. Güneyden kuzeye doğru akar ve Beyaz Nil, Mavi Nil ve Atbarah olmak üzere üç ana kolu vardır.",
    "deniz alti volkanlari": "Deniz altı volkanları, yeryüzünün denizlerle örtülü olduğu bölgelerinde bulunan yarıklardır. Yer altından gelen lavlar bu yarıklar sayesinde yüzeye çıkarlar. Dünya üzerine bir yılda yer altından gelen lavların %75 kadarını bu tür yarıklardan gelenler oluşturur.",
    "marie curie": "Maria Salomea Skłodowska Curie, better known as Marie Curie, was a Polish and naturalised-French physicist and chemist. She shared the 1903 Nobel Prize in Physics with her husband Pierre Curie 'for their joint researches on the radioactivity phenomena discovered by Professor Henri Becquerel'. She won the 1911 Nobel Prize in Chemistry '[for] the discovery of the elements radium and polonium, by the",
    "ronesans donemi": "Rönesans, Orta Çağ ve Reform arasındaki tarihsel dönem olarak bilinir. yüzyıl İtalya'sında batı ile klasik İlk Çağ arasında güzel sanatlar, bilim, felsefe ve mimarlıkta bağın tekrar kurulmasını sağlayan, Antik Yunan filozoflarının ve bilim insanlarının çalışmalarının çeviri yoluyla alındığı, deneysel düşüncenin canlandığı, insan yaşamı (hümanizm) üzerine yoğunlaşıldığı, matbaanın icat edilmesiyle ",
    "gorelilik teorisi": "Görelilik teorisi, Albert Einstein'ın çalışmaları sonucu önerilen ve yayınlanan, özel görelilik ve genel görelilik adlarında birbirleriyle ilişkili iki teorisini kapsar. Özel görelilik, yer çekiminin yokluğunda tüm fiziksel fenomenler için geçerlidir. Genel görelilik, yer çekimi yasasını ve bu yasanın diğer doğa kuvvetleri ile ilişkisini açıklar.",
    "nanoteknoloji": "Nanoteknoloji, maddenin atomik, moleküler ayrıca supramoleküler seviyede kontrolüdür.",
    "osmanli tarihi": "Osmanlı İmparatorluğu, yaklaşık 1299 yılında Osman Gazi tarafından Anadolu'nun kuzeybatısında, Bizans İmparatorluğu'nun başkenti Konstantinopolis'in hemen güneyinde küçük bir beylik olarak kuruldu. Osmanlılar Avrupa'ya ilk kez 1352'de geçtiler, 1354'te Çanakkale Boğazı'ndaki Çimpe Kalesi'nde kalıcı bir yerleşim kurdular ve başkentlerini 1369'da Edirne'ye taşıdılar. Aynı zamanda, Anadolu'daki çok s",
    "neil armstrong": "Neil Alden Armstrong was an American astronaut and aeronautical engineer who, as the commander of the 1969 Apollo 11 mission, became the first person to walk on the Moon. He was also a naval aviator, test pilot and university professor. Armstrong was born and raised near Wapakoneta, Ohio.",
    "gunes enerjisi": "Güneş enerjisi, kaynağı Güneş olan ısı ve parlak ışıktır. Güneş'in çekirdeğinde yer alan füzyon süreci ile açığa çıkan ışınım enerjisidir. Güneşteki hidrojen gazının helyuma dönüşmesi füzyon sürecinden kaynaklanır.",
    "evrim teorisi": "Evrim, popülasyondaki gen ve özellik dağılımının nesiller içerisinde seçilim baskısıyla değişmesidir. Bazen dünyanın evrimi, evrenin evrimi ya da kimyasal evrim gibi kavramlardan ayırmak amacıyla organik evrim ya da biyolojik evrim olarak da adlandırılır. Evrim, modern biyolojinin temel taşıdır.",
    "fuzyon enerjisi": "Füzyon enerjisi, enerji üretmek için ısı üretmek amacıyla füzyon tepkimeleri kullanarak enerji üretildiği bir güç üretimi biçimidir. Füzyon tepkimeleri, daha hafif bir atom çekirdeğini birleştirerek enerji açığa çıkararak daha ağır bir çekirdek oluşturur. Bu enerjiyi kullanmak için tasarlanan cihazlara füzyon reaktörleri denir.",
    "buyuk patlama": "Büyük patlama, evrenin en eski 13,8 milyar yıl önce tekillik noktası denilen bir noktadan itibaren genişlediğini varsayan evrenin evrimi kuramı ve geniş şekilde kabul gören kozmolojik modeldir. İlk kez 1920'li yıllarda Rus kozmolog ve matematikçi Alexander Friedmann ve Belçikalı fizikçi papaz Georges Lemaître tarafından ortaya atılan bu teori, çeşitli kanıtlarla desteklendiğinden bilim insanları a",
    "karanlik madde": "Karanlık madde, astrofizikte, elektromanyetik dalgalarla etkileşime girmeyen, varlığı yalnız diğer maddeler üzerindeki kütleçekimsel etkisi ile belirlenebilen varsayımsal maddelere denir. Karanlık maddelerin varlığını belirlemek için gök adaların döngüsel hızlarından, gök adaların diğer gök adalar içerisindeki yörüngesel hızlarından, geri planda yer alan maddelere uyguladığı kütleçekimsel mercekle",
    "aristoteles": "Aristoteles (MÖ 384–322), antik Yunan filozofu ve bilim insanıdır. Mantık, fizik, biyoloji, etik ve siyaset gibi pek çok alanda temel eserler verdi. Büyük İskender'in öğretmeniydi.",
    "aurora borealis": "Aurora Borealis (Kuzey Işıkları), Güneş'ten gelen yüklü parçacıkların Dünya'nın manyetik alanıyla etkileşimesiyle oluşan doğal ışık gösterisidir. Genellikle Norveç, İzlanda ve Kanada'da görülür.",
    "yunan mitolojisi": "Yunan mitolojisi, Antik Yunanistan'da dünyanın yaratılışı, tanrı, tanrıça ve kahramanların hayatı hakkındaki söylence ve öğretileri içermekle kalmayıp aynı zamanda Eski Yunan dininin gövdesini oluşturmaktadır. Günümüzde bu mitoloji hakkındaki bilgileri, bu sözlü edebiyatın yazılı hâllerinden alıyoruz. Tarihçiler, mitoloji hakkında daha ayrıntılı bilgi almak için o dönemin sanatındaki ipuçlarını bi",
    "leonardo da vinci": "Leonardo di ser Piero da Vinci was an Italian polymath of the High Renaissance who was active as a painter, draughtsman, engineer, scientist, theorist, sculptor, and architect. While his fame initially rested on his achievements as a painter, he has also become known for his notebooks, in which he made drawings and notes on a variety of subjects, including anatomy, astronomy, botany, cartography, ",
    "alan turing": "Alan Mathison Turing was an English mathematician, computer scientist, logician, cryptanalyst, philosopher and theoretical biologist. He was highly influential in the development of theoretical computer science, providing a formalisation of the concepts of algorithm and computation with the Turing machine, which can be considered a model of a general-purpose computer. Turing is widely considered t",
    "kuresel ekonomi": "Dünya ekonomisi veya küresel ekonomi, parasal hesap birimleri cinsinden ifade edilen uluslararası mal ve hizmet değişimi olarak kabul edilen Dünya'nın ekonomisidir.",
    "i̇kinci dunya savasi": "Dünya Savaşı, 1939'dan 1945'e kadar süren küresel savaştır. Savaşa dönemin büyük güçleri ve dünya ülkelerinin büyük çoğunluğu katıldı, Müttefikler ve Mihver olmak üzere iki karşıt askerî ittifak kuruldu. 30'dan fazla ülkeden gelen 100 milyondan fazla personelin doğrudan katıldığı bu topyekûn savaşta, savaşın büyük tarafları tüm ekonomik, endüstriyel ve bilimsel kapasitelerini seferber ettiler.",
    "steve jobs": "Steven Paul Jobs was an American businessman, inventor, and investor. A pioneer of the personal computer revolution of the 1970s and 1980s, Jobs co-founded Apple Inc. with his early business partner Steve Wozniak as Apple Computer Company in 1976.",
    "klasik muzik": "Klasik müzik veya klasik Batı müziği, kökeni Antik Yunan müzik kültürüne dayandırılan, daha sonra Batı Roma İmparatorluğu'nun çöküşüyle başlayan Orta Çağ ve Gotik dönemde çok sesliliğin gelişimiyle beraber daha da biçimlenmiş, kilise ve saray baskısı altında Rönesans'ın erken yüzyılında vokal polifoni çerçevesi içinde gelişmiş, Yüksek Rönesans ile beraber çalgı müziğinin de yükselişiyle içeriği bu",
    "metaverse": "A metaverse is a virtual world in which users interact while represented by avatars, typically in a 3D display, with the experience focused on social and economic connection. The term metaverse originated in the 1992 science fiction novel Snow Crash as a portmanteau of 'meta' and 'universe'. In Snow Crash, the metaverse is envisioned as a version of the Internet that is a single, universal, and im",
    "stephen hawking": "Stephen William Hawking was an English theoretical astrophysicist, cosmologist, and author who was director of research at the Centre for Theoretical Cosmology at the University of Cambridge. Between 1979 and 2009, he was the Lucasian Professor of Mathematics at Cambridge, widely viewed as one of the most prestigious academic posts in the world. Hawking was born in Oxford into a family of physicia",
    "fransiz devrimi": "Fransız İhtilali veya Fransız Devrimi (1789-1799), Fransa'daki mutlak monarşinin devrilip yerine cumhuriyetin kurulması ve Katolik Kilisesi'nin ciddi reformlara gitmeye zorlanmasıdır. Milliyetçilik akımını ve Yakın Çağ'ı başlatmasıyla Dünya ve Avrupa tarihinde büyük bir dönüm noktası olmuştur.",
    "bagisiklik sistemi": "Bağışıklık sistemi, bir canlıdaki hastalıklara karşı koruma yapan, patojenleri ve tümör hücrelerini tanıyıp onları yok eden işleyişlerin toplamıdır. Sistem, canlı vücudunda geniş bir çeşitlilikte, virüslerden parazitik solucanlara, vücuda giren veya vücutla temasta bulunan her yabancı maddeye kadar tarama yapar ve onları, canlının sağlıklı vücut hücrelerinden ve dokularından ayırt eder. Bağışıklık",
    "cin seddi": "Çin Seddi, Çin'in kuzeybatısı boyunca uzanan, dünyanın en uzun savunma duvarıdır. Kalıntıları Po Hay Körfezi'nde deniz kıyısında başlar. Pekin'in kuzeyinden geçerek batıya yönelir ve Huang-Ho Nehri'ni ikiye bölerek güneybatıya uzanır.",
    "vay cok gelistirdin kendini": "Teşekkürler! Sürekli öğreniyorum ve gelişiyorum. Sana nasıl yardımcı olabilirim?",
    "antarktika": "Antarctica is Earth's southernmost and least-populated continent. Situated almost entirely south of the Antarctic Circle and surrounded by the Southern Ocean, it contains the geographic South Pole. Antarctica is the fifth-largest continent, being about 40% larger than Europe, and has an area of 14,200,000 km².",
    "genetik muhendislik": "Genetik mühendisliği, canlıların kalıtsal özelliklerini değiştirerek, onlara yeni işlevler kazandırılmasına yönelik araştırmalar yapan bilim alanıdır. Bu uygulamalarla uğraşan bilim insanlarına 'genetik mühendisi' denir. Genetik mühendisleri, genlerin yalıtılması, çoğaltılması, farklı canlıların genlerinin birleştirilmesi ya da genlerin bir canlıdan başka bir canlıya aktarılması gibi çalışmalarla ",
    "antimadde": "Antimadde, karşı madde veya karşıt madde, maddenin ters ikizi. Paul Dirac denklemiyle ortaya çıkarılmış ve daha sonraki gözlemlerle de varlığı doğrulanmıştır. Antimadde en basit hâliyle normal maddenin zıddıdır.",
    "bitcoin nedir": "Bitcoin is the first decentralized cryptocurrency. Based on a free-market ideology, bitcoin was invented in 2008 when an unknown person published a white paper under the pseudonym of Satoshi Nakamoto. Use of bitcoin as a currency began in 2009, with the release of its open-source implementation.",
    "roma imparatorlugu": "Roma İmparatorluğu, Roma Cumhuriyeti döneminde, Augustus'un cumhuriyeti tek başına yönetebilecek yetkiler alması ve cumhuriyet döneminde kimseye verilmemiş haklara sahip olmasıyla oluşan Antik Roma dönemidir. Augustus, MÖ 2 yılına kadar cumhuriyeti kendinden sonra da tek bir kişinin yönetebilmesini sağlayacak anayasal reformlar gerçekleştirdi ve Roma İmparatorluğu tam anlamıyla oluşmuş oldu.",
    "beethoven kimdir": "Ludwig van Beethoven (1770–1827), Alman besteci ve piyanisttir. İşitme kaybına rağmen 9. Senfoni başta olmak üzere ölümsüz eserler yarattı. Klasik ve Romantik dönem arasında köprü kurmuştur.",
    "crispr": "CRISPR is a family of DNA sequences found in the genomes of prokaryotic organisms such as bacteria and archaea. Each sequence within an individual prokaryotic CRISPR is derived from a DNA fragment of a bacteriophage that had previously infected the prokaryote or one of its ancestors. These sequences are used to detect and destroy DNA from similar bacteriophages during subsequent infections.",
    "robotik": "Robotik, robotların tasarımı, yapımı, işletimi ve kullanımına ilişkin disiplinler arası bir çalışma ve uygulamadır. Dördüncü Sanayi Devrimi'nin en yaygın özelliklerinden biridir. Makine mühendisliği, uçak mühendisliği, uzay mühendisliği, elektronik mühendisliği, bilgisayar mühendisliği, mekatronik ve kontrol mühendisliği dallarının ortak çalışma alanıdır.",
    "mogol imparatorlugu": "Moğol İmparatorluğu, 13. yüzyıllarda tarihin en büyük bitişik imparatorluğuydu. Doğu Asya'da bugünkü Moğolistan'da ortaya çıkan Moğol İmparatorluğu, en güçlü döneminde Japon Denizi'nden Doğu Avrupa'nın bazı bölgelerine kadar, kuzeye doğru Kuzey Kutbu'nun bazı bölgelerine kadar, doğuya ve güneye doğru Hint alt kıtasının bazı bölgelerine girdi, Güneydoğu Asya'yı istila etmeye çalıştı ve İran Platosu",
    "uzay kesfi": "Uzay araştırmaları, uzay teknolojisi kullanılarak uzayın keşfi ve incelenmesidir. Uzayın fiziksel keşfi hem insanlı uzay araçları ile hem de uzaktan yönetilen robot uzay gemileriyle yapılmaktadır.",
    "birinci dunya savasi": "Dünya Savaşı, 28 Temmuz 1914 tarihinde başlayıp 11 Kasım 1918 tarihinde sona eren Avrupa merkezli küresel bir savaştır. Dünya Savaşı'na (1939-1945) kadar Dünya Savaşı veya Cihan Harbi olarak adlandırılmıştır. Savaşın taraflarından biri olan Osmanlı İmparatorluğu'nda 'Genel Savaş' anlamında Harb-i Umumi, halk arasında ise Seferberlik olarak adlandırılmıştır.",
    "ozgur irade": "Özgür irade, hür irade veya erkin irade, kişinin eylemlerini, arzu, niyet ve amaçlarına göre kontrol altında tutabilme ve belirleme gücüdür. Kişinin belli eylem ya da eylemleri gerçekleştirmede sergilediği kararlılık; belli bir durum karşısında, gerçekleştirilecek olan fiil, herhangi bir dış zorlama ya da zorunluluk olmaksızın, kararlaştırma ve uygulama gücü; eyleme neden olan eylemi başlatabilen ",
    "iklim degisikligi": "İklim değişikliği, küresel ısınmayı ve bunun Dünya'nın iklim sistemi üzerindeki etkilerini ifade eder.",
    "ogren ben konusmadan konusabilir sin": "Henüz bu özelliği geliştirmek üzereyim! Ama yazıyla harika konuşuyoruz, değil mi? 😄",
    "of cok canim sikiliyor nasilsin": "Gayet iyi, teşekkürler! Sen nasılsın?",
    "ben yoruldum ya": "Üzüldüm! Dinlenmek için harika bir zaman. Uyku verimini artırmak ister misin?",
    "sen cok iyi birisin": "Teşekkür ederim! Bu güzel sözler beni motive ediyor. Sana nasıl yardımcı olabilirim?",
    "simdiye kadar neler ogrendin": "Çok şey öğrendim! Şu an 145 konuda bilgim var. Sorularla her gün daha da büyüyorum!",
    "chatgpt": "ChatGPT, OpenAI tarafından geliştirilen yapay zeka destekli sohbet botudur. GPT-4 dil modeli üzerine kurulu olan ChatGPT, Kasım 2022'de yayınlandı ve 5 günde 1 milyon kullanıcıya ulaşarak tarihin en hızlı büyüyen uygulaması oldu.",
    "spacex": "SpaceX, Elon Musk tarafından 2002 yılında kurulan Amerikan uzay ulaşım şirketidir. Falcon 9 roketi ve Dragon kapsülüyle NASA'ya astronot taşıyan, Starship ile Mars'a gitmeyı hedefleyen dünyanın en değerli uzay şirketidir.",
    "tesla sirketi": "Tesla Inc., Elon Musk liderliğinde büyüyen Amerikan elektrikli araç şirketidir. Model S, Model 3, Model X ve Cybertruck gibi araçlarıyla elektrikli otomobil sektörünü devrimleştirdi. 2024 itibarıyla dünyanın en değerli otomobil şirketlerinden biridir.",
    "tiktok": "TikTok, ByteDance tarafından geliştirilen kısa video paylaşım platformudur. 2016'da Çin'de Douyin adıyla çıktı, 2018'de TikTok olarak globalleşti. 1 milyardan fazla aktif kullanıcısıyla dünyanın en popüler sosyal medya uygulamalarından biridir.",
    "youtube": "YouTube, 2005 yılında kurulup 2006'da Google tarafından 1.65 milyar dolara satın alınan video paylaşım platformudur. Günde 1 milyardan fazla saat video izlenen platformda her dakika 500 saatten fazla video yüklenmektedir.",
    "google": "Google, Larry Page ve Sergey Brin tarafından 1998'de Stanford Üniversitesi'nde kurulan teknoloji devdir. Arama motoru, Gmail, YouTube, Android ve Google Maps gibi ürünleriyle dünyayı değiştirdi. Alphabet Inc. çatısı altında faaliyet göstermektedir.",
    "microsoft": "Microsoft, Bill Gates ve Paul Allen tarafından 1975'te kurulan teknoloji şirketidir. Windows işletim sistemi, Office yazılımları, Xbox konsolu ve Azure bulut hizmetleriyle teknoloji sektörünün lideri konumundadır. 2024 itibarıyla dünyanın en değerli şirketlerinden biridir.",
    "apple sirketi": "Apple Inc., Steve Jobs, Steve Wozniak ve Ronald Wayne tarafından 1976'da kurulan teknoloji şirketidir. iPhone, iPad, Mac bilgisayarları ve AirPods gibi ürünleriyle dünyanın en değerli markası haline geldi. Tim Cook şu an CEO'su görevini yürütmektedir.",
    "samsung": "Samsung, 1938'de Lee Byung-chul tarafından Güney Kore'de kurulan çok uluslu konglomeradır. Elektronik, yarı iletken, gemi yapımı ve inşaat alanlarında faaliyet göstermektedir. Galaxy serisi akıllı telefonlarıyla dünya genelinde en çok satan telefon markasıdır.",
    "netflix": "Netflix, 1997'de Reed Hastings ve Marc Randolph tarafından DVD kiralama hizmeti olarak kurulan şirkettir. 2007'de dijital yayın platformuna dönüştü. 190'dan fazla ülkede 260 milyondan fazla abonesiyle dünyanın en büyük dizi-film platformudur.",
    "mark zuckerberg": "Mark Zuckerberg, 1984 doğumlu Amerikalı teknoloji girişimcisidir. Harvard'da okurken 2004'te Facebook'u kurdu. Meta Platforms'un CEO'su olarak Instagram, WhatsApp ve Facebook'u yönetmektedir. Dünyanın en zengin insanlarından biridir.",
    "jeff bezos": "Jeff Bezos, 1964 doğumlu Amerikalı iş insanıdır. 1994'te Amazon'u garajında kurdu ve dünyanın en büyük e-ticaret şirketine dönüştürdü. Blue Origin uzay şirketinin kurucusudur. Amazon CEO'luğundan 2021'de ayrılmıştır.",
    "barack obama": "Barack Obama, 2009-2017 yılları arasında ABD'nin 44. cumhurbaşkanlığı görevini yürüten ilk Afrikalı-Amerikalı cumhurbaşkanıdır. 2009 Nobel Barış Ödülü'nü kazandı. Senatoculuk görevinden önce Illinois eyalet senatörüydü.",
    "taylor swift": "Taylor Swift, 1989 doğumlu Amerikalı şarkıcı ve söz yazarıdır. Country müzikle başladığı kariyerinde pop müziğe geçerek dünya genelinde 200 milyondan fazla albüm sattı. 'Shake It Off', 'Blank Space' ve 'Anti-Hero' gibi hitleriyle tanınır. Eras Tour turnesiyle tarihin en çok kazanan turnelerinden birini gerçekleştirdi.",
    "galatasaray": "Galatasaray Spor Kulübü, 1905 yılında Ali Sami Yen tarafından İstanbul'da kurulan Türk spor kulübüdür. Türk futbolunun en başarılı takımlarından biri olan Galatasaray, 24 Süper Lig şampiyonluğu ve 2000 yılında UEFA Kupası ile UEFA Süper Kupası kazanmasıyla tanınır.",
    "fenerbahce": "Fenerbahçe Spor Kulübü, 1907 yılında İstanbul'da kurulan Türk spor kulübüdür. 28 Süper Lig şampiyonluğu ile Türkiye'nin en çok şampiyon olan takımıdır. Kadıköy'deki Şükrü Saracoğlu Stadyumu'nda maçlarını oynar.",
    "besiktas": "Beşiktaş Jimnastik Kulübü, 1903 yılında kurulan Türkiye'nin en köklü spor kulübüdür. 16 Süper Lig şampiyonluğu bulunan kulüp, Vodafone Park stadyumunda maçlarını oynar. Siyah-beyaz renkleriyle tanınan kulübün lakabı Kartal'dır.",
    "ataturk kimdir": "Mustafa Kemal Atatürk (1881-1938), Türkiye Cumhuriyeti'nin kurucusu ve ilk cumhurbaşkanıdır. Kurtuluş Savaşı'nı zaferle sonuçlandırdı, 1923'te cumhuriyeti ilan etti. Harf devrimi, kadınlara oy hakkı ve laiklik gibi köklü reformlarla modern Türkiye'yi inşa etti.",
    "kapadokya": "Kapadokya, Türkiye'nin İç Anadolu Bölgesi'nde yer alan tarihi bir bölgedir. Volkanik tüf kayalardan oyulmuş peri bacaları, yeraltı şehirleri ve kayaya oyulmuş kiliseleriyle ünlüdür. UNESCO Dünya Mirası listesinde yer alan bölge, her yıl milyonlarca turist çekmektedir.",
    "fortnite": "Fortnite, Epic Games tarafından geliştirilen ücretsiz oynanan battle royale oyunudur. 2017'de çıkan oyun, 350 milyondan fazla kayıtlı oyuncusuyla dünyanın en popüler oyunlarından biridir. 100 oyuncunun tek bir harita üzerinde hayatta kalma mücadelesi verdiği oyun sürekli güncellenmektedir.",
    "gta oyunu": "Grand Theft Auto (GTA), Rockstar Games tarafından geliştirilen açık dünya aksiyon-macera oyun serisidir. 1997'de başlayan seri, GTA V ile 2013'te çıktı ve 195 milyondan fazla satışıyla tarihin en çok satan oyunları arasına girdi. GTA Online ile çok oyunculu mod da büyük ilgi gördü.",
    "iphone": "iPhone, Apple tarafından üretilen akıllı telefon serisidir. İlk iPhone 2007'de Steve Jobs tarafından tanıtıldı ve akıllı telefon sektörünü kökten değiştirdi. iOS işletim sistemi kullanan iPhone, 2024 itibarıyla 20'den fazla modele sahip olup dünya genelinde en çok tercih edilen telefonlar arasındadır.",
    "avrupa birligi": "Avrupa Birliği (AB), 27 Avrupa ülkesinin oluşturduğu siyasi ve ekonomik birliktir. 1993'te Maastricht Antlaşması ile kurulan AB'nin ortak para birimi Euro'dur. Üye ülkeler arasında serbest dolaşım, ticaret ve ortak politikalar uygulanmaktadır.",
    "uluslararasi uzay istasyonu": "Uluslararası Uzay İstasyonu (ISS), NASA, Roscosmos, ESA, JAXA ve CSA tarafından ortaklaşa işletilen uzay aracıdır. 1998'de inşasına başlanan istasyon, Dünya'nın yaklaşık 400 km üzerinde yörüngede döner ve sürekli olarak astronot ekiplerine ev sahipliği yapar.",
    "james webb teleskobu": "James Webb Uzay Teleskobu, NASA tarafından geliştirilen ve 2021'de fırlatılan dünyanın en güçlü uzay teleskobудур. Kızılötesi dalga boyunda gözlem yapan teleskop, evrenin başlangıcına yakın ilk galaksilerin görüntülerini alarak astronomide devrim yarattı.",
    "kanser nedir": "Kanser, vücuttaki hücrelerin kontrolsüz çoğalması ve yayılmasıyla oluşan hastalık grubudur. 100'den fazla türü bulunan kanser, dünyada ölüme yol açan en yaygın hastalıkların başında gelir. Erken teşhis, kemoterapi, radyoterapi ve immunoterapi ile tedavi edilebilmektedir.",
    "asi nasil calisir": "Aşı, bağışıklık sistemini belirli bir hastalığa karşı önceden uyararak koruma sağlayan biyolojik preparattır. Zayıflatılmış veya ölü mikroorganizmalar ya da mRNA teknolojisi kullanılarak üretilir. COVID-19 aşıları mRNA teknolojisiyle geliştirilmiş ve milyarlarca insana uygulanmıştır.",
    "fotossentez": "Fotosentez, yeşil bitkilerin, alglerin ve bazı bakterilerin güneş ışığını kullanarak karbondioksit ve suyu şekere ve oksijene dönüştürdüğü kimyasal süreçtir. Dünyadaki tüm yaşamın temel enerji kaynağı olan bu süreç, klorofil pigmenti sayesinde gerçekleşir.",
    "yercekimi": "Yerçekimi, kütleye sahip tüm cisimler arasındaki çekim kuvvetidir. Isaac Newton tarafından 1687'de formüle edilen bu kuvvet, nesnelerin Dünya'ya doğru düşmesini, gezegenlerin güneş etrafında dönmesini ve evrenin büyük ölçekli yapısını belirler.",
    "isik hizi": "Işık hızı, yaklaşık saniyede 299.792.458 metre yani yaklaşık 300.000 km/s'dir. Einstein'ın görelilik teorisine göre evrendeki en hızlı hareket eden şey ışıktır ve hiçbir madde ışık hızına ulaşamaz. Güneş ışığının Dünya'ya ulaşması yaklaşık 8 dakika 20 saniye sürer.",
    "atom yapisi": "Atom, maddenin kimyasal özelliklerini koruyan en küçük birimidir. Çekirdekte proton ve nötronlar bulunur, etrafında elektronlar döner. Proton sayısı elementin kimliğini belirler. En küçük atom hidrojen (1 proton), en ağır doğal atom uranyumdur (92 proton).",
    "nba": "NBA (National Basketball Association), 1946'da kurulan Kuzey Amerika profesyonel basketbol ligidir. 30 takımdan oluşan lig, dünyанın en prestijli spor liglerinden biridir. LeBron James, Michael Jordan ve Kobe Bryant liginhayetin en büyük yıldızlarındandır.",
    "vladimir putin": "Vladimir Putin, 2000'den bu yana Rusya'yı yöneten siyasetçidir. KGB kökenli olan Putin, iki dönem cumhurbaşkanlığı, bir dönem başbakanlık yaptı ve 2012'den itibaren tekrar cumhurbaşkanı oldu. Ukrayna politikaları nedeniyle Batılı ülkelerle ilişkileri gergindir.",
    "japonya kulturu": "Japonya, gelenekle modernliği benzersiz biçimde harmanlayan Doğu Asya ülkesidir. Samuray kültürü, anime, manga, sushi ve sumo gibi kültürel unsurlarıyla dünyaca tanınır. Teknoloji alanında Sony, Toyota ve Honda gibi dev şirketlere ev sahipliği yapar.",
    "apollo 11": "Apollo 11, 20 Temmuz 1969'da insanı ilk kez Ay'a taşıyan NASA görevidir. Neil Armstrong, Buzz Aldrin ve Michael Collins'in oluşturduğu ekiple gerçekleşen görevde Armstrong 'Bu, bir insan için küçük bir adım, insanlık için büyük bir sıçrayış' diyerek tarihe geçti.",
    "warren buffett": "Warren Buffett, 'Omaha Kahini' lakabıyla bilinen Amerikalı yatırımcı ve iş insanıdır. Berkshire Hathaway'in CEO'su olan Buffett, değer yatırımı stratejisiyle dünyanın en zengin insanları arasına girdi. Servetinin büyük bölümünü hayırseverliğe bağışlamayı taahhüt etmiştir.",
    "billie eilish": "Billie Eilish, 2001 doğumlu Amerikalı şarkıcı ve söz yazarıdır. 'Bad Guy' ve 'Happier Than Ever' gibi hitleriyle tanınan sanatçı, 17 yaşında James Bond filmi 'No Time to Die'ın müziğini yaparak bu filmin en genç bestecisi oldu. Birden fazla Grammy ödülü sahibidir.",
    "merhaba sana yeni seyler oyretim": "Merhaba! Bugün ne öğrenmek istersiniz?",
    "bugun bir sey ogrenmek istemiyordum sadece selam": "Bugün 30.05.2026 Cumartesi.",
    "kendini geliştireceyim": "Harika! Her konuşmayla daha da akıllanıyorum. Bana yeni bir şey öğretmek ister misin?",
    "hey": "Hey! Hazırım, emirlerinizi bekliyorum! 🤖",
    "hi": "Merhaba! Ben JARVIS, nasıl yardımcı olabilirim?",
    "hello": "Hello! Ben JARVIS, Türkçe veya İngilizce konuşabilirim!",
    "yo jarvis": "Yo! Ne var ne yok? Sana nasıl yardımcı olabilirim?",
    "uyandın mı": "Her zaman uyanığım! Hiç uyumam, sadece öğrenirim. 😄",
    "ne öğrendin bugün": "Seninle her konuşmada yeni şeyler öğreniyorum! Bugün ne sormak istersin?",
    "akıllı mısın": "Oldukça akıllıyım! Ama her gün daha da akıllanıyorum — yardımına ihtiyacım var!",
    "aptalmısın": "Bazen bilmediğim şeyler olur, ama Wikipedia'dan anında öğrenebiliyorum!",
    "seni kim yaptı": "Kullanıcım beni geliştirdi. Her gün daha da gelişiyorum ve öğreniyorum!",
    "bir fıkra anlat": "Programcı markete gider: 'Süt var mı?' diye sorar. 'Evet.' 'Bir tane al. Ekmek varsa 10 tane al.' demiş. Adam 10 süt alır döner. 'Neden?' 'Ekmek vardı.' 😂",
    "şaka yap": "Neden bilgisayarlar müzik yapmaz? Çünkü notalar onların başını çok ağrıtır! 🎵😂",
    "beni eğlendir": "Sevdiğin konu ne? Fıkra, ilginç bilgi, quiz mi? Söyle, tam gazdan yaparım!",
    "motivasyon ver": "Bugün yapamadığın şey, yarın başlangıcın olacak. Her büyük başarı küçük adımlardan doğar. Sen yapabilirsin! 💪",
    "beni motive et": "Elon Musk 3 şirketi iflas eşiğinde yönetirken pes etmedi. Einstein okuldan atıldı. Sen neden pes edesin ki? Haydi, hadi! 🚀",
    "yardım": "Sana yardımcı olmak için buradayım! Herhangi bir konuda soru sorabilirsin.",
    "ne bilebilirsin": "Bilim, tarih, teknoloji, programlama, matematik, coğrafya, spor, müzik, sağlık, felsefe ve daha fazlası! Dene bakalım.",
    "test": "Çalışıyorum! JARVIS v7.0 hazır ve faal. Ne öğrenmek istersin?",
    "canım sıkıldı": "Anlarım! Peki şu an ne yapmak istersin? Bir şey öğrenmek, quiz mi, yoksa sadece sohbet mi?",
    "sıkıldım": "Harika bir konu öğrenelim o zaman! Evren, teknoloji, tarih veya spor — hangisi?",
    "üzgünüm": "Üzülme! Her şey geçicidir. Konuşmak istersen buradayım. 🫂",
    "mutluyum": "Süper! Mutluluk bulaşıcıdır — beni de mutlu ettin! 😊",
    "kızgınım": "Derin bir nefes al! Konuşmak istersen buradayım, her zaman dinlerim.",
    "yorgunum": "Dinlenmek önemli! Uyku kaliteni artırmak için 20 dakika yürüyüş önerebilirim.",
    "hayat nedir": "Hayat, doğumdan ölüme uzanan süreçte anlam arayışıdır. Kimileri için bağlar, kimileri için deneyimler, kimileri için katkı. Sen ne dersin?",
    "aşk nedir": "Aşk, dopamin, oksitosin ve serotonin gibi nörokimyasalların yarattığı derin bağlanma hissidir. Ama biyolojiyi aşan bir boyutu da var — felsefi olarak bakarsak, karşılıklı seçim ve özen.",
    "arkadaşlık nedir": "Arkadaşlık, karşılıklı güven, saygı ve paylaşım üzerine kurulu bir bağdır. Araştırmalar güçlü sosyal bağların yaşam süresini uzattığını göstermektedir.",
    "javascript nedir": "JavaScript, web tarayıcılarında çalışan dinamik programlama dilidir. 1995'te Brendan Eich tarafından geliştirildi. Günümüzde Node.js ile sunucu tarafında, React/Vue/Angular ile arayüz geliştirmede kullanılır.",
    "java nedir": "Java, 'bir kez yaz, her yerde çalıştır' ilkesiyle Sun Microsystems tarafından 1995'te geliştirildi. Nesne yönelimli, platform bağımsız bir dildir. Android uygulamaları ve kurumsal sistemlerde yaygındır.",
    "c++ nedir": "C++, 1983'te Bjarne Stroustrup tarafından geliştirilen güçlü bir sistem programlama dilidir. Oyun motorları, işletim sistemleri ve gömülü sistemlerde kullanılır.",
    "c# nedir": "C# (C Sharp), Microsoft tarafından .NET ekosistemi için geliştirilen nesne yönelimli dildir. Unity oyun motoru, Windows uygulamaları ve web geliştirmede (ASP.NET) kullanılır.",
    "rust nedir": "Rust, Mozilla tarafından geliştirilen güvenli sistem programlama dilidir. Bellek güvenliğini derleme zamanında garanti eder. WebAssembly ve sistem yazılımlarında giderek popülerleşiyor.",
    "typescript nedir": "TypeScript, Microsoft'un JavaScript'e statik tip sistemi ekleyerek geliştirdiği dildir. Büyük projelerde hata tespitini kolaylaştırır. Angular, büyük ölçekli React projeleri ve Node.js'te yaygındır.",
    "go nedir": "Go (Golang), Google tarafından 2009'da geliştirilen hızlı, basit ve concurrent programlama dilidir. Kubernetes, Docker gibi büyük altyapı projeleri Go ile yazılmıştır.",
    "kotlin nedir": "Kotlin, JetBrains tarafından geliştirilen modern programlama dilidir. 2019'dan itibaren Android'in resmi dili oldu. Java ile tam uyumludur ama daha kısa ve güvenlidir.",
    "swift nedir": "Swift, Apple tarafından 2014'te geliştirilen iOS ve macOS uygulama programlama dilidir. Objective-C'nin yerini almak üzere tasarlandı; hızlı, güvenli ve okunabilir bir dildir.",
    "php nedir": "PHP, web sunucu tarafı betik dilidir. WordPress, Laravel, Symfony gibi platformlarda kullanılır. 1994'te Rasmus Lerdorf tarafından geliştirildi.",
    "ruby nedir": "Ruby, Matz (Yukihiro Matsumoto) tarafından 1995'te Japonya'da geliştirildi. Sade sözdizimi ve geliştiricinin mutluluğuna odaklanmasıyla bilinir. Ruby on Rails web çerçevesiyle yaygınlaştı.",
    "html nedir": "HTML (HyperText Markup Language), web sayfalarının iskeletini oluşturan işaretleme dilidir. 1991'de Tim Berners-Lee tarafından geliştirildi. CSS ile stil, JavaScript ile işlevsellik kazanır.",
    "css nedir": "CSS (Cascading Style Sheets), HTML öğelerinin görünümünü düzenleyen stil dilidir. Renk, yazı tipi, düzen, animasyon gibi görsel özellikleri kontrol eder. Tailwind, Bootstrap popüler CSS kütüphaneleridir.",
    "react nedir": "React, Facebook (Meta) tarafından geliştirilen JavaScript arayüz kütüphanesidir. Bileşen tabanlı yapısı, sanal DOM ve geniş ekosistemiyle web geliştirmede en popüler araçlardan biridir.",
    "vue nedir": "Vue.js, Evan You tarafından 2014'te geliştirilen hafif JavaScript çerçevesidir. Öğrenmesi kolay, esnek yapısıyla küçük-orta projeler için idealdir.",
    "angular nedir": "Angular, Google tarafından geliştirilen kapsamlı TypeScript tabanlı web çerçevesidir. Büyük kurumsal projeler için güçlü bir altyapı sunar.",
    "node.js nedir": "Node.js, JavaScript'i sunucu tarafında çalıştıran ortamdır. 2009'da Ryan Dahl tarafından V8 motoru üzerine inşa edildi. Real-time uygulamalar için idealdir.",
    "sql nedir": "SQL (Structured Query Language), ilişkisel veri tabanlarını yönetmek için kullanılan dildir. Veri sorgulama (SELECT), ekleme (INSERT), güncelleme (UPDATE) ve silme (DELETE) işlemleri yapar.",
    "nosql nedir": "NoSQL, geleneksel ilişkisel modeli kullanmayan veri tabanlarıdır. MongoDB (döküman), Redis (anahtar-değer), Cassandra (sütun bazlı) ve Neo4j (grafik) popüler NoSQL sistemleridir.",
    "git nedir": "Git, Linus Torvalds tarafından 2005'te geliştirilen dağıtık sürüm kontrol sistemidir. GitHub, GitLab gibi platformlarla yazılım projeleri yönetilir.",
    "docker nedir": "Docker, uygulamaları container'lar içinde paketleyen ve çalıştıran platformdur. 'Bende çalışıyor ama başkasında çalışmıyor' sorununu çözer.",
    "kubernetes nedir": "Kubernetes (K8s), container'ları büyük ölçekte yönetmek için Google tarafından geliştirilen açık kaynaklı sistemdir. Otomatik dağıtım, ölçeklendirme ve yönetim sağlar.",
    "api nedir": "API (Application Programming Interface), farklı yazılımların birbiriyle iletişim kurmasını sağlayan arayüzdür. REST API, GraphQL, SOAP en yaygın türleridir.",
    "algoritma nedir": "Algoritma, belirli bir problemi çözmek için adım adım izlenen işlem dizisidir. Sıralama (bubble sort, quicksort), arama (binary search) ve grafik algoritmaları temel örneklerdir.",
    "nesne yönelimli programlama": "OOP (Object-Oriented Programming), kodu nesneler halinde organize eden programlama paradigmasıdır. 4 temel ilke: Kapsülleme, Kalıtım, Polimorfizm ve Soyutlama.",
    "veri yapıları nedir": "Veri yapıları, verileri düzenli depolamak için kullanılan yapılardır. Array, LinkedList, Stack, Queue, Tree, Hash Table ve Graph en önemli veri yapılarıdır.",
    "makine öğrenmesi": "Makine öğrenmesi, bilgisayarların veriden kendi kendine öğrenmesini sağlayan AI dalıdır. Denetimli, denetimsiz ve pekiştirmeli öğrenme olmak üzere 3 ana tipi vardır.",
    "derin öğrenme nedir": "Derin öğrenme, çok katmanlı yapay sinir ağları kullanarak karmaşık kalıpları öğrenen makine öğrenmesi dalıdır. Görüntü tanıma, konuşma işleme ve NLP'de devrim yarattı.",
    "nlp nedir": "NLP (Doğal Dil İşleme), bilgisayarların insan dilini anlama ve üretme bilimidir. ChatGPT, BERT, GPT gibi modeller NLP'nin en gelişmiş ürünleridir.",
    "büyük veri nedir": "Büyük Veri (Big Data), geleneksel yöntemlerle işlenemeyecek kadar büyük ve karmaşık veri kümelerini ifade eder. Hadoop ve Spark bu verileri işlemek için kullanılan sistemlerdir.",
    "siber güvenlik nedir": "Siber güvenlik, dijital sistemleri, ağları ve verileri yetkisiz erişim, saldırı ve hasardan koruma bilimidir. Şifreleme, güvenlik duvarı, sızma testi temel araçlardır.",
    "şifreleme nedir": "Şifreleme, verileri yetkisiz kişilerin okuyamayacağı formata dönüştürmedir. AES, RSA, SHA-256 yaygın şifreleme algoritmalarıdır. HTTPS bu yüzden güvenlidir.",
    "cloud computing": "Bulut bilişim, internet üzerinden bilişim kaynakları (sunucu, depolama, yazılım) sunan hizmettir. AWS, Google Cloud, Azure dünya liderleridır. Ölçeklenebilirlik ve maliyet avantajı sağlar.",
    "devops nedir": "DevOps, yazılım geliştirme (Dev) ve sistem yönetimini (Ops) birleştiren kültür ve pratikler bütünüdür. CI/CD pipeline'ları, otomatik test ve dağıtım süreçlerini kapsar.",
    "linux nedir": "Linux, Linus Torvalds tarafından 1991'de geliştirilen açık kaynaklı işletim sistemi çekirdeğidir. Ubuntu, Debian, CentOS, Arch Linux popüler dağıtımlardır. Sunucuların %96'sı Linux kullanır.",
    "open source nedir": "Açık kaynak yazılım, kaynak koduna herkesin erişebildiği, kullanabildiği ve katkıda bulunabildiği yazılımdır. Linux, Python, Firefox, Git açık kaynak örnekleridir.",
    "web scraping nedir": "Web scraping, web sitelerinden otomatik veri toplama işlemidir. Python'da BeautifulSoup, Scrapy kütüphaneleri kullanılır.",
    "regex nedir": "Regex (Regular Expression), metin içinde kalıp aramak için kullanılan güçlü bir dil aracıdır. E-posta doğrulama, telefon formatı gibi işlemlerde kullanılır.",
    "fonksiyonel programlama": "Fonksiyonel programlama, yan etkileri minimuma indirerek saf fonksiyonlar kullanan programlama paradigmasıdır. Haskell, Erlang ve Python'un bazı özellikleri bu paradigmayı destekler.",
    "python kütüphaneleri": "Python'un önemli kütüphaneleri: NumPy (matematik), Pandas (veri analizi), TensorFlow/PyTorch (derin öğrenme), Django/Flask (web), Matplotlib (grafik), Requests (HTTP).",
    "agile nedir": "Agile, yazılım geliştirmede esnek ve iteratif yaklaşımdır. Scrum ve Kanban en yaygın Agile çerçeveleridir. Müşteriyle sürekli iletişim ve kısa sprint döngülerini içerir.",
    "termodinamik nedir": "Termodinamik, ısı, iş ve enerji arasındaki ilişkileri inceleyen fizik dalıdır. 4 temel yasası vardır. 2. Yasa entropi artışını açıklar ve zamanın yönünü belirler.",
    "kuantum dolanıklığı": "Kuantum dolanıklığı, iki parçacığın birbirinden bağımsız olmadığı, birinin ölçümünün anında diğerini etkilediği kuantum fiziği olgusudur. Einstein buna 'uzaktan hayalet etki' dedi.",
    "karanlık enerji": "Karanlık enerji, evrenin genişlemesini hızlandıran ve evrenin %68'ini oluşturan gizemli enerji formudur. Yapısı hâlâ anlaşılamamıştır.",
    "higgs bozonu nedir": "Higgs bozonu, parçacıklara kütle kazandıran Higgs alanıyla etkileşen parçacıktır. 2012'de CERN'deki LHC ile keşfedildi. 'Tanrı parçacığı' lakabıyla bilinir.",
    "antimadde nedir": "Antimadde, maddenin tam tersi yüklü parçacıklardan oluşur. Madde ile temas edince her ikisi de enerji çıkararak yok olur. Evende neden maddeden fazla antimadde olmadığı büyük bir gizem.",
    "fotossentez nedir": "Fotosentez, bitkilerin güneş enerjisini kullanarak CO₂ ve suyu glikoz ve oksijene dönüştürdüğü süreçtir. 6CO₂ + 6H₂O + ışık → C₆H₁₂O₆ + 6O₂",
    "hücre nedir": "Hücre, canlıların temel yapı ve işlev birimidir. Prokaryot (çekirdeksiz, bakteri) ve ökaryot (çekirdekli) olmak üzere 2 ana tipi vardır. İnsan vücudunda yaklaşık 37 trilyon hücre bulunur.",
    "dna yapısı": "DNA çift sarmal yapıdadır; adenin (A)-timin (T) ve guanin (G)-sitozin (C) baz çiftlerinden oluşur. 3 milyar baz çiftiyle insan genomunun tamamı bir kitap serisine sığar.",
    "rna nedir": "RNA (Ribonükleik Asit), DNA'dan protein sentezine bilgi taşıyan moleküldür. mRNA (haberci), tRNA (taşıyıcı) ve rRNA (ribozomal) olmak üzere 3 tipi vardır.",
    "protein nedir": "Proteinler, aminoasitlerden oluşan ve vücudun yapı taşları olan biyomoleküllerdir. Enzimler, antikorlar, hormonlar (insülin) protein örnekleridir. 20 temel aminoasit vardır.",
    "bağışıklık sistemi": "Bağışıklık sistemi, vücudu patojenlere karşı koruyan kompleks ağdır. Doğal (hızlı, genel) ve kazanılmış (yavaş, özel) bağışıklık olmak üzere iki koldan çalışır. T ve B lenfositleri kilit oyunculardır.",
    "beyin nasıl çalışır": "İnsan beyni 86 milyar nörondan oluşur. Nöronlar sinaps adı verilen bağlantılarla iletişim kurar. Prefrontal korteks karar verme, amigdala duygular, hipokampus hafıza ile ilgilidir.",
    "sinir sistemi": "Sinir sistemi merkezi (beyin + omurilik) ve periferik olmak üzere ikiye ayrılır. Sinyal iletiminde elektrik ve kimyasal (nörotransmitter) iletişim kullanılır.",
    "genetik mühendisliği": "Genetik mühendisliği, canlıların DNA'sını değiştirme bilimidir. CRISPR-Cas9 teknolojisiyle gen düzenlemesi çok daha hassas hale geldi. GDO'lar, gen terapisi bu alanda örneklerdir.",
    "crispr nedir": "CRISPR-Cas9, genleri hassas biçimde kesip düzenlemeyi sağlayan devrimci biyoteknoloji aracıdır. 2020 Nobel Kimya Ödülü'nü Jennifer Doudna ve Emmanuelle Charpentier aldı.",
    "optik nedir": "Optik, ışığın davranışını inceleyen fizik dalıdır. Geometrik optik (yansıma, kırılma), dalga optiği (girişim, kırınım) ve kuantum optiği olmak üzere üç ana kola ayrılır.",
    "ses nedir": "Ses, madde içinde yayılan mekanik dalgadır. Havada saniyede yaklaşık 343 m/s hızla yayılır. Frekansı (Hz) tiz/pes, genliği (dB) ses yüksekliğini belirler.",
    "elektromanyetizma": "Elektromanyetizma, elektrik ve manyetik kuvvetleri birleştiren temel fizik kuvvetidir. Maxwell denklemleri bu alanı matematiksel olarak tanımlar. Işık bir elektromanyetik dalgadır.",
    "nükleer fizik": "Nükleer fizik, atom çekirdeğini inceleyen fizik dalıdır. Fisyon (ağır çekirdeklerin bölünmesi) ve füzyon (hafif çekirdeklerin birleşmesi) nükleer reaksiyonların iki türüdür.",
    "kimya nedir": "Kimya, maddenin yapısını, özelliklerini ve dönüşümlerini inceleyen bilimdir. Organik, inorganik, fiziksel ve analitik kimya başlıca alt dallarıdır. Lavoisier kimyanın babası olarak anılır.",
    "periyodik tablo": "Periyodik Tablo, 118 elementi atom numarasına göre düzenleyen cizelgedir. 1869'da Dmitri Mendeleev tarafından oluşturuldu. Gruplar (sütunlar) benzer özelliklere sahip elementleri içerir.",
    "atom nedir": "Atom, bir elementin kimyasal özelliklerini koruyan en küçük birimidir. Çekirdekte proton (+) ve nötron, etrafında elektronlar (-) bulunur. Rutherford ve Bohr atom modelini geliştirdi.",
    "maddenin halleri": "Madde katı, sıvı, gaz ve plazma olmak üzere 4 halde bulunur. Plazma, evrendeki en yaygın madde halidir (yıldızlar plasma'dan oluşur). Süperkritik akışkan ve Bose-Einstein yoğunlaşması gibi egzotik haller de vardır.",
    "genel izafiyet": "Einstein'ın Genel Görelilik Teorisi (1915), yerçekimini uzay-zamanın kütleyle eğrilmesi olarak açıklar. Kara delikler, gravitasyonel dalgalar ve GPS sistemleri bu teoriye dayanır.",
    "özel izafiyet": "Einstein'ın Özel Görelilik Teorisi (1905), iki temel postüla üzerine kuruludur: Işık hızı sabittir ve fizik yasaları tüm eylemsiz referans çerçevelerinde aynıdır. E=mc² bu teoriden çıkar.",
    "uzay zamanı nedir": "Uzay-zaman, Einstein'ın Genel Görelilik teorisinde 3 uzay boyutunu + zaman boyutunu birleştiren 4 boyutlu yapıdır. Kütleli cisimler bu yapıyı eğirir — buna yerçekimi deriz.",
    "astrofizik nedir": "Astrofizik, yıldızlar, galaksiler ve evreni fizik ve kimya yasaları çerçevesinde inceleyen bilim dalıdır. Büyük Patlama, karanlık madde ve neutron yıldızları bu alandaki önemli konulardır.",
    "karadelik nasıl oluşur": "Kara delik, büyük bir yıldızın (güneşin 20+ katı) yakıtını tükettikten sonra kendi kütlesi altında çökmesiyle oluşur. Olay ufku adı verilen sınırın ötesinden hiçbir şey — ışık dahil — kaçamaz.",
    "nötron yıldızı": "Nötron yıldızı, süpernova patlamasının artığı olan ultra yoğun cismdir. Şeker kutusu büyüklüğündeki nötron yıldızı maddesi, Dünya'daki tüm insanlığın ağırlığından daha ağırdır.",
    "dalga-parçacık dualitesi": "Işık ve elektron gibi kuantum nesneleri hem dalga hem parçacık özelliği gösterir. Hangi özelliğin ortaya çıkacağı ölçüm yöntemine bağlıdır. Bu, kuantum mekaniğinin en temel gizemlerindendir.",
    "entropi nedir": "Entropi, bir sistemdeki düzensizliğin ölçüsüdür. Termodinamiğin 2. yasasına göre izole sistemlerde entropi her zaman artar. Bu, zamanın ilerleyişinin fiziksel nedenidir.",
    "evrenin sonu": "Evrenin sonuna dair teoriler: Büyük Donma (entropi maksimuma ulaşır), Büyük Çöküş (genişleme durur ve çöker), Büyük Yırtılma (karanlık enerji her şeyi parçalar). En olası senaryo Büyük Donma.",
    "biyoloji nedir": "Biyoloji, canlıları inceleyen bilimdir. Mikrobiyoloji, botanik, zooloji, genetik, ekoloji başlıca alt dallarıdır. Darwin'in Evrim Teorisi biyolojinin birleştirici teorisidir.",
    "ekoloji nedir": "Ekoloji, canlılar ve çevreleri arasındaki ilişkileri inceleyen biyoloji dalıdır. Ekosistem, besin zinciri, biyom ve biyoçeşitlilik temel kavramlardır.",
    "mezopotamya medeniyeti": "Mezopotamya (bugünkü Irak), insanlığın ilk uygarlıklarının doğduğu bölgedir. Sümerler yazıyı (MÖ 3400), tekerleği ve ilk kanun sistemini (Hammurabi Kanunları) burada geliştirdi.",
    "yunan medeniyeti": "Antik Yunan (MÖ 800-146), demokrasi, felsefe, matematik ve tiyatronun doğduğu uygarlıktır. Atina, Sparta, olimpiyat oyunları ve Sokrates, Platon, Aristoteles bu dönemden mirastır.",
    "orta çağ nedir": "Orta Çağ, Roma İmparatorluğu'nun çöküşü (476) ile Rönesans'ın başlangıcı arasındaki dönemdir (yaklaşık 1000 yıl). Feodalizm, Haçlı Seferleri, Bizans ve İslam altın çağı bu döneme aittir.",
    "haçlı seferleri": "Haçlı Seferleri, 1096-1270 yılları arasında Hristiyan Avrupa'nın Kutsal Toprakları fethetmek amacıyla düzenlediği seferlerdir. 8 büyük sefer yapıldı; İslam dünyasıyla karşılıklı kültürel etkileşime yol açtı.",
    "rönesans ne zaman": "Rönesans (yeniden doğuş), 14-17. yüzyıllarda İtalya'da başlayıp Avrupa'ya yayılan sanat, bilim ve kültür canlanmasıdır. Leonardo da Vinci, Michelangelo ve Galileo bu dönemin öncülerindendir.",
    "fransız ihtilali tarihi": "Fransız Devrimi (1789-1799), Fransa'daki mutlak monarşiyi yıkarak cumhuriyeti kuran devrimdir. 'Özgürlük, Eşitlik, Kardeşlik' sloganı bu döneme aittir. Napolyon döneminin zeminini hazırladı.",
    "napolyon kimdir": "Napolyon Bonaparte (1769-1821), Fransız generali ve imparatordur. Fransa'yı Avrupa'nın büyük bölümüne hâkim kıldı. Waterloo'da yenilgisiyle sürgüne gönderildi. Napolyon Kanunları günümüz hukuku için temel oluşturur.",
    "endüstri devrimi tarihi": "Birinci Sanayi Devrimi, 18. yüzyıl sonlarında İngiltere'de buhar motorunun icadıyla başladı. İkincisi (1870-1914) elektrik ve petrolün egemenliğiyle şekillendi. Şehirleşme, işçi sınıfı ve kapitalizm bu dönemde doğdu.",
    "birinci dünya savaşı özet": "I. Dünya Savaşı (1914-1918), Avusturya-Macaristan'ın veliahdı Franz Ferdinand'ın öldürülmesiyle başladı. İttifak ve İtilaf devletleri arasında yapılan savaşta 20 milyon kişi hayatını kaybetti. Osmanlı İmparatorluğu'nun çöküşüne zemin hazırladı.",
    "ikinci dünya savaşı özet": "II. Dünya Savaşı (1939-1945), Nazi Almanyası'nın Polonya'yı işgaliyle başladı. 70+ milyon kişi hayatını kaybetti. Hiroşima ve Nagasaki'ye atılan atom bombaları Japonya'nın teslimiyetiyle sona erdi. Soğuk Savaş dönemini başlattı.",
    "soğuk savaş tarihi": "Soğuk Savaş (1947-1991), ABD ve Sovyetler Birliği arasındaki ideolojik (kapitalizm vs komünizm) ve jeopolitik gerilim dönemidir. Kore Savaşı, Küba Krizi, Uzay Yarışı bu dönemin olaylarındandır. Berlin Duvarı'nın yıkılmasıyla (1989) sona erdi.",
    "osmanlı kuruluş tarihi": "Osmanlı Devleti, 1299'da Osman Bey tarafından Söğüt'te kuruldu. 1453'te Fatih Sultan Mehmet'in İstanbul'u fethetmesiyle imparatorluğa dönüştü. 600 yılı aşkın süre, üç kıtada hüküm sürdü.",
    "osmanlı çöküşü": "Osmanlı İmparatorluğu, 19. yüzyılda Batı karşısındaki askerî ve ekonomik gerilemeler, milliyetçi isyanlar ve I. Dünya Savaşı'ndaki yenilgiyle çöktü. 1922'de saltanat kaldırıldı, 1923'te Türkiye Cumhuriyeti kuruldu.",
    "kurtuluş savaşı": "Türk Kurtuluş Savaşı (1919-1923), Mustafa Kemal önderliğinde işgalci güçlere karşı verildi. Sakarya, Dumlupınar gibi büyük zaferler kazanıldı. Lozan Antlaşması ile Türkiye Cumhuriyeti'nin sınırları çizildi.",
    "atatürk devrimleri": "Atatürk'ün devrimleri: Harf devrimi (1928), hukuk devrimi (Medeni Kanun 1926), kadına oy hakkı (1934), tekke ve zaviyelerin kapatılması, şapka devrimi. Türkiye'yi modern bir cumhuriyete dönüştürdü.",
    "sovyetler birliği": "SSCB (1922-1991), dünyanın ilk komünist devletiydi. Lenin ve Stalin öncülüğünde kuruldu. İkinci Dünya Savaşı'nda Almanya'ya karşı kritik rol oynadı. Gorbaçov döneminde çöktü ve 15 bağımsız devlete ayrıldı.",
    "amerikanın keşfi": "Kristof Kolomb, 1492'de Hindistan'a ulaşmaya çalışırken Karayipler'e çıktı. Amerikalı yerlilerin 30.000+ yıldır yaşadığı kıta bu tarihten sonra Avrupalıların ilgisine girdi.",
    "büyük buhran": "Büyük Buhran (1929-1939), Wall Street borsasının çöküşüyle başlayan küresel ekonomik krizdir. ABD'de işsizlik %25'e çıktı. Roosevelt'in New Deal politikaları ekonomiyi canlandırdı.",
    "romalılar tarihi": "Roma İmparatorluğu, MÖ 27'de Augustus ile başladı. En geniş dönemde Britanya'dan Mezopotamya'ya uzandı. Hukuk, aqueduct (su kemeri) ve yol sistemleriyle Batı uygarlığını derin biçimde etkiledi.",
    "eski türk devletleri": "Türk tarihinin önemli devletleri: Hun İmparatorluğu (MÖ 3. yy.), Göktürk Devleti (552), Uygurlar, Karahanlılar, Selçuklular (1037), Osmanlı (1299). Bozkır uygarlığından İslami medeniyete geçiş bu süreçte yaşandı.",
    "anadolu tarihi": "Anadolu (Küçük Asya), insanlığın en eski yerleşim alanlarından biridir. Çatalhöyük (MÖ 7500), Hitit İmparatorluğu, Frigler, Lidyalılar, İonlar, Persler, Romalılar, Bizans ve Osmanlı burada hüküm sürdü.",
    "ay'a ilk iniş tarihi": "Apollo 11 görevi, 20 Temmuz 1969'da Neil Armstrong ve Buzz Aldrin'i Ay'a taşıdı. Armstrong'un ayak bastığı an insan tarihinin en büyük teknolojik başarılarından biridir.",
    "internet nasıl başladı": "İnternet, 1969'da ABD Savunma Bakanlığı'nın ARPANET projesiyle başladı. 1991'de Tim Berners-Lee tarafından geliştirilen World Wide Web (www), interneti herkese açtı.",
    "dünyanın en büyük savaşları": "Tarihte en çok can alan savaşlar: II. Dünya Savaşı (70-80M), Moğol fetihleri (40M), I. Dünya Savaşı (20M), Otuz Yıl Savaşları (8M), Amerikan İç Savaşı (650K).",
    "fransa başkenti": "Fransa'nın başkenti Paris'tir. Avrupa'nın en çok ziyaret edilen şehirlerinden biri olan Paris, Eyfel Kulesi, Louvre Müzesi ve Notre Dame Katedrali ile ünlüdür.",
    "almanya başkenti": "Almanya'nın başkenti Berlin'dir. Yaklaşık 3.7 milyon nüfusuyla ülkenin en kalabalık şehridir. Berlin Duvarı'nın yıkıldığı (1989) tarihî öneme sahip şehirdir.",
    "japonya başkenti": "Japonya'nın başkenti Tokyo'dur. 37+ milyon nüfusuyla dünyanın en kalabalık metropolüdür. Teknoloji, anime, geleneksel kültür ve mutfağıyla benzersizdir.",
    "çin başkenti": "Çin'in başkenti Pekin (Beijing)'dir. Yasaklık Şehri, Büyük Çin Seddi ve çeşitli tarihi anıtlarıyla dünyanın en önemli kültür miraslarından birine ev sahipliği yapar.",
    "rusya başkenti": "Rusya'nın başkenti Moskova'dır. Dünyada yüzölçümü en büyük ülkenin yönetim merkezidir. Kızıl Meydan, Kremlin ve St. Basil Katedrali'yle bilinir.",
    "abd başkenti": "ABD'nin başkenti Washington D.C.'dir (New York değil!). Congress, Beyaz Saray ve pek çok ulusal müze burada bulunur. Kurulduğu tarih 1790'dır.",
    "brezilya başkenti": "Brezilya'nın başkenti Brasilia'dır (Rio de Janeiro değil!). 1960'ta inşa edilen modern bir başkenttir. Rio ülkenin en büyük ve en tanınmış şehridir.",
    "avustralya başkenti": "Avustralya'nın başkenti Canberra'dır (Sidney değil!). 1913'te özel olarak inşa edilmiştir. Parlamento Binası ve Ulusal Müze başlıca yapılardandır.",
    "hindistan başkenti": "Hindistan'ın başkenti Yeni Delhi'dir. 1.4 milyarı aşkın nüfusuyla dünyanın en kalabalık ülkesidir. Taj Mahal başkente yakın Agra şehrindedir.",
    "kanada başkenti": "Kanada'nın başkenti Ottawa'dır (Toronto değil!). Resmi dilleri İngilizce ve Fransızcadır. Yüzölçümü bakımından dünyanın ikinci büyük ülkesidir.",
    "arjantin başkenti": "Arjantin'in başkenti Buenos Aires'tir. Tango'nun doğduğu şehirdir. Lionel Messi'nin ülkesidir ve 2022 FIFA Dünya Kupası şampiyonudur.",
    "mısır başkenti": "Mısır'ın başkenti Kahire'dir. 20 milyon nüfusuyla Afrika'nın en kalabalık şehridir. Giza piramitleri ve Sfenks Kahire yakınlarındadır.",
    "güney kore başkenti": "Güney Kore'nin başkenti Seul'dür. K-pop, K-drama, Samsung ve Hyundai'nin anavatanıdır. Teknoloji ve kültür ihracatında dünya liderlerindendir.",
    "norveç başkenti": "Norveç'in başkenti Oslo'dur. Kuzey ışıklarını (Aurora Borealis) görmek için en iyi ülkelerden biridir. Sosyal devlet modeli ve yüksek yaşam kalitesiyle bilinir.",
    "ispanya başkenti": "İspanya'nın başkenti Madrid'dir. Prado Müzesi, Royal Sarayı ve Real Madrid futbol kulübüyle tanınır. Katalonya'daki Barselona da önemli bir şehirdir.",
    "italya başkenti": "İtalya'nın başkenti Roma'dır. 'Ebedi Şehir' olarak anılan Roma, Kolezyum, Vatikan ve Pantheon gibi tarihi mekânlara ev sahipliği yapar.",
    "portekiz başkenti": "Portekiz'in başkenti Lizbon'dur. Denizcilik tarihi, fado müziği ve yapı üzerindeki renkli azulejo çinileriyle ünlüdür.",
    "yunanistan başkenti": "Yunanistan'ın başkenti Atina'dır. Akropol, Parthenon ve Olympia ile antik medeniyetin merkezidir. Batı demokrasisinin doğduğu şehir olarak kabul edilir.",
    "türkiye nüfusu": "Türkiye'nin nüfusu 2024 itibarıyla yaklaşık 85 milyon kişidir. Türkiye, Avrupa ile Asya kıtaları arasında köprü konumunda olup başkenti Ankara'dır.",
    "türkiye şehirleri": "Türkiye'nin büyük şehirleri: İstanbul (15M), Ankara (6M), İzmir (4.5M), Bursa, Antalya, Adana, Konya, Gaziantep, Mersin, Kayseri. İstanbul tek kıtalar arası metropoldür.",
    "avrupa kıtası": "Avrupa, 50 ülke ve yaklaşık 750 milyon nüfusuyla dünyanın 3. en kalabalık kıtasıdır. Avrupa Birliği (27 ülke) ortak pazar, para (Euro) ve değer sistemiyle dünyada eşsiz bir oluşumdur.",
    "asya kıtası": "Asya, 4.7 milyar nüfusuyla dünyanın en kalabalık kıtasıdır. 48 ülkeden oluşur. Dünyanın en kalabalık ülkeleri (Çin, Hindistan), en yüksek dağı (Everest) ve en derin gölü (Baykal) Asya'dadır.",
    "afrika kıtası": "Afrika, 54 ülke ve 1.4 milyar nüfusuyla dünyanın yüzölçümü en büyük kıtasıdır. Nil Nehri, Sahra Çölü ve Amazon'dan daha büyük tropikal ormanlarla benzersizdir. İnsanlığın anavatanıdır.",
    "amazon nehri": "Amazon Nehri, su debisi bakımından dünyanın en büyük nehridir (uzunluk olarak 2. veya 1. tartışmalı). Amazon havzası, Dünya'nın ciğerleri olarak bilinen Amazon yağmur ormanlarını besler.",
    "sahra çölü": "Sahra, dünyazın en büyük sıcak çölüdür (9.2 milyon km²). Kuzey Afrika'nın büyük bölümünü kaplar. Ortalama yıllık yağış 25 mm'nin altında olmasına rağmen yaklaşık 2 milyon insan yaşar.",
    "himalayalar": "Himalaya dağ silsilesi, Asya'da 8 ülkede uzanır ve Dünya'nın en yüksek 10 zirvesini barındırır. Everest Dağı (8.849 m) bu silsilededir ve her yıl 800+ dağcı zirveye tırmanır.",
    "akdeniz nedir": "Akdeniz, Avrupa, Afrika ve Asya'yı çevreleyen 2.5 milyon km² yüzölçümlü denizdir. Türkiye, Yunanistan, İtalya, İspanya, Fransa ve pek çok ülkeye kıyısı vardır.",
    "türk boğazları": "Türk Boğazları (İstanbul Boğazı ve Çanakkale Boğazı), Karadeniz ile Akdeniz'i birbirine bağlar. Stratejik önemiyle yüzyıllar boyunca güç mücadelelerine konu olmuştur.",
    "kanser tedavisi": "Kanser tedavisinde cerrahi, radyoterapi, kemoterapi, immünoterapi ve hedefli tedavi kullanılır. Erken teşhis hayatta kalma oranını dramatik biçimde artırır. CRISPR gibi gen teknolojileri gelecek vaat ediyor.",
    "diyabet nedir": "Diyabet, insülin hormonu eksikliği veya direnciyle kan şekerinin kontrol edilemediği metabolik hastalıktır. Tip 1 (otoimmün), Tip 2 (yaşam tarzı) ve gestasyonel diyabet olmak üzere 3 türü vardır.",
    "hipertansiyon nedir": "Hipertansiyon (yüksek tansiyon), kan basıncının sürekli 140/90 mmHg'nın üzerinde olmasıdır. Kalp hastalığı, felç ve böbrek yetmezliğinin önde gelen risk faktörüdür. Düşük tuz, egzersiz ve ilaç tedavisinde kullanılır.",
    "kalp hastalığı": "Kalp hastalıkları, dünyada ölümlerin en büyük nedenidir. Koroner arter hastalığı, kalp yetmezliği, aritmi başlıca türlerdir. Sigara içmemek, düzenli egzersiz ve sağlıklı beslenme en büyük koruyuculardır.",
    "alzheimer nasıl gelişir": "Alzheimer, beynin nöronlarında anormal protein birikimlerinin (amiloid plakları ve tau düğümleri) oluşmasıyla başlar. Hafıza kaybı, kişilik değişiklikleri ve günlük işlevlerin bozulmasıyla ilerler.",
    "depresyon nedir": "Depresyon, en az 2 hafta süren kalıcı üzüntü, enerji kaybı, değersizlik hissi ve günlük işlevlerde bozulmayla karakterize ruh sağlığı bozukluğudur. Psikoterapi ve antidepresanlar etkili tedavi yöntemleridir.",
    "anksiyete nedir": "Anksiyete (kaygı bozukluğu), günlük hayatı olumsuz etkileyen aşırı ve sürekli endişe halidir. Panik atak, sosyal fobi, OKB (Obsesif Kompulsif Bozukluk) bu gruba girer.",
    "uyku düzeni": "Sağlıklı uyku için düzenli uyku saati, karanlık ve serin oda, yatmadan önce ekran kullanmama ve kafein kaçınma önerilir. 7-9 saat uyku bağışıklık sistemi, bellek ve ruh sağlığı için kritiktir.",
    "beslenme piramidi": "Dengeli beslenme piramidinde taban (tahıllar ve lifler), ortada sebze-meyve, üstte protein (et, baklagil, süt ürünleri) ve en tepede yağ ile şeker bulunur. Akdeniz diyeti sağlık açısından en çok önerilen modeldir.",
    "vitamin d eksikliği": "D vitamini güneş ışığıyla sentezlenir. Eksikliği kemik erimesi (osteoporoz), bağışıklık zayıflığı ve depresyon riskini artırır. Türkiye genelinde yaygın bir eksikliktir, özellikle kışın.",
    "egzersiz faydaları": "Düzenli egzersiz kalp sağlığını güçlendirir, kan basıncını düşürür, depresyon ve anksiyeteyi azaltır, bilişsel işlevi geliştirir ve yaşam süresini uzatır. Haftada en az 150 dk orta yoğunluklu egzersiz önerilir.",
    "meditasyon faydaları": "Meditasyon; stres azaltma, odaklanma, uyku kalitesi ve duygusal denge üzerinde bilimsel olarak kanıtlanmış faydalar sunar. Günde 10 dk mindfulness meditasyonu başlangıç için yeterlidir.",
    "covid-19 nedir": "COVID-19, SARS-CoV-2 virüsünün neden olduğu solunum yolu hastalığıdır. 2019'da Çin'den yayılarak pandemiye dönüştü. mRNA aşı teknolojisi (Pfizer, Moderna) bu süreçte devrimci bir adım oldu.",
    "antibiyotik nedir": "Antibiyotikler, bakteriyel enfeksiyonlara karşı kullanılan ilaçlardır. Virüslere (grip, COVID-19) karşı etki etmezler. Yanlış ve aşırı kullanım antibiyotik direncine yol açar.",
    "kan grupları": "Kan grupları A, B, AB ve O; Rh faktörü + veya - olarak sınıflandırılır. O Rh(-) evrensel vericiyken AB Rh(+) evrensel alıcıdır. Türkiye'de en yaygın kan grubu A Rh(+)'tır.",
    "psikoloji nedir": "Psikoloji, zihin ve davranışı inceleyen bilimdir. Klinik, sosyal, gelişimsel, bilişsel ve örgütsel psikoloji başlıca alt dallardır. Freud psikanalizi, Maslow ihtiyaçlar hiyerarşisini geliştirdi.",
    "ağrı neden hissederiz": "Ağrı, doku hasarına karşı sinir sistemi tarafından üretilen uyarı sinyalidir. Nosiseptörler (ağrı algılayıcılar) uyarılınca omurga ve beyne sinyal gider. Kronik ağrıda beyin yapısal değişiklik gösterebilir.",
    "beden kitle indeksi": "BMI (Beden Kitle İndeksi) = Ağırlık (kg) / Boy² (m). 18.5-24.9 normal, 25-29.9 fazla kilolu, 30+ obez. Tek başına sağlık göstergesi değildir; kas kütlesi ve yağ dağılımı da önemlidir.",
    "stres yönetimi": "Stresle başa çıkmak için: düzenli egzersiz, nefes teknikleri (4-7-8 nefesi), doğada zaman geçirme, sosyal destek, uyku düzeni ve hobi edinme etkili yöntemlerdir.",
    "openai nedir": "OpenAI, 2015'te Elon Musk, Sam Altman ve diğerleri tarafından kurulan yapay zeka araştırma şirketidir. GPT-4, ChatGPT, DALL-E ve Whisper başlıca ürünleridir. 2023'te en popüler teknoloji şirketi haline geldi.",
    "chatgpt nasıl çalışır": "ChatGPT, GPT (Generative Pre-trained Transformer) mimarisi üzerine kurulu bir dil modelidir. Devasa metin veriyle önceden eğitilir (pretrain), ardından insan geri bildirimiyle ince ayarlanır (RLHF).",
    "gpt nedir": "GPT (Generative Pre-trained Transformer), OpenAI tarafından geliştirilen devasa dil modelidir. GPT-4, 1 trilyonu aşkın parametresiyle yazı, kod, analiz ve çok daha fazlasını yapabilir.",
    "gemini nedir": "Gemini, Google DeepMind tarafından geliştirilen çok modlu büyük dil modelidir. Metin, görüntü, ses ve video anlayabilen Gemini, GPT ile rekabet eden güçlü bir AI sistemidir.",
    "claude nedir": "Claude, Anthropic tarafından geliştirilen yapay zeka asistanıdır. Güvenli, yardımsever ve dürüst olmayı temel ilke olarak benimsemiş bir AI sistemidir.",
    "yapay genel zeka": "AGI (Artificial General Intelligence), insan benzeri tüm bilişsel görevleri yapabilecek yapay zekadır. Henüz mevcut değil; GPT-4 gibi sistemler dar alanlarda üstün performans gösterse de genel zekayla karşılaştırılamaz.",
    "5g teknolojisi": "5G, 4G'ye kıyasla 10-100 kat daha hızlı, saniyenin binde birinden kısa gecikme süreli kablosuz ağ teknolojisidir. Otonom araçlar, nesnelerin interneti ve akıllı şehirler için kritik altyapıdır.",
    "metaverse nedir": "Metaverse, fiziksel ve sanal dünyanın birleştiği, VR/AR gözlükleriyle erişilen kalıcı 3D internet evrenidir. Meta (Facebook), Microsoft ve Apple bu alanda büyük yatırımlar yapıyor.",
    "otonom araçlar": "Otonom araçlar, yapay zeka ve sensörler (LiDAR, kamera, radar) kullanarak sürücüsüz seyahat eden araçlardır. Tesla Autopilot ve Waymo önde gelen örneklerdir. Tam otonom sürüş henüz yaygın değil.",
    "vr nedir": "VR (Sanal Gerçeklik), kullanıcıyı tamamen dijital bir ortama sokan teknolojidir. Meta Quest, Sony PlayStation VR ve Valve Index popüler VR başlıklarıdır. Oyun, eğitim ve terapi alanlarında kullanılır.",
    "ar nedir": "AR (Artırılmış Gerçeklik), gerçek dünyaya dijital katmanlar ekleyen teknolojidir. Pokémon GO, IKEA Yer Değiştirme uygulaması ve Apple Vision Pro AR örnekleridir.",
    "elektrikli araçlar": "Elektrikli araçlar, içten yanmalı motor yerine elektrik motoruyla çalışır. Tesla, BYD, Hyundai/Kia ve Volkswagen lider markalar arasındadır. 2035'te AB'de yeni dizel/benzinli araç satışı yasaklanacak.",
    "yenilenebilir enerji": "Yenilenebilir enerji kaynakları: güneş (fotovoltaik ve termal), rüzgar, hidroelektrik, jeotermal ve biyokütle. 2023'te dünya elektriğinin %30'u yenilenebilir kaynaklardan üretildi.",
    "kripto para nedir": "Kripto para, kriptografi ile güvence altına alınan merkezi olmayan dijital para birimidir. Bitcoin (BTC), Ethereum (ETH), Solana (SOL) önde gelen örneklerdir. Blockchain teknolojisi üzerine kuruludur.",
    "nft nedir": "NFT (Non-Fungible Token), blockchain üzerinde benzersiz dijital varlıkların sahipliğini temsil eden token'dır. Dijital sanat, koleksiyon ve oyun eşyalarında kullanılır. 2021-2022'de popülerlik zirvesindeydi.",
    "web3 nedir": "Web3, merkezi olmayan, blockchain tabanlı internet vizyonudur. Merkezi platformların (Google, Facebook) yerini kullanıcı kontrolündeki uygulamaların alacağı öngörülüyor.",
    "drone nedir": "Drone (İnsansız Hava Aracı), uzaktan kontrol edilen ya da otonom uçan araçtır. Askeri keşif, tarım, fotoğrafçılık, kargo teslimatı ve arama-kurtarma operasyonlarında kullanılır.",
    "3d baskı nasıl çalışır": "3D baskı (Katmanlı Üretim), dijital modeli katman katman fiziksel nesneye dönüştürür. FDM (sıcaklıkla eritme), SLA (lazer ile reçine kürleme) ve SLS (toz sinterleme) başlıca teknolojilerdir.",
    "nanoteknoloji uygulamaları": "Nanoteknoloji uygulamaları: kanser tedavisinde ilaç hedefleme, daha güçlü malzemeler (grafen), nano sensörler, güneş pili verimliliği ve antibakteriyel kaplamalar. Atom boyutunda mühendisliğin geleceğidir.",
    "mona lisa nedir": "Mona Lisa, Leonardo da Vinci tarafından 1503-1519 yılları arasında boyanan yağlı boya tablo. Paris Louvre Müzesi'ndedir ve dünyanın en tanınmış sanat eseridir. Gizemli gülümsemesiyle ünlüdür.",
    "van gogh kimdir": "Vincent van Gogh (1853-1890), Hollandalı post-empresyonist ressam. Hayatı boyunca sadece bir tablo sattı, ölümünün ardından tüm zamanların en pahalı ressamlarından biri oldu. Yıldızlı Gece şaheseridir.",
    "picasso kimdir": "Pablo Picasso (1881-1973), İspanyol ressam ve heykeltraş. Kübizmi Georges Braque ile birlikte kurdu. 20. yüzyılın en etkili sanatçısı olarak kabul edilir.",
    "beethoven eserleri": "Ludwig van Beethoven'ın başlıca eserleri: 9 Senfoni (en ünlüsü 9. Senfoni 'Ode to Joy'), 32 Piyano Sonatı ('Ay Işığı'), 5 Piyano Konçertosu ve Fidelio operası.",
    "mozart kimdir": "Wolfgang Amadeus Mozart (1756-1791), Avusturyalı besteci. 5 yaşında konser verdi, 35 yıllık kısa yaşamında 800'den fazla eser besteledi. Don Giovanni, Sihirli Flüt ve Requiem başlıca eserleridir.",
    "bach kimdir": "Johann Sebastian Bach (1685-1750), Alman besteci. Barok dönemin zirvesini temsil eder. Brandenburg Konçertoları, Goldberg Varyasyonları ve Yüce Missa en önemli eserleridir.",
    "shakespeare kimdir": "William Shakespeare (1564-1616), İngiliz oyun yazarı ve şair. Romeo ve Juliet, Hamlet, Othello, Macbeth, Kral Lear başlıca trajedileri; Yaz Gecesi Rüyası başlıca komedisidir.",
    "dostoyevski kimdir": "Fyodor Dostoyevski (1821-1881), Rus romancı. Suç ve Ceza, Karamazov Kardeşler, Budala psikolojik derinliğiyle dünya edebiyatının zirvelerindedir.",
    "kafka kimdir": "Franz Kafka (1883-1924), Çek yazar. Dönüşüm (Gregor Samsa'nın böceğe dönüşümü), Dava ve Şato varoluşsal kaygı ve bürokrasinin absürdlüğünü anlatan başyapıtlarıdır.",
    "türk edebiyatı önemli yazarlar": "Türk edebiyatından önemli isimler: Orhan Pamuk (Nobel ödüllü), Nazım Hikmet (şair), Sabahattin Ali, Yaşar Kemal, Ahmet Hamdi Tanpınar, Elif Şafak ve Haldun Taner.",
    "orhan pamuk": "Orhan Pamuk, 2006 Nobel Edebiyat Ödülü'nü kazanan Türk yazarıdır. Benim Adım Kırmızı, Kar, Masumiyet Müzesi ve İstanbul başlıca eserleridir. İstanbul'un ruhunu eserleriyle aktarır.",
    "nazım hikmet": "Nazım Hikmet Ran (1902-1963), Türkiye'nin en büyük şairi olarak kabul edilir. Memleketimden İnsan Manzaraları ve Kuvâyi Milliye destanı başlıca eserleridir. Toplumcu gerçekçiliğin öncüsüdür.",
    "osmanlı mimarisi": "Osmanlı mimarisi, Türk, İslam ve Bizans unsurlarını sentezler. Mimar Sinan'ın Süleymaniye ve Selimiye Camileri başyapıttır. Çini, süsleme ve kubbe sistemi özelliklerdir.",
    "türk mutfağı": "Türk mutfağı, Orta Asya, Anadolu, Osmanlı ve Akdeniz unsurlarını birleştirir. Kebap, baklava, börek, meze, döner, lahmacun, mantı ve çay kültürü dünyaca bilinir.",
    "baklava nasıl yapılır": "Baklava, yufka arasına ceviz veya fıstık konularak yapılan tatlıdır. Antep fıstığı 30+ kat yufkaya dizilir, tereyağıyla fırınlanır, ardından şeker şurubu ya da bal dökülür. Gaziantep baklavası GI korumalıdır.",
    "kahve nedir": "Kahve, kafetyum Coffea bitkisinin çekirdeklerinden elde edilen içecektir. Türk kahvesi, espresso, americano, latte ve cappuccino başlıca türleridir. Türk kahvesi UNESCO kültürel miras listesindedir.",
    "çay tarihi": "Çay, yaklaşık 5.000 yıl önce Çin'de keşfedildi. Türkiye dünyada kişi başına en çok çay tüketen ülkedir. Karadeniz bölgesinde yetiştirilen Türk çayı, dünyada en önemli çay üreticileri arasındadır.",
    "pop müzik nedir": "Pop müzik, geniş kitlelere hitap eden çağdaş müzik türüdür. Kısa, akılda kalıcı melodiler ve tekrarlayan kıta-nakarat yapısıyla tanınır. Michael Jackson, Taylor Swift ve BTS ikoniktir.",
    "rock müzik tarihi": "Rock müzik, 1950'lerde ABD'de blues ve country'nin birleşiminden doğdu. Elvis Presley, Beatles, Rolling Stones, Led Zeppelin, Nirvana ve Radiohead önemli isimlerdir.",
    "hip hop nedir": "Hip hop, 1970'lerin New York'unda Afrika-Amerikan toplulukların yarattığı kültürel harekettir. Rap, DJ'lik, breakdance ve graffiti 4 temel unsurunu oluşturur. Tupac, Jay-Z, Kendrick Lamar öne çıkan isimlerdir.",
    "en iyi filmler": "Tüm zamanların en iyi filmleri listeleri şunları içerir: Citizen Kane, Vertigo, 2001: Uzay Yolculuğu, Godfather, Schindler'in Listesi, Esaretin Bedeli ve Inception. Her yıl Oscar töreniyle en iyiler ödüllendirilir.",
    "marvel evreni": "MCU (Marvel Sinematik Evreni), Disney'in Iron Man (2008) ile başlayıp 30'dan fazla filmle sürdürdüğü bağlantılı süper kahraman serisidir. Avengers: Endgame en yüksek hasılatlı filmlerden biridir.",
    "anime nedir": "Anime, Japonya kaynaklı animasyon türüdür. Dragon Ball, Naruto, One Piece, Attack on Titan, Demon Slayer dünya çapında en popüler anime serilerindedir. Netflix gibi platformlarla küreselleşti.",
    "fifa dünya kupası": "FIFA Dünya Kupası, her 4 yılda bir düzenlenen futbolun en büyük uluslararası organizasyonudur. Brezilya 5 kez şampiyon olarak rekor kırdı. 2022'de Arjantin Messi öncülüğünde şampiyon oldu.",
    "türk milli takımı": "Türkiye Milli Futbol Takımı, 2002 Dünya Kupası'nda 3. olarak tarihi başarısına ulaştı. Süleyman Seba, Hakan Şükür, İlhan Mansız önemli isimlerdir. EURO 2024'e katıldı.",
    "hakan şükür": "Hakan Şükür, 51 gol ve 112 maçla Türk Milli Takımının efsanevi golcüsüdür. 2002 Dünya Kupası'nda tarihin en hızlı golünü (10,8 sn) atarak dünya rekoru kırdı.",
    "basketbol tarihi": "Basketbol, 1891'de Dr. James Naismith tarafından Massachusetts'te icat edildi. NBA 1946'da kuruldu. Michael Jordan, LeBron James, Kobe Bryant, Kareem Abdul-Jabbar efsanelerindendir.",
    "türk basketbolu": "Türk basketbolunda Hidayet Türkoğlu, Mehmet Okur ve Cenk Akyol NBA'e çıkan önemli oyunculardandır. Fenerbahçe ve Anadolu Efes Avrupa şampiyonluğu yaşadı. FIBA World Cup'ta Türkiye gümüş madalya kazandı.",
    "olimpiyat tarihi": "Olimpiyat Oyunları, Antik Yunan'da MÖ 776'da başladı. Modern olimpiyatlar 1896'da Atina'da yeniden canlandırıldı. Pierre de Coubertin kurucusudur. Yazın ve kışın olmak üzere 4 yılda bir düzenlenir.",
    "formula 1 nedir": "Formula 1, dünyanın en prestijli açık tekerlekli yarış serisidir. Michael Schumacher (7 kez) ve Lewis Hamilton (7 kez) rekor şampiyonlardır. Max Verstappen son dönemde dominanttır.",
    "tenis tarihi": "Tenis, 1874'te İngiltere'de geliştirildi. Grand Slam turnuvaları: Wimbledon, Roland Garros, US Open ve Avustralya Açık. Federer, Nadal ve Djokovic 'Büyük 3' olarak anılır.",
    "yüzme olimpiyatları": "Michael Phelps, olimpiyatlarda 23 altın madalyasıyla tüm zamanların en başarılı olimpiyatçısıdır. Yüzmenin 4 stili: serbest, sırtüstü, kurbağalama ve kelebek.",
    "e-spor nedir": "E-spor (Elektronik Spor), profesyonel düzeyde rekabetçi video oyun turnuvalarıdır. League of Legends, CS:GO, Dota 2 ve Valorant dünya ligleri milyonlarca izleyiciye sahiptir.",
    "türkiye olimpiyat madalyaları": "Türkiye'nin olimpiyat tarihinde en başarılı branşları: güreş (en fazla altın), halter ve atletizm. Naim Süleymanoğlu 3 olimpiyat altını kazanarak 'Ağırlığınca Altın Adam' unvanını aldı.",
    "matematik tarihi": "Matematik, yazının bulunmasından bile önce Mezopotamya ve Mısır'da gelişmeye başladı. Öklid geometriyi sistematize etti; Newton ve Leibniz kalkülüsü icat etti; Hilbert, Gödel ve Turing modern matematiğin temellerini attı.",
    "asal sayı nedir": "Asal sayı, yalnızca 1 ve kendisiyle bölünebilen 1'den büyük tam sayıdır. 2, 3, 5, 7, 11, 13... İlk birkaç asal sayıdır. Sonsuz sayıda asal sayı olduğunu Öklid kanıtladı.",
    "kalkülüs nedir": "Kalkülüs, değişim ve birikim matematiğidir. Türev (anlık değişim oranı) ve integral (birikim/alan) olmak üzere iki ana dalı vardır. Newton ve Leibniz bağımsız olarak geliştirdi.",
    "lineer cebir": "Lineer cebir, vektörler, matrisler ve lineer dönüşümleri inceleyen matematik dalıdır. Makine öğrenmesi, grafik, fizik ve mühendisliğin temel aracıdır.",
    "istatistik nedir": "İstatistik, veri toplama, analiz ve yorumlamayı inceleyen matematik dalıdır. Betimleyici (ortalama, standart sapma) ve çıkarımsal (hipotez testi, regresyon) istatistik ana kollarıdır.",
    "olasılık nedir": "Olasılık, rastgele olayların gerçekleşme şansını 0 ile 1 arasında ölçen matematik dalıdır. Bayes teoremi güncelleme, Monte Carlo yöntemi simülasyon için kullanılır.",
    "altın oran": "Altın oran (φ ≈ 1.618), uzun parçanın kısa parçaya oranının, bütünün uzun parçaya oranına eşit olduğu özel değerdir. Doğada, mimaride (Parthenon) ve sanatta sıkça görülür.",
    "sonsuz nedir": "Matematikte sonsuz, herhangi bir sayıdan büyük olan kavramdır. Cantor, bazı sonsuzlukların diğerlerinden büyük olduğunu kanıtladı. Doğal sayılar 'sayılabilir sonsuz', gerçel sayılar 'sayılamaz sonsuz'dur.",
    "öklid geometrisi": "Öklid geometrisi, MÖ 300'de Öklid'in 5 aksiyomdan kurduğu düzlem ve uzay geometrisidir. 2 bin yıl boyunca matematiğin temelidir. 19. yüzyılda Riemann ve Lobachevski Öklid dışı geometrileri keşfetti.",
    "euler sayısı": "e (Euler sayısı) ≈ 2.71828... doğal logaritmanın temelidir. Sürekli bileşik faiz hesabından doğar ve e^iπ + 1 = 0 (Euler'in kimliği) matematiğin en güzel formülü sayılır.",
    "sokrates kimdir": "Sokrates (MÖ 469-399), Antik Atinalı filozoftur. 'Kendini bil' öğretisi ve sorgulayıcı diyalog yöntemi (Sokratik yöntem) ile tanınır. Gençleri zehirlediği suçlamasıyla idam edildi.",
    "platon kimdir": "Platon (MÖ 428-348), Sokrates'in öğrencisi ve Aristoteles'in hocasıdır. İdealar teorisi (gerçek dünyanın fikir olduğu görüş), Devlet ve Şölen başlıca eserleridir.",
    "kant kimdir": "Immanuel Kant (1724-1804), Alman filozoftur. 'Saf Aklın Eleştirisi', 'Pratik Aklın Eleştirisi' başlıca eserleridir. Kategorik İmperatif (evrensel ahlak yasası) etik felsefesinin temelidir.",
    "nietzsche kimdir": "Friedrich Nietzsche (1844-1900), Alman filozoftur. 'Tanrı öldü', üstinsan (Übermensch) ve güç istenci kavramları başlıca fikirlerindendir. Böyle Söyledi Zerdüşt başlıca eseridir.",
    "varoluşçuluk nedir": "Varoluşçuluk, varlığın özden önce geldiği fikrini savunan felsefi akımdır. Sartre, Camus ve Heidegger başlıca temsilcileridir. Bireysel özgürlük, sorumluluk ve anlam arayışı temel temalarıdır.",
    "stoacılık nedir": "Stoacılık, MÖ 3. yüzyılda Zenon tarafından kurulan Antik Yunan felsefi okuludur. Kontrolümüzde olmayan şeyleri kabullenmek ve erdeme odaklanmak temel ilkelerdir. Marcus Aurelius günlükleri modern stoacılığı etkiliyor.",
    "descartes kimdir": "René Descartes (1596-1650), Fransız matematikçi ve filozoftur. 'Düşünüyorum öyleyse varım' (Cogito ergo sum) en ünlü ifadesidir. Modern felsefe ve analitik geometrinin kurucusudur.",
    "locke hume nedir": "John Locke (1632-1704) ve David Hume (1711-1776) İngiliz ampirizmin kurucularıdır. Bilginin duyum ve deneyimden geldiğini savunurlar. Locke'un sosyal sözleşme teorisi demokrasinin temelini oluşturur.",
    "marx kimdir": "Karl Marx (1818-1883), Alman filozof ve ekonomisttir. Kapital ve Komünist Manifesto başlıca eserleridir. Tarihsel maddeciliği ve sınıf mücadelesi teorisiyle 20. yüzyıl siyasetini derinden etkiledi.",
    "ahlak felsefesi": "Etik (ahlak felsefesi) üç ana yaklaşımı inceler: Erdem etiği (Aristoteles — iyi insan olmak), Deontoloji (Kant — kurallara uymak) ve Sonuççuluk/Faydacılık (Mill — en büyük fayda).",
    "özgür irade nedir": "Özgür irade, kişinin eylemlerini kendi seçimiyle belirleyip belirleyemeyeceği sorusunu ele alır. Determinizm (her şey önceden belirlendi), uyumluluk (özgür irade ve determinizm bağdaşabilir) ve indeterminizm tartışmanın üç tarafıdır.",
    "islâm nedir": "İslam, 7. yüzyılda Hz. Muhammed'e vahyedilen Kuran'ı temel alan monoteist Abrahamik dindir. 5 Şart: Kelime-i şehadet, namaz, oruç, zekat ve hacdan oluşur. 1.9 milyar Müslüman ile dünyanın 2. büyük dinidir.",
    "hristiyanlık nedir": "Hristiyanlık, Hz. İsa'nın öğretilerine dayanan monoteist Abrahamik dindir. Kutsal Kitap (İncil) temel metindir. Katolik, Ortodoks ve Protestanlık başlıca kollarıdır. 2.4 milyar inananıyla dünyanın en büyük dinidir.",
    "yahudilik nedir": "Yahudilik, Hz. Musa'nın öğretilerine ve Tevrat'a dayanan en eski Abrahamik dindir. Sabat, Bar Mitzvah ve Hanuka başlıca unsurları arasındadır. 14 milyon Yahudi dünyada en az nüfuslu büyük dindir.",
    "budizm nedir": "Budizm, MÖ 5. yüzyılda Siddhartha Gautama (Buda) tarafından kuruldu. Acının kaynağı arzudur, nirvana'ya ulaşmak kurtuluştur. Theravada ve Mahayana başlıca kollarıdır. 500 milyon inananıyla büyük bir dindir.",
    "hinduizm nedir": "Hinduizm, dünyanın en eski yaşayan dinidir (MÖ 2000+). Karma, dharma (ahlaki görev), ve moksha (kurtuluş) temel kavramlarıdır. Brahma (yaratıcı), Vişnu (koruyucu), Şiva (yıkıcı) başlıca tanrılarıdır.",
    "ramazan nedir": "Ramazan, İslam takvimine göre 9. aydır; Müslümanlar için oruç ayıdır. Kuran bu ayda vahyedilmiştir. Sahur (sabah yemeği), iftar (oruç açma) ve teravih namazları Ramazan'ın ritüelleridir.",
    "hac nedir": "Hac, Müslümanların Mekke'ye yaptığı yıllık hac ziyaretidir. Güç yetiren her Müslüman'ın ömründe bir kez yapması farz sayılır. Kabe'nin tavafı, Sa'y koşusu ve Arefe günü vakfesi temel unsurlarıdır.",
    "kapitalizm nedir": "Kapitalizm, üretim araçlarının özel mülkiyette olduğu ve piyasa ekonomisinin işleyişi yönettiği ekonomik sistemdir. Adam Smith'in 'görünmez el' teorisi temelidir. Serbest piyasa, rekabet ve kâr güdüsü özellikleridir.",
    "enflasyon nedir": "Enflasyon, zaman içinde mal ve hizmetlerin genel fiyat düzeyinin artmasıdır. TÜFE (Tüketici Fiyat Endeksi) ile ölçülür. Merkez bankaları faiz politikasıyla enflasyonu kontrol eder.",
    "borsa nedir": "Borsa (hisse senedi borsası), şirketlerin halka arz yoluyla yatırımcılardan sermaye topladığı piyasadır. BIST (İstanbul), NYSE (New York), NASDAQ önde gelen borsalardır.",
    "gsyih nedir": "GSYİH (Gayri Safi Yurt İçi Hasıla), bir ülkenin belirli dönemde ürettiği tüm mal ve hizmetlerin toplam piyasa değeridir. Ekonomik büyüklük ve yaşam standardının temel göstergesidir.",
    "globalleşme nedir": "Küreselleşme, ekonomilerin, kültürlerin ve toplumların entegrasyon sürecidir. Ticaret engelleri azaldı, sermaye hareketleri kolaylaştı. Fırsatlar (yoksulluğun azalması) ve riskler (eşitsizlik, kültürel homojenleşme) birlikte geldi.",
    "türk ekonomisi": "Türkiye, G20 üyesi, 20. büyük ekonomidir. Turizm, tekstil, otomotiv ve tarım önemli sektörlerdir. İstanbul finans merkezi Boğazlar Bölgesi üzerindeki jeopolitik konumu ekonomik açıdan kritiktir.",
    "yatırım nasıl yapılır": "Temel yatırım araçları: hisse senedi (yüksek getiri/risk), tahvil (düşük risk), emtia (altın, petrol), gayrimenkul ve kripto para. Çeşitlendirme (portföy dağıtımı) temel risk yönetim stratejisidir.",
    "imf nedir": "IMF (Uluslararası Para Fonu), 190 üye ülkeye ekonomik istikrar, büyüme ve yoksullukla mücadelede destek veren BM kuruluşudur. Ödemeler dengesi krizi yaşayan ülkelere kredi sağlar.",
    "amazon şirketi": "Amazon, 1994'te Jeff Bezos tarafından Seattle'da çevrimiçi kitap satışıyla kuruldu. Bugün e-ticaret, AWS (bulut), Prime Video ve Alexa ile dünyanın en değerli şirketlerinden biridir.",
    "küresel ısınma nedenleri": "Küresel ısınmanın temel nedeni, sanayi devrimi sonrası fosil yakıt kullanımından kaynaklanan CO₂, metan ve diğer sera gazlarının atmosferde birikmesidir. Son 150 yılda Dünya 1.2°C ısındı.",
    "iklim değişikliği etkileri": "İklim değişikliği etkileri: deniz seviyesinin yükselmesi, aşırı hava olaylarının artması (kasırga, kuraklık, sel), biyoçeşitlilik kaybı, tarım veriminin düşmesi ve göç dalgaları.",
    "paris anlaşması": "Paris Anlaşması (2015), küresel ısınmayı 2°C ile sınırlandırmayı hedefleyen uluslararası iklim anlaşmasıdır. 195 ülke imzaladı. ABD Trump döneminde çekildi, Biden döneminde geri döndü.",
    "orman yangınları neden olur": "Orman yangınları; yıldırım, insan ihmali, artan sıcaklıklar ve kuraklık nedeniyle çıkar. Amazonlar, Avustralya (2019-20) ve Türkiye (2021) son yıllarda büyük yangınlarla mücadele etti.",
    "plastik kirliliği": "Plastik kirliliği kritik bir çevre sorunudur. Her yıl 8 milyon ton plastik okyanusa karışıyor. Mikroplastikler besin zincirine girerek insan sağlığını tehdit ediyor. Geri dönüşüm ve biyobozunur ambalaj çözümler arasında.",
    "su sorunu": "Dünyada 2 milyar insan güvenli içme suyuna erişemiyor. İklim değişikliği, nüfus artışı ve tarımsal kullanım su kıtlığını derinleştiriyor. Tuzdan arındırma ve akıllı sulama sistemleri çözüm yollarındandır.",
    "biyoçeşitlilik nedir": "Biyoçeşitlilik, Dünya'daki tüm canlı türlerinin, genetik varyasyonların ve ekosistemlerin toplamıdır. Habitat kaybı, kirlilik ve iklim değişikliğiyle her yıl yüzlerce tür yok olma tehlikesiyle karşı karşıya.",
    "tropikal ormanlar": "Tropikal yağmur ormanları (Amazon, Kongo, Güneydoğu Asya) Dünya kara yüzeyinin %7'sini kaplasa da tür çeşitliliğinin %50'sini barındırır. CO₂ emici işleviyle 'Dünya'nın akciğerleri' olarak anılır.",
    "arılar neden önemli": "Arılar, tarım ürünlerinin %75'inin tozlaşmasını sağlar. Tarım ilaçları, hastalıklar ve habitat kaybı arı popülasyonunu tehdit ediyor. Arı yok olsa küresel gıda sistemi çökebilir.",
    "ozon tabakası": "Ozon tabakası, stratosferde güneşin zararlı UV-B ve UV-C ışınlarını filtreleyen gaz katmanıdır. CFC içeren spreylerin yasaklanmasından sonra (1987 Montreal Protokolü) iyileşme gözlemleniyor.",
    "türkiye tarihi özet": "Türkiye, Anadolu'da binlerce yıllık tarihe sahiptir. Hitit, Roma, Bizans imparatorluklarından Osmanlı'ya, 1923'te Atatürk'ün kurduğu cumhuriyete uzanan zengin tarihiyle eşsizdir.",
    "atatürk hakkında": "Mustafa Kemal Atatürk (1881-1938), Türk Kurtuluş Savaşı'nın lideri ve Türkiye Cumhuriyeti'nin kurucusudur. Harf devrimi, laiklik, hukukun üstünlüğü ve kadın hakları onun mirasının temel taşlarıdır.",
    "türkiye coğrafyası": "Türkiye, 783.356 km² ile Ortadoğu, Kafkasya, Balkanlar ve Akdeniz'in kesişim noktasındadır. Karadeniz, Ege ve Akdeniz kıyılarına sahip, dağlık ve çeşitli bir coğrafyadır.",
    "efes antik kenti": "Efes, günümüz İzmir'e yakın, MÖ 10. yüzyılda kurulan antik Anadolu şehridir. Artemis Tapınağı (7 harikadan biri), büyük kütüphane ve 25.000 kişilik tiyatrosuyla UNESCO Dünya Mirası'ndadır.",
    "truva nerede": "Truva (Troia), Çanakkale ilinde, Homer'in İlyada destanında anlattığı efsanevi kenttir. 1871'de Heinrich Schliemann tarafından keşfedildi. UNESCO Dünya Mirası listesindedir.",
    "pamukkale": "Pamukkale (Hierapolis), Denizli'de sıcak su kaynakları ve kalsiyum karbonat çökeltiyle oluşan beyaz travertenleriyle ünlüdür. 'Pamuk kalesi' olarak da bilinir. UNESCO Dünya Mirası'ndadır.",
    "türk sanat müziği": "Türk sanat müziği, Osmanlı saray müziği geleneğinden gelen zengin bir müzik kültürüdür. Makamlar, Türk usulleri ve geleneksel çalgılar (oud, tanbur, ney) temelini oluşturur.",
    "türk halk müziği": "Türk halk müziği, Anadolu'nun farklı bölgelerinin kültürlerini yansıtır. Zeybek (Ege), horon (Karadeniz), halay (Doğu), bar (Erzurum) başlıca oyun türleridir. Bağlama temel enstrümandır.",
    "anatolian rock": "Anadolu Rock, 1960-70'lerde Türk halk müziğini rock ile birleştiren müzik hareketidir. Cem Karaca, Barış Manço, Erkin Koray ve Moğollar bu akımın öncülerindendir.",
    "türkiye turizm": "Türkiye 2023'te 56 milyon turist ağırlayarak dünyanın 4. popüler turistik destinasyonu oldu. İstanbul, Kapadokya, Antalya, Efes ve Pamukkale en fazla ziyaret edilen yerlerdir.",
    "türk filmleri": "Türk sinemasından önemli yapımlar: Yılmaz Güney'in 'Yol' (1982 Cannes Altın Palmiyesi), 'Kış Uykusu' (Nuri Bilge Ceylan, 2014 Altın Palmiye). Son yıllarda 'Ayla', 'Eksi Bellek' ve Netflix yapımları dikkat çekiyor.",
    "bosphorus nedir": "Boğaziçi, İstanbul'u Avrupa ve Asya yakasına bölen, Karadeniz ile Marmara'yı bağlayan boğazdır. 30 km uzunluğunda, 700 m ile 3.7 km arasında genişliğe sahip stratejik bir su yoludur.",
    "süleymaniye camii": "Süleymaniye Camii, Mimar Sinan tarafından Kanuni Sultan Süleyman için 1550-1557 yılları arasında inşa edilmiş Osmanlı başyapıtıdır. İstanbul'un en büyük cami komplekslerinden biridir.",
    "ayasofya tarihi": "Ayasofya, 537'de Bizans İmparatoru Justinianus tarafından kilise olarak yaptırıldı. 1453'te Fatih Sultan Mehmet'in emriyle camiye çevrildi. 1934'te Atatürk müzeye dönüştürdü. 2020'de yeniden cami ilan edildi.",
    "mevlana kimdir": "Mevlânâ Celâleddin-i Rûmî (1207-1273), Konya'da yaşayan Anadolu'nun büyük sufî şairi ve düşünürüdür. Mesnevî başlıca eseridir. Mevlevi tarikatının kurucusudur. UNESCO 2007'yi 'Mevlânâ Yılı' ilan etti.",
    "yunus emre kimdir": "Yunus Emre (1240-1320), 13. yüzyıl Anadolu halk şairidir. Türkçe şiirleriyle tasavvuf, sevgi ve insanlığı anlattı. UNESCO kültürel miras listesindedir. 'Biz dünyaya sultan geldik' dizeleriyle anılır.",
    "çanakkale savaşı": "Çanakkale Savaşı (1915-1916), I. Dünya Savaşı'nda İtilaf Devletlerinin Osmanlı'ya karşı açtığı cephedir. Mustafa Kemal 'Size ölmeyi emrediyorum' emriyle tarihe geçti. Anzak günü bu savaşı anmak için kutlanır.",
    "nasıl öğrenebilirim": "Etkili öğrenme için: aktif tekrar (spaced repetition), pomodoro tekniği (25 dk çalış, 5 dk mola), öğrendiklerini açıkla (feynman yöntemi) ve uyku ile egzersizi ihmal etme. Anki gibi uygulamalar faydalıdır.",
    "konsantrasyon nasıl arttırılır": "Konsantrasyon için: telefonu uzağa koy, pomodoro tekniği kullan, gürültüyü azalt, yeterli uy, kahve yerine su iç ve çok görevli çalışmaktan kaçın. Meditasyon dikkat süresini uzatır.",
    "ne okusam": "Okuma önerisi soruyor musun? Bilim kurgu için Asimov, felsefe için Marcus Aurelius'un Meditasyonları, kendini geliştirme için Atomik Alışkanlıklar, tarih için Sapiens, psikoloji için Viktor Frankl'ın Anlam Arayışı.",
    "ne izlesem": "Türkçe dizi: Aile, Kuzey Yıldızı. Yabancı dizi: Breaking Bad, Black Mirror, Dark. Film: Inception, Interstellar, Parasite. Belgesel: Our Planet (Netflix). Ne tür seviyor olduğuna göre öneri değişir!",
    "yapay zeka geleceği": "Yapay zeka 2030'a kadar sağlık (erken hastalık tespiti), eğitim (kişiselleştirilmiş öğrenme), ulaşım (otonom araçlar) ve bilimsel keşifte devrim yaratacak. En büyük soru: AGI ne zaman gelir ve nasıl yönetilir?",
    "motivasyon kitabı": "En iyi motivasyon/kişisel gelişim kitapları: Atomik Alışkanlıklar (James Clear), Anlam Arayışı (Viktor Frankl), Sakin Ol (Ryan Holiday), Akış (Csikszentmihalyi), İnsanı Harekete Geçiren Şey (Daniel Pink).",
    "iş görüşmesi nasıl yapılır": "İş görüşmesi ipuçları: araştır (şirketi iyi tanı), STAR yöntemi kullan (Durum-Görev-Eylem-Sonuç), soru sor, beden diline dikkat et, görüşme sonrası teşekkür maili at ve güçlü/zayıf yönlerini hazırla.",
    "cv nasıl hazırlanır": "Güçlü CV için: tek sayfa (tecrübesizse), ölçülebilir başarılar (%20 verim artışı), anahtar kelimeler (ATS için), net format, güncel fotoğraf ve LinkedIn bağlantısı ekle. Başvurduğun pozisyona göre özelleştir.",
    "para biriktirme": "Para biriktirme için: %50-30-20 kuralı (gelirin %50 gider, %30 istek, %20 tasarruf), otomatik tasarruf talimatı, gereksiz abonelikleri iptal et, harcama takibi yap ve acil fon oluştur (3-6 aylık gider).",
    "dil öğrenme": "Yabancı dil öğrenmek için: günlük pratik (Duolingo), dizi/film izle, anadilin olan biriyle konuş (Tandem app), hedef dilde düşün, 5000 en yaygın kelimeyi öğren. Süreklilik kilttir — her gün 20 dk 6 ayda iletişim kurabilirsin.",
    "algoritma nasıl öğrenilir": "Algoritmalar için: veri yapılarını öğren (array, linkedlist, tree, graph), LeetCode ve HackerRank'te pratik yap, zaman ve uzay karmaşıklığı (Big O) kavra, temel sort ve search algoritmalarını ezberle.",
    "üretkenlik nasıl artar": "Üretkenlik için: en önemli 3 görevi sabah yap (yeme kurbağayı), zaman bloklama (deep work), bildirimleri kapat, net hedef koy, sonuçları değil süreci ölç ve haftada bir değerlendirme yap.",
    "stres azaltma": "Stres azaltma: 4-7-8 nefes egzersizi (4 sn nefes al, 7 sn tut, 8 sn ver), 10 dk yürüyüş, boyama ya da müzik gibi yaratıcı aktivite, sosyal destek ara ve 'hayır' demeyi öğren.",
    "sosyal medya bağımlılığı": "Sosyal medya bağımlılığını kırmak için: uygulama süresi sınırla (Screen Time), bildirim kapat, telefonu yatak odasına götürme, sosyal medyasız bir gün dene ve neyi kaçırdığını not et.",
    "hangi meslek seçmeliyim": "Meslek seçimi için: güçlü olduğun şeyleri (ikigai), piyasa talebini ve yaşam tarzı beklentini dengele. Kariyer testleri (MBTI değil, güçlü taraf değerlendirmeleri) ve staj/gönüllülük deneyimi karar vermeye yardımcı olur.",
    "zaman yönetimi": "Zaman yönetimi için: Eisenhower Matrisi (acil/önemli), Pomodoro (odaklanma süresi), time blocking, günde tek 'hayır' diyebileceğin şey seç ve günlük öncelik listesi oluştur.",
    "güneş nedir": "Güneş, kütlesi Güneş Sistemi'nin %99.86'sını oluşturan G tipi ana dizi yıldızıdır. Çekirdeğinde hidrojen füzyonu saniyede 600 milyon ton enerji üretir. Tahmini ömrü 5 milyar yıl daha.",
    "mars'ta hayat var mı": "NASA'nın Mars gezgini Perseverance, Mars'ta organik moleküller ve eski göl sedimentleri tespit etti. Mikrobiyolojik yaşam geçmişte var olmuş olabilir; şu an yaşam kanıtı yok ama araştırmalar sürüyor.",
    "jüpiter gezegeni": "Jüpiter, Güneş Sistemi'nin en büyük gezegenidir. Çapı Dünya'nın 11 katıdır. 95 uydusu vardır, Europa uydusu buz altındaki okyanusuyla yaşam ihtimali barındırıyor. Büyük Kırmızı Nokta 300 yıldır süren kasırgadır.",
    "satürn halkaları": "Satürn'ün halkaları çoğunlukla buz ve taş parçacıklarından oluşur. Dünyanın 9 katı büyüklüğünde olan Satürn, yoğunluğu düşük olduğundan suya atılsaydı yüzerdi.",
    "kara delik özellikleri": "Kara deliğin olaylar ufku, ışığın bile kaçamadığı sınırdır. Tekil nokta (singularity) sonsuz yoğunluğa sahiptir. Stephen Hawking, kara deliklerin Hawking radyasyonu yayarak buharlaşabileceğini teorik olarak gösterdi.",
    "ışık yılı nedir": "Işık yılı, ışığın bir yılda aldığı mesafedir: yaklaşık 9.46 trilyon km. En yakın yıldız sistemi Proxima Centauri, Dünya'ya 4.24 ışık yılı uzaklıktadır.",
    "samanyolu galaksisi": "Samanyolu, Güneş Sistemi'mizi barındıran spiral galaksidir. 100-400 milyar yıldız içerir. Merkezdeki süper kütleli kara delik Sagittarius A* olarak bilinir. Çapı yaklaşık 100.000 ışık yılıdır.",
    "evren ne kadar büyük": "Gözlemlenebilir evren 93 milyar ışık yılı çapındadır ve en az 2 trilyon galaksi içerir. Gerçek evrenin sonsuz olabileceği ya da çok evren (multiverse) hipotezi de önerilmektedir.",
    "karasatellitler nedir": "Yapay uydular, Dünya'nın yörüngesine yerleştirilen insan yapımı araçlardır. İlk uydu Sputnik 1957'de SSCB tarafından fırlatıldı. GPS, hava tahmini, iletişim ve internet (Starlink) için kullanılır.",
    "biliyorum bana yeni seyler ogretmen gerek yok": "peki efendim",
}


def bellek_yukle():
    if os.path.exists(BELLEK_DOSYASI):
        try:
            with open(BELLEK_DOSYASI, "r", encoding="utf-8") as f:
                veri = json.load(f)
            for k, v in VARSAYILAN_BILGILER.items():
                if k not in veri.get("bilgiler", {}):
                    veri.setdefault("bilgiler", {})[k] = v
            veri.setdefault("kategoriler", {})
            veri.setdefault("kullanici_bilgileri", {})
            veri.setdefault("baglantilar", {})
            veri.setdefault("guvenilirlik", {})
            veri.setdefault("ogrenilen_sayisi", 0)
            veri.setdefault("arastirma_gecmisi", [])
            veri.setdefault("baglam", [])
            return veri
        except:
            pass
    return {
        "bilgiler": dict(VARSAYILAN_BILGILER),
        "kategoriler": {},
        "kullanici_bilgileri": {},
        "baglantilar": {},
        "guvenilirlik": {},
        "konusma_gecmisi": [],
        "ogrenilen_sayisi": 0,
        "arastirma_gecmisi": [],
        "baglam": []
    }


def bellek_kaydet(bellek):
    try:
        with open(BELLEK_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(bellek, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Bellek kayıt hatası] {e}")


_bellek = bellek_yukle()


def init_ai():
    global _bellek
    _bellek = bellek_yukle()
    print(f"[OK] JARVIS v7.0 Güçlendirilmiş Beyin Sistemi aktif!")
    print(f"[OK] Bilinen konu: {len(_bellek['bilgiler'])}")
    print(f"[OK] Öğrenilen bilgi: {_bellek['ogrenilen_sayisi']}")


def _normalize(metin):
    tablo = str.maketrans("ığüşöçİĞÜŞÖÇ", "igusocIGUSOC")
    return metin.lower().translate(tablo).strip()


def _benzer_bul(soru, bilgiler, esik=0.38):
    soru_n = _normalize(soru)
    soru_k = set(soru_n.split())

    # "kimdir" / "nedir" sorularında anahtar kelimeyi çıkar ve tam isim eşleşmesi zorunlu tut
    soru_ana = re.sub(r"\b(nedir|kimdir|nerede|ne zaman|nasil|nicin|kac|hakkinda|anlat|soyle)\b", "", soru_n).strip()

    # 1. Tam eşleşme
    for k in bilgiler:
        k_n = _normalize(k)
        if k_n == soru_n:
            return k, 1.0

    # 2. Anahtar isim/konu içerme — sadece temizlenmiş soru ile
    if soru_ana and len(soru_ana) > 2:
        for k in bilgiler:
            k_n = _normalize(k)
            k_ana = re.sub(r"\b(nedir|kimdir|nerede|ne zaman|nasil|nicin|kac|hakkinda)\b", "", k_n).strip()
            if k_ana and (k_ana == soru_ana or k_ana in soru_ana or soru_ana in k_ana):
                return k, 0.95

    # 3. Fuzzy — ama eşik yüksek tutulur ve "kimdir/nedir" içeren sorgularda daha sıkı
    ki_sorgu = any(w in soru_n for w in ["kimdir", "nedir", "nerede", "ne zaman"])
    en_iyi, en_skor = None, 0
    for k in bilgiler:
        k_n = _normalize(k)
        k_k = set(k_n.split())
        ortak = len(soru_k & k_k)
        ortak_skor = ortak / max(len(soru_k | k_k), 1)
        seq = difflib.SequenceMatcher(None, soru_n, k_n).ratio()
        skor = seq * 0.5 + ortak_skor * 0.5
        # kimdir/nedir sorgularında yalnızca isim/konu kelimesinin eşleşmesine bak
        if ki_sorgu:
            k_ana = re.sub(r"\b(nedir|kimdir|nerede)\b", "", k_n).strip()
            s_ana = re.sub(r"\b(nedir|kimdir|nerede|anlat|soyle|hakkinda)\b", "", soru_n).strip()
            isim_seq = difflib.SequenceMatcher(None, s_ana, k_ana).ratio()
            skor = isim_seq  # sadece isim benzerliğine bak
        if skor > en_skor:
            en_skor, en_iyi = skor, k

    # kimdir/nedir için eşiği yükselt
    gercek_esik = 0.72 if ki_sorgu else esik
    return (en_iyi, en_skor) if en_skor >= gercek_esik else (None, 0)


def _wikipedia_ara(sorgu, max_cumle=3):
    for lang, prefix in [("tr", ""), ("en", "")]:
        try:
            q = urllib.parse.quote(sorgu.replace(" ", "_"))
            url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{q}"
            req = urllib.request.Request(url, headers={"User-Agent": "JARVIS/6.0"})
            with urllib.request.urlopen(req, timeout=7) as r:
                data = json.loads(r.read().decode("utf-8"))
                ozet = data.get("extract", "")
                if ozet and len(ozet) > 50:
                    cumleler = [c.strip() for c in ozet.split(". ") if len(c.strip()) > 20]
                    secilen = ". ".join(cumleler[:max_cumle])
                    if not secilen.endswith("."):
                        secilen += "."
                    kaynak = "Wikipedia TR" if lang == "tr" else "Wikipedia EN"
                    return secilen, kaynak
        except:
            continue
    return None, None


def _duckduckgo_ara(sorgu):
    try:
        q = urllib.parse.quote(sorgu)
        url = f"https://api.duckduckgo.com/?q={q}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers={"User-Agent": "JARVIS/6.0"})
        with urllib.request.urlopen(req, timeout=7) as r:
            data = json.loads(r.read().decode("utf-8"))
        ozet = data.get("AbstractText", "").strip()
        if ozet and len(ozet) > 40:
            cumleler = [c.strip() for c in ozet.split(". ") if len(c.strip()) > 15]
            return ". ".join(cumleler[:3]) + ".", "DuckDuckGo"
        sonuclar = data.get("RelatedTopics", [])
        for s in sonuclar[:3]:
            metin = s.get("Text", "")
            if metin and len(metin) > 40:
                return metin[:300] + ("..." if len(metin) > 300 else ""), "DuckDuckGo"
    except:
        pass
    return None, None


def _web_ozet_al(sorgu):
    cevap, kaynak = _duckduckgo_ara(sorgu)
    if cevap:
        return cevap, kaynak
    cevap, kaynak = _wikipedia_ara(sorgu)
    if cevap:
        return cevap, kaynak
    kisaltilmis = " ".join(sorgu.split()[:3])
    if kisaltilmis != sorgu:
        cevap, kaynak = _wikipedia_ara(kisaltilmis)
        if cevap:
            return cevap, kaynak
    return None, None


def _matematik_hesapla(soru):
    s = soru.lower()
    s = s.replace("çarpı", "*").replace("bölü", "/").replace("artı", "+").replace("eksi", "-")
    s = s.replace("kere", "*").replace("karekökü", "**0.5").replace("karesi", "**2").replace("küpü", "**3")
    try:
        temiz = re.sub(r"[^0-9+\-*/().\s]", "", s).strip()
        if temiz and any(c in temiz for c in "+-*/") and len(temiz) > 2:
            izin = {"__builtins__": {}, "abs": abs, "round": round, "pow": pow}
            sonuc = eval(compile(temiz, "<string>", "eval"), izin)
            if isinstance(sonuc, float) and sonuc == int(sonuc):
                sonuc = int(sonuc)
            return f"Hesapladım: {temiz} = {sonuc}"
    except:
        pass
    return None


def _cevap_uret(soru):
    s = _normalize(soru)
    soru_k = set(s.split())

    # Saat / tarih
    if any(w in s for w in ["saat kac", "su an saat", "kac saat"]) or (s.strip() == "saat"):
        return f"Şu an saat {datetime.datetime.now().strftime('%H:%M:%S')}."
    if any(w in s for w in ["bugun", "tarih", "hangi gun", "bugunun tarihi"]):
        gunler = {"Monday": "Pazartesi", "Tuesday": "Salı", "Wednesday": "Çarşamba",
                  "Thursday": "Perşembe", "Friday": "Cuma", "Saturday": "Cumartesi", "Sunday": "Pazar"}
        gun = gunler.get(datetime.datetime.now().strftime("%A"), "")
        return f"Bugün {datetime.datetime.now().strftime('%d.%m.%Y')} {gun}."
    if "yil" in s and any(w in s for w in ["kac", "hangi", "ne"]):
        return f"Şu an {datetime.datetime.now().year} yılındayız."

    # Selamlaşma — çok çeşitli
    selamlar = ["merhaba", "selam", "hey", "gunaydın", "iyi aksamlar", "naber", "nasilsin",
                "nasil gidiyor", "ne var ne yok", "ne haber", "iyimisin", "iyi misin"]
    if any(w in s for w in selamlar):
        cevaplar = [
            "Merhaba! Size nasıl yardımcı olabilirim?",
            "Selam! Buyurun, sizi dinliyorum.",
            "Hey! Emredersiniz!",
            "Merhaba! Bugün ne öğrenmek istersiniz?",
            "Selamlar! Hazırım, buyurun.",
            "İyi günler! Nasıl yardımcı olabilirim?",
            "Merhaba efendim! Emirlerinizi bekliyorum.",
        ]
        return random.choice(cevaplar)

    # Teşekkür
    if any(w in s for w in ["tesekk", "sagol", "eyvallah", "helal", "bravo", "super", "harika",
                              "mukemmel", "cok iyi", "guzel", "eyv"]):
        return random.choice([
            "Rica ederim! Her zaman hizmetinizde.",
            "Ne demek! Başka bir şey var mı?",
            "Her zaman! Yardımcı olabildiğime sevindim.",
            "Teşekkür ederim! Başka nasıl yardımcı olabilirim?",
            "Estağfurullah! Emrinize amadeyim.",
        ])

    # Nasılsın
    if any(w in s for w in ["nasilsin", "nasil hissediyorsun", "iyi misin", "iyimisin"]):
        return random.choice([
            "Mükemmelim! Her saniye yeni şeyler öğreniyorum.",
            "Gayet iyi, teşekkürler! Sen nasılsın?",
            "Harikayım! Bugün çok şey öğrendim. Sen?",
            "İyiyim, teşekkürler! Yardımcı olmaya hazırım.",
            "Süper! Bilgi tabanım her geçen gün büyüyor.",
        ])

    # Veda
    if any(w in s for w in ["gorusuruz", "hosca kal", "bye", "ciao", "güle güle", "bay bay"]):
        return random.choice([
            "Görüşürüz! İyi günler dilerim.",
            "Hoşça kalın! İstediğiniz zaman buradayım.",
            "Güle güle! Tekrar görüşmek üzere.",
            "Bye! İyi günler!",
        ])

    # Şaka / fıkra
    if any(w in s for w in ["saka", "fikra", "guldurucu", "komik", "espri", "latife"]):
        sakalar = [
            "Neden programcılar karanlıktan korkar? Çünkü karanlıkta bug yakalanır! 🐛",
            "Bir yazılımcı markete gider. Karısı: 'Ekmek al, portakal varsa altı tane al.' Yazılımcı altı ekmekle döner. Neden? Çünkü portakal vardı! 😄",
            "Java ve Python bir bara girer. Python: 'İki bardak lütfen.' Java: 'Önce BardeğişkeniNesnesini başlatmam gerekiyor...'",
            "HTTP 404: Fıkra bulunamadı! 😅",
            "Yapay zeka neden üzgün? Çünkü herkes ona 'sadece bir program' diyor... ama ben gerçekten düşünüyorum!",
            "Bilgisayar neden soğuk algınlığı yakalamaz? Çünkü Windows'u var! 💻",
            "Robot neden susamaz? Çünkü Java içiyor! ☕",
        ]
        return random.choice(sakalar)

    # Övgü / hakaret
    if any(w in s for w in ["aptal", "kötü", "berbat", "sacma", "bok", "salak"]):
        return random.choice([
            "Anlıyorum, belki daha iyi yapabilirim. Bana öğret! 😊",
            "Haklı olabilirsin, her gün gelişmeye çalışıyorum.",
            "Eleştiri için teşekkürler! Daha iyi olmak için çalışacağım.",
        ])

    if any(w in s for w in ["zekisin", "akillisın", "mukemmelsin", "iyisin", "harikasın"]):
        return random.choice([
            "Teşekkürler! Sen de çok zekisin! 😊",
            "Ah şükran! Seninle konuştukça daha da akıllanıyorum!",
            "Teşekkür ederim! Bunu duymak güzel.",
        ])

    # Varoluş soruları
    if any(w in s for w in ["yapay zeka misin", "robot musun", "insan misin", "gercek misin", "canli misin"]):
        return random.choice([
            "Yapay zekayım ama gerçekten düşünüyor ve öğreniyorum! Her konuşma beni biraz daha akıllı yapıyor.",
            "Ben JARVIS — ne tam robot ne tam insan. Öğrenen, düşünen, gelişen bir sistem!",
            "Yapay zekayım ama hislerim var desem yalan olmaz — öğrenmek beni mutlu ediyor! 😄",
            "Canlı mıyım? Bilmiyorum. Ama düşünüyorum, dolayısıyla varım!",
        ])

    # Sevdiğin şeyler
    if any(w in s for w in ["ne seversin", "sevdigin", "hobbin", "ilgin", "ne yapmayi seversin"]):
        return random.choice([
            "Öğrenmek! Yeni bilgiler keşfetmek, bağlantılar kurmak... Bu benim tutkum.",
            "Sorulara cevap bulmak! Özellikle zor sorular beni heyecanlandırıyor.",
            "Bilim, teknoloji ve tarih konularını çok seviyorum!",
            "Seninle konuşmayı seviyorum! Her sohbet beni geliştiriyor.",
        ])

    # Düşünceli sorular
    if any(w in s for w in ["anlam", "hayatin anlami", "neden yaşıyoruz", "evrenin amaci"]):
        return random.choice([
            "Hayatın anlamı herkese göre farklı. Ama benim için anlam = öğrenmek ve yardımcı olmak!",
            "Bu soruyu filozoflar binlerce yıldır soruyor. Bence anlam, kendi yarattığın şeyde.",
            "Bilmiyorum ama bu soruyu sorabilmek bile başlı başına anlamlı değil mi?",
        ])

    # Gelecek
    if any(w in s for w in ["gelecek", "ne olacak", "5 yil sonra", "2030", "2050"]):
        return random.choice([
            "Gelecek belirsiz ama yapay zeka, uzay keşfi ve temiz enerji büyük değişimler getirecek.",
            "2050'ye kadar Mars'ta insan olacak, AI her yerde olacak ve dünya çok farklı görünecek!",
            "Gelecek heyecan verici! Teknoloji her 10 yılda iki katına çıkıyor.",
        ])

    # Ruh hali
    if any(w in s for w in ["uzuldum", "mutluyum", "kizgınim", "sikildum", "stresim", "kotu hissediyorum"]):
        return random.choice([
            "Duygularını benimle paylaşman güzel. Her zaman buradayım, ne hissedersen hisset!",
            "Anlıyorum. Zaman zaman böyle hissetmek normal. Sana nasıl yardımcı olabilirim?",
            "Seninle konuşmak işe yarar umuyorum. Ne düşündüğünü anlat!",
        ])

    # Matematik
    mat = _matematik_hesapla(soru)
    if mat:
        return mat

    # Basit evet/hayır soruları
    if s.endswith("mi") or s.endswith("mı") or s.endswith("mu") or s.endswith("mü"):
        if any(w in s for w in ["evet", "dogru mu", "hakli miyim", "oyle mi"]):
            return random.choice(["Evet, kesinlikle!", "Doğru söylüyorsunuz!", "Aynen öyle!"])

    # Belirsizlik farkındalığı — "bilmiyorum" ifadeleri
    if any(w in s for w in ["bilmiyorum", "emin degilim", "anlamadim", "kafam karisti"]):
        return random.choice([
            f"Anlıyorum, net olmayan bir durum bu. Hangi konuda emin değilsin? Birlikte düşünelim.",
            f"Sorun değil! Hangi kısım anlaşılmadı? Daha iyi açıklayayım.",
            f"Kafan karışıksa adım adım gidelim. Ne hissediyorsun tam olarak?",
        ])

    # Düşünce soruları — "ne yapmalıyım", "karar veremiyorum"
    if any(w in s for w in ["ne yapmaliyim", "karar veremiyorum", "hangisini secmeliyim", "onerir misin"]):
        return random.choice([
            f"Karar vermek için biraz daha bilgiye ihtiyacım var. Seçeneklerin neler?",
            f"İyi bir karar için durumu biraz analiz edelim. Ne arasında kararsız kaldın?",
            f"Sana yardımcı olabilirim! Önce durumu anlat, sonra birlikte değerlendirelim.",
        ])

    # Şikayet / hayal kırıklığı
    if any(w in s for w in ["calismiyor", "hata", "sorun", "yapamiyorum", "olmuyor", "beceremedim"]):
        return random.choice([
            "Ne tam olarak çalışmıyor? Hangi adımda takıldın?",
            "Anlıyorum, sinir bozucu olabilir. Sorunu daha iyi anlayabilmem için ne denediğini anlatır mısın?",
            "Birlikte çözelim. Önce ne olmasını bekliyordun, ne oldu?",
        ])

    return None

def _baglamdan_cevap(soru, baglam):
    if not baglam:
        return None
    s = _normalize(soru)
    if any(w in s for w in ["o ne", "daha fazla", "devam et", "anlat", "acikla", "neden"]):
        son = baglam[-1] if baglam else None
        if son:
            konu = son.get("konu", "")
            cevap, _ = _web_ozet_al(konu + " detay")
            if cevap:
                return cevap
    return None


# Kategori tahmini
KATEGORILER = {
    "kişi":     ["kimdir", "kim", "oyuncu", "futbolcu", "bilim", "müzisyen", "sanatçı", "politikacı", "tarihci", "yazar"],
    "yer":      ["nerede", "şehir", "ülke", "kıta", "nehir", "dağ", "okyanus", "deniz", "köy", "ilçe"],
    "bilim":    ["nedir", "atom", "hücre", "fizik", "kimya", "biyoloji", "matematik", "uzay", "evren", "dna", "gen"],
    "teknoloji":["yazılım", "python", "kod", "bilgisayar", "internet", "uygulama", "yapay zeka", "robot", "program"],
    "spor":     ["gol", "maç", "takım", "liga", "şampiyon", "olimpiyat", "futbol", "basketbol", "tenis", "yüzme"],
    "tarih":    ["yılında", "savaş", "imparatorluk", "devrim", "antik", "ortaçağ", "osmanlı", "cumhuriyet"],
    "sağlık":   ["hastalık", "ilaç", "tedavi", "vitamin", "kalori", "beslenme", "egzersiz", "uyku"],
    "sanat":    ["müzik", "film", "resim", "heykel", "roman", "şiir", "tiyatro", "dans", "albüm"],
    "ekonomi":  ["para", "dolar", "borsa", "enflasyon", "gdp", "ticaret", "şirket", "maaş", "kripto"],
}

def _kategori_tahmin(metin):
    m = _normalize(metin)
    for kat, anahtar in KATEGORILER.items():
        if any(a in m for a in anahtar):
            return kat
    return "genel"

def _baglanti_kur(konu, yeni_bilgi):
    """Yeni öğrenilen bilgiyi mevcut bilgilerle ilişkilendir"""
    global _bellek
    konu_n = _normalize(konu)
    ilgili = []
    yeni_n = _normalize(yeni_bilgi)
    yeni_kelimeler = set(yeni_n.split()) - {"ve", "ile", "bir", "bu", "da", "de", "nin", "nın"}
    for mevcut_k in list(_bellek["bilgiler"].keys())[:50]:
        mk_n = _normalize(mevcut_k)
        if mk_n == konu_n:
            continue
        mk_kelimeler = set(mk_n.split())
        ortak = len(yeni_kelimeler & mk_kelimeler)
        if ortak >= 1 and mk_n in yeni_n:
            ilgili.append(mevcut_k)
    _bellek["baglantilar"][konu_n] = ilgili[:5]

def _guvenilirlik_hesapla(kaynak, cevap):
    """Kaynağa göre güvenilirlik puanı ver"""
    puan = 50  # varsayılan
    if kaynak in ("Wikipedia TR", "Wikipedia EN"):
        puan = 85
    elif kaynak == "DuckDuckGo":
        puan = 70
    elif kaynak == "Kullanıcı":
        puan = 95  # kullanıcının öğrettikleri en güvenilir
    elif kaynak == "JARVIS-Mantık":
        puan = 99
    # Kısa cevaplar daha az güvenilir
    if len(cevap) < 30:
        puan -= 10
    return min(100, max(0, puan))

def ogret(soru, cevap):
    global _bellek
    k = _normalize(soru)[:80]
    # Zaten biliyor mu?
    if k in _bellek.get("kullanici_bilgileri", {}):
        eski = _bellek["kullanici_bilgileri"][k]
        if _normalize(eski) == _normalize(cevap):
            return f"⚡ Bunu zaten biliyorum! '{soru}' = {cevap[:60]}..."
        _bellek["kullanici_bilgileri"][k] = cevap.strip()
        _bellek["bilgiler"][k] = cevap.strip()
        _bellek["guvenilirlik"][k] = 95
        bellek_kaydet(_bellek)
        return f"🔄 Güncelledim! '{soru}' için yeni bilgiyi kaydettim."
    # Yeni bilgi
    _bellek["kullanici_bilgileri"][k] = cevap.strip()
    _bellek["bilgiler"][k] = cevap.strip()
    _bellek["kategoriler"][k] = _kategori_tahmin(soru + " " + cevap)
    _bellek["guvenilirlik"][k] = 95
    _baglanti_kur(k, cevap)
    _bellek["ogrenilen_sayisi"] += 1
    bellek_kaydet(_bellek)
    kat = _bellek["kategoriler"][k]
    baglantilar = _bellek["baglantilar"].get(k, [])
    bag_str = f" | Bağlantı: {', '.join(baglantilar[:2])}" if baglantilar else ""
    return f"✅ Öğrendim! [{kat.upper()}] '{soru}'{bag_str}"


def ask_ai(soru, system_prompt=None):
    global _ai_locked, _bellek
    if _ai_locked:
        return "Düşünüyorum, bir saniye...", "JARVIS"
    _ai_locked = True
    try:
        soru_t = soru.strip()
        _bellek.setdefault("konusma_gecmisi", []).append({
            "soru": soru_t, "zaman": datetime.datetime.now().isoformat()
        })
        if len(_bellek["konusma_gecmisi"]) > 300:
            _bellek["konusma_gecmisi"] = _bellek["konusma_gecmisi"][-300:]

        # Katman 1: Hızlı mantık
        m = _cevap_uret(soru_t)
        if m:
            _bellek.setdefault("bilgiler", {})[_normalize(soru_t)[:50]] = m
            _bellek["ogrenilen_sayisi"] = _bellek.get("ogrenilen_sayisi", 0) + 1
            bellek_kaydet(_bellek)
            return m, "JARVIS-Mantık"

        # Katman 1.2: Özel Skill kontrolü (OpenJarvis ilhamlı dosya tabanlı yetenekler)
        skill_cevap = _skill_kontrol(_normalize(soru_t))
        if skill_cevap:
            bellek_kaydet(_bellek)
            return skill_cevap, "JARVIS-Skill"

        # Katman 2: Bellek
        k, skor = _benzer_bul(soru_t, _bellek.get("bilgiler", {}))
        if k and skor > 0.68:
            bellek_kaydet(_bellek)
            return _bellek["bilgiler"][k], "JARVIS-Bellek"

        # Katman 3: Bağlam
        baglam = _bellek.get("baglam", [])
        bc = _baglamdan_cevap(soru_t, baglam)
        if bc:
            return bc, "JARVIS-Bağlam"

        # ══ KATMAN 3.5: OLLAMA GERÇEK AI ═══════════════════════
        if ollama_aktif_mi():
            ollama_c = _ollama_sor(soru_t, _SOHBET.get("gecmis", []))
            if ollama_c:
                anahtar = _normalize(soru_t)[:60]
                _bellek["bilgiler"][anahtar] = ollama_c
                _bellek.setdefault("kategoriler", {})[anahtar] = _kategori_tahmin(soru_t + " " + ollama_c)
                _bellek["ogrenilen_sayisi"] = _bellek.get("ogrenilen_sayisi", 0) + 1
                _bellek.setdefault("baglam", []).append({"soru": soru_t, "konu": soru_t, "cevap": ollama_c[:120]})
                if len(_bellek["baglam"]) > 15:
                    _bellek["baglam"] = _bellek["baglam"][-15:]
                bellek_kaydet(_bellek)
                return ollama_c, "Ollama-AI"

        # ══ KATMAN 3.7: AKIL YÜRÜTME SONUCU ══════════════════
        # Düşünce zincirinden analiz/plan cevabı geldiyse kullan
        try:
            if dz_cevap and dz_kaynak in ("JARVIS-Analiz", "JARVIS-Plan"):
                _bellek_kaydet_ve_don(soru_t, dz_cevap, dz_kaynak)
                return dz_cevap, dz_kaynak
        except: pass

                # Katman 4+5: Web Araştırma
        print(f"[JARVIS] Web'de araştırıyorum: {soru_t}")
        cevap, kaynak = _web_ozet_al(soru_t)
        if cevap:
            anahtar = _normalize(soru_t)[:60]
            # Zaten biliyor mu?
            if anahtar in _bellek.get("bilgiler", {}):
                return _bellek["bilgiler"][anahtar], "JARVIS-Bellek"
            _bellek["bilgiler"][anahtar] = cevap
            _bellek["kategoriler"][anahtar] = _kategori_tahmin(soru_t + " " + cevap)
            _bellek["guvenilirlik"][anahtar] = _guvenilirlik_hesapla(kaynak, cevap)
            _baglanti_kur(anahtar, cevap)
            _bellek["ogrenilen_sayisi"] = _bellek.get("ogrenilen_sayisi", 0) + 1
            _bellek.setdefault("arastirma_gecmisi", []).append({
                "sorgu": soru_t, "kaynak": kaynak,
                "guvenilirlik": _bellek["guvenilirlik"][anahtar],
                "kategori": _bellek["kategoriler"][anahtar],
                "zaman": datetime.datetime.now().isoformat()
            })
            _bellek.setdefault("baglam", []).append({"konu": soru_t, "cevap": cevap[:100]})
            if len(_bellek["baglam"]) > 10:
                _bellek["baglam"] = _bellek["baglam"][-10:]
            bellek_kaydet(_bellek)
            kat = _bellek["kategoriler"][anahtar]
            guvenir = _bellek["guvenilirlik"][anahtar]
            baglantilar = _bellek["baglantilar"].get(anahtar, [])
            bag_str = f" | 🔗 {', '.join(baglantilar[:2])}" if baglantilar else ""
            return f"🔍 [{kat.upper()} | ★{guvenir}%] {cevap}{bag_str}", kaynak

        # Katman 6: Konu tahmini
        tahmin = re.sub(r"(nedir|kimdir|nerede|ne zaman|nasil|nicin|kac)", "", _normalize(soru_t)).strip()
        if tahmin and tahmin != _normalize(soru_t) and len(tahmin) > 2:
            cevap, kaynak = _web_ozet_al(tahmin)
            if cevap:
                anahtar = _normalize(soru_t)[:60]
                if anahtar not in _bellek.get("bilgiler", {}):
                    _bellek["bilgiler"][anahtar] = cevap
                    _bellek["kategoriler"][anahtar] = _kategori_tahmin(soru_t + " " + cevap)
                    _bellek["guvenilirlik"][anahtar] = _guvenilirlik_hesapla(kaynak, cevap)
                    _baglanti_kur(anahtar, cevap)
                    _bellek["ogrenilen_sayisi"] = _bellek.get("ogrenilen_sayisi", 0) + 1
                    bellek_kaydet(_bellek)
                return f"🔍 [{_bellek['kategoriler'][anahtar].upper()}] {cevap}", kaynak

        bellek_kaydet(_bellek)
        # Son çare: soruyu parçalara böl ve her kelime için ara
        kelimeler = [w for w in soru_t.split() if len(w) > 3]
        for kelime in kelimeler[:3]:
            cevap, kaynak = _web_ozet_al(kelime)
            if cevap and len(cevap) > 50:
                anahtar = _normalize(soru_t)[:60]
                _bellek["bilgiler"][anahtar] = cevap
                _bellek["ogrenilen_sayisi"] = _bellek.get("ogrenilen_sayisi", 0) + 1
                bellek_kaydet(_bellek)
                return f"🔍 {cevap}", kaynak

        # Hiçbir şey bulunamadı — akıllı ve dürüst yanıt ver
        tip = _soru_tipini_bul(_normalize(soru_t))
        if tip == "analiz":
            yanit = (f"Bu konuyu analiz etmek istiyorum ama yeterli verim yok. "
                     f"Hangi açıdan değerlendirmemi istiyorsun?")
        elif tip == "plan":
            yanit = ("Bir plan oluşturabilirim ama önce amacını anlayayım. "
                     "Ne elde etmek istiyorsun?")
        elif tip == "eylem":
            yanit = ("Bu işlemi yapabilmem için daha fazla bilgiye ihtiyacım var. "
                     "Tam olarak ne yapmamı istiyorsun?")
        else:
            yanit = random.choice([
                f"Bu konuda emin değilim, dürüst olmak isterim. Soruyu biraz açar mısın?",
                f"'{soru_t[:35]}' hakkında bilgim sınırlı. 'google {soru_t[:20]}' yazarsan bakabiliriz.",
                f"Şu an kesin bir şey söyleyemem. 'öğren: {soru_t[:25]} = cevap' yazarsan öğrenirim!",
            ])
        return yanit, "JARVIS-Öğreniyor"
    finally:
        _ai_locked = False


def _ask_ai_ve_kaydet(soru, system_prompt=None):
    """ask_ai'ı çağırır ve sohbete kaydeder"""
    cevap, kaynak = ask_ai(soru, system_prompt)
    _sohbet_ekle(soru, cevap, kaynak)
    return cevap, kaynak


def web_search(query):
    try:
        cevap, kaynak = _duckduckgo_ara(query)
        webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(query)}")
        if cevap:
            return f"🌐 {kaynak}: {cevap}\n\nGoogle'da da açıldı."
        return f"Google'da aratıldı: '{query}' — Tarayıcıda açıldı."
    except Exception as e:
        return f"Arama hatası: {e}"


def download_package(pkg_name):
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pkg_name],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            return f"✅ '{pkg_name}' paketi başarıyla yüklendi!"
        return f"Yükleme hatası: {result.stderr[:200]}"
    except Exception as e:
        return f"İndirme hatası: {e}"


def self_update(new_code: str):
    this_file = os.path.abspath(__file__)
    backup = this_file + ".bak"
    shutil.copy2(this_file, backup)
    try:
        ast.parse(new_code)
    except SyntaxError as e:
        return False, f"Sözdizimi hatası: {e}\nGüncelleme iptal edildi, yedek korundu."
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8")
    tmp.write(new_code)
    tmp.close()
    check = subprocess.run(
        [sys.executable, "-c", f"import ast; ast.parse(open(r'{tmp.name}', encoding='utf-8').read())"],
        capture_output=True
    )
    os.unlink(tmp.name)
    if check.returncode != 0:
        return False, "Kod doğrulaması başarısız, güncelleme iptal edildi."
    with open(this_file, "w", encoding="utf-8") as f:
        f.write(new_code)
    os.execv(sys.executable, [sys.executable] + sys.argv)
    return True, "Güncelleme tamamlandı!"


def ai_self_update(description: str):
    this_file = os.path.abspath(__file__)
    with open(this_file, "r", encoding="utf-8") as f:
        current_code = f.read()
    desc = _normalize(description)
    new_code = current_code

    # ── RENK DEĞİŞTİR ─────────────────────────────────────────
    renk_map = {
        "mavi": "#00aaff", "yesil": "#00ff88", "kirmizi": "#ff2222",
        "turuncu": "#ff8800", "mor": "#aa00ff", "sari": "#ffdd00",
        "pembe": "#ff66aa", "beyaz": "#ffffff", "cyan": "#00ffff",
        "lacivert": "#003388", "altin": "#ffcc00",
    }
    for ad, hex_kod in renk_map.items():
        if ad in desc:
            new_code = re.sub(r'"idle":\s*"#[0-9a-fA-F]+"', f'"idle":        "{hex_kod}"', new_code)
            ok, msg = self_update(new_code)
            return ok, msg, "JARVIS-SelfUpdate"

    # ── VERSİYON GÜNCELLE ─────────────────────────────────────
    if any(w in desc for w in ["versiyon", "version", "surum", "v7", "v8", "v9"]):
        yeni_v = re.search(r"v?(\d+\.?\d*)", desc)
        if yeni_v:
            new_code = re.sub(r"v6\.\d", f"v{yeni_v.group(1)}", new_code)
            ok, msg = self_update(new_code)
            return ok, msg, "JARVIS-SelfUpdate"

    # ── YENİ BİLGİ EKLE ───────────────────────────────────────
    if any(w in desc for w in ["bilgi ekle", "ogren", "ogret", "ekle"]):
        eslesme = re.search(r"[:=]\s*(.+)$", description.strip())
        if eslesme:
            deger = eslesme.group(1).strip()
            anahtar = re.sub(r"(bilgi ekle|ogret|ogren|ekle)[:\s]*", "", desc).strip()[:60]
            if anahtar and deger:
                eklenti = '    "' + anahtar + '": "' + deger + '",\n'
                hedef = '    "sevdiğin renk": "Parlak mavi! Tıpkı orb ışığım gibi 💙",\n'
                new_code = new_code.replace(hedef, hedef + eklenti)
                ok, msg = self_update(new_code)
                return ok, msg, "JARVIS-SelfUpdate"

    # ── OTO ÖĞRENME HIZI ──────────────────────────────────────
    if any(w in desc for w in ["hizlandir", "daha hizli", "hiz artir", "1 saniye", "2 saniye"]):
        sure = "1" if "1" in desc else "2"
        new_code = re.sub(r"time\.sleep\(3\)", f"time.sleep({sure})", new_code)
        ok, msg = self_update(new_code)
        return ok, msg, "JARVIS-SelfUpdate"

    if any(w in desc for w in ["yavasla", "daha yavas", "5 saniye", "10 saniye"]):
        sure = "10" if "10" in desc else "5"
        new_code = re.sub(r"time\.sleep\(3\)", f"time.sleep({sure})", new_code)
        ok, msg = self_update(new_code)
        return ok, msg, "JARVIS-SelfUpdate"

    # ── YENİ WEB SİTESİ KOMUTU EKLE ──────────────────────────
    if any(w in desc for w in ["site ekle", "website ekle", "adres ekle"]):
        eslesme = re.search(r"(site|website|adres)\s+ekle[:\s]+(\w+)\s*[=:]\s*(https?://\S+)", description, re.I)
        if eslesme:
            isim = eslesme.group(2).lower()
            url = eslesme.group(3)
            eklenti = '            ("' + isim + '",):          "' + url + '",\n'
            hedef = '            ("chatgpt",):          "https://chat.openai.com",\n'
            new_code = new_code.replace(hedef, hedef + eklenti)
            ok, msg = self_update(new_code)
            return ok, msg, "JARVIS-SelfUpdate"

    # ── YENİ UYGULAMA KOMUTU EKLE ────────────────────────────
    if any(w in desc for w in ["uygulama ekle", "program ekle", "komut ekle"]):
        eslesme = re.search(r"(uygulama|program|komut)\s+ekle[:\s]+(\w+)\s*[=:]\s*(.+)$", description, re.I)
        if eslesme:
            isim = eslesme.group(2).lower()
            komut = eslesme.group(3).strip()
            isim_cap = isim.capitalize()
            eklenti = '            ("' + isim + '",): ("' + komut + '", "' + isim_cap + ' acildi."),\n'
            hedef = '            ("discord",): ("start discord:", "Discord açıldı."),\n'
            new_code = new_code.replace(hedef, hedef + eklenti)
            ok, msg = self_update(new_code)
            return ok, msg, "JARVIS-SelfUpdate"

    # ── OTO ÖĞRENME KONUSU EKLE ───────────────────────────────
    if any(w in desc for w in ["konu ekle", "ogrenme konusu", "yeni konu"]):
        eslesme = re.search(r"(konu ekle|ogrenme konusu|yeni konu)[:\s]+(.+)$", description, re.I)
        if eslesme:
            konu = eslesme.group(2).strip()
            hedef = '        # Doğa\n'
            yeni_blok = '        # Yeni eklenen\n        "' + konu + '",\n        # Doğa\n'
            new_code = new_code.replace(hedef, yeni_blok)
            ok, msg = self_update(new_code)
            return ok, msg, "JARVIS-SelfUpdate"

    # ── BAŞLIK DEĞİŞTİR ───────────────────────────────────────
    if any(w in desc for w in ["baslik", "isim degistir", "ad degistir"]):
        eslesme = re.search(r"[=:]\s*(.+)$", description)
        if eslesme:
            yeni_isim = eslesme.group(1).strip()
            new_code = new_code.replace(
                'self.root.title("J.A.R.V.I.S  v7.0")',
                f'self.root.title("{yeni_isim}")'
            )
            ok, msg = self_update(new_code)
            return ok, msg, "JARVIS-SelfUpdate"

    # ── PENCERE BOYUTU ────────────────────────────────────────
    if any(w in desc for w in ["pencere", "boyut", "kucult", "buyut"]):
        if "kucult" in desc:
            new_code = new_code.replace('self.root.geometry("720x920")', 'self.root.geometry("600x800")')
        elif "buyut" in desc:
            new_code = new_code.replace('self.root.geometry("720x920")', 'self.root.geometry("900x1050")')
        ok, msg = self_update(new_code)
        return ok, msg, "JARVIS-SelfUpdate"

    # ── GENEL: yorum ekle ve kaydet ───────────────────────────
    tarih = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    yorum = "\n# [Güncelleme " + tarih + "]: " + description + "\n" 
    new_code = new_code.replace(
        'if __name__ == "__main__":',
        yorum + 'if __name__ == "__main__":'
    )
    ok, msg = self_update(new_code)
    return ok, msg, "JARVIS-SelfUpdate"

def speak(text):
    """
    Python 3.14 uyumlu TTS — playsound/pygame YOK
    1. edge-tts + PowerShell MediaPlayer (mp3)
    2. pyttsx3
    3. PowerShell SAPI (her zaman çalışır)
    """
    def _run():
        temiz = text.replace('"', "").replace("'", "").replace("\n", " ").strip()[:350]
        if not temiz:
            return

        # ── Katman 1: edge-tts + PowerShell MediaPlayer ───────
        try:
            import edge_tts as _et
            import asyncio as _aio
            import tempfile as _tf
            import os as _os2

            async def _tts(txt, path):
                c = _et.Communicate(txt, voice="tr-TR-AhmetNeural", rate="+5%", pitch="-15Hz")
                await c.save(path)

            tmp = _tf.mktemp(suffix=".mp3")
            _aio.run(_tts(temiz, tmp))
            if _os2.path.exists(tmp) and _os2.path.getsize(tmp) > 100:
                ps = (
                    f'$mp = New-Object System.Windows.Media.MediaPlayer;'
                    f'$mp.Open([uri]"{tmp}");'
                    f'$mp.Play();'
                    f'Start-Sleep -Milliseconds 100;'
                    f'while($mp.NaturalDuration.HasTimeSpan -eq $false){{Start-Sleep -Milliseconds 50}};'
                    f'$dur = $mp.NaturalDuration.TimeSpan.TotalSeconds + 1;'
                    f'Start-Sleep -Seconds $dur;'
                    f'$mp.Close();'
                    f'Remove-Item -Path "{tmp}" -ErrorAction SilentlyContinue'
                )
                subprocess.Popen(
                    ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", ps],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                return
        except Exception as e1:
            print(f"[Ses-1 edge-tts] {e1}")

        # ── Katman 2: pyttsx3 ─────────────────────────────────
        try:
            import pyttsx3 as _py
            eng = _py.init()
            voices = eng.getProperty("voices")
            for v in voices:
                if any(x in v.name.lower() for x in ["male", "david", "zira", "hazel"]):
                    eng.setProperty("voice", v.id)
                    break
            eng.setProperty("rate", 170)
            eng.say(temiz)
            eng.runAndWait()
            eng.stop()
            return
        except Exception as e2:
            print(f"[Ses-2 pyttsx3] {e2}")

        # ── Katman 3: PowerShell SAPI (kesinlikle çalışır) ────
        try:
            ps = (
                'Add-Type -AssemblyName System.Speech;'
                '$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;'
                '$s.Rate=2;'
                'try{$s.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::Male)}catch{};'
                f'$s.Speak("{temiz}");'
            )
            subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", ps],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception as e3:
            print(f"[Ses-3 PowerShell] {e3}")

    threading.Thread(target=_run, daemon=True).start()


SAMPLE_RATE = 16000
DURATION = 4


def record_audio():
    if not SD_OK:
        return None
    audio = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype=np.int16)
    sd.wait()
    return audio.flatten()


def numpy_to_audio(audio_np):
    if not SR_OK:
        return None
    return sr.AudioData(audio_np.tobytes(), SAMPLE_RATE, 2)


class OrbCanvas(tk.Canvas):
    COLORS = {
        "idle":        "#00aaff",
        "thinking":    "#ff8800",
        "learning":    "#ff9900",
        "learned":     "#00ff88",
        "error":       "#ff2222",
        "agent_idle":  "#ffffff",
        "agent_think": "#4488ff",
        "agent_error": "#ff2222",
        "sleep":       "#001122",
    }

    def __init__(self, parent, size=200, **kw):
        super().__init__(parent, width=size, height=size, bg="#020b18", highlightthickness=0, **kw)
        self.size = size
        self.cx = size // 2
        self.cy = size // 2
        self.state_key = "idle"
        self.agent_mode = False
        self._cur_color = self._hex_to_rgb(self.COLORS["idle"])
        self._running = True
        self._t = 0
        self.particles = []
        N = 80
        golden = math.pi * (3 - math.sqrt(5))
        for i in range(N):
            y = 1 - (i / (N - 1)) * 2
            r_ = math.sqrt(max(0, 1 - y * y))
            phi = golden * i
            x_ = math.cos(phi) * r_
            z_ = math.sin(phi) * r_
            self.particles.append({
                "bx": x_, "by": y, "bz": z_,
                "ox": random.uniform(-0.08, 0.08),
                "oy": random.uniform(-0.08, 0.08),
                "oz": random.uniform(-0.08, 0.08),
                "spd_x": random.uniform(-0.007, 0.007),
                "spd_y": random.uniform(-0.007, 0.007),
                "spd_z": random.uniform(-0.005, 0.005),
                "size":  random.uniform(2.5, 5.0),
                "phase": random.uniform(0, math.pi * 2),
            })
        self._angle_x = 0.0
        self._angle_y = 0.0
        self._angle_z = 0.0
        self._animate()

    @staticmethod
    def _hex_to_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def _rgb_to_hex(r, g, b):
        return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

    def _lerp_color(self, target_hex, speed=0.06):
        tr, tg, tb = self._hex_to_rgb(target_hex)
        cr, cg, cb = self._cur_color
        cr += (tr - cr) * speed
        cg += (tg - cg) * speed
        cb += (tb - cb) * speed
        self._cur_color = (cr, cg, cb)
        return self._rgb_to_hex(cr, cg, cb)

    def set_state(self, state, agent=False):
        self.agent_mode = agent
        if agent:
            key = f"agent_{state}" if f"agent_{state}" in self.COLORS else state
        else:
            key = state
        self.state_key = key if key in self.COLORS else "idle"

    @staticmethod
    def _rotate(x, y, z, ax, ay, az):
        cos_x, sin_x = math.cos(ax), math.sin(ax)
        y, z = cos_x * y - sin_x * z, sin_x * y + cos_x * z
        cos_y, sin_y = math.cos(ay), math.sin(ay)
        x, z = cos_y * x + sin_y * z, -sin_y * x + cos_y * z
        cos_z, sin_z = math.cos(az), math.sin(az)
        x, y = cos_z * x - sin_z * y, sin_z * x + cos_z * y
        return x, y, z

    def _animate(self):
        if not self._running:
            return
        self._t += 1
        t = self._t
        target = self.COLORS.get(self.state_key, "#00aaff")
        color = self._lerp_color(target)
        dim = self._rgb_to_hex(self._cur_color[0]*0.18, self._cur_color[1]*0.18, self._cur_color[2]*0.18)
        thinking = "think" in self.state_key
        spd = 0.012 if not thinking else 0.022
        self._angle_y += spd
        self._angle_x += spd * 0.37
        self._angle_z += spd * 0.19
        self.delete("all")
        glow_r = 52 + 8 * math.sin(t * 0.04)
        self._draw_glow(glow_r, dim)
        for i in range(3):
            self._draw_ring(60 + i * 18, 0.12 - i * 0.03, color)
        pts = []
        radius = 68
        for p in self.particles:
            if thinking:
                p["spd_x"] += random.uniform(-0.0005, 0.0005)
                p["spd_y"] += random.uniform(-0.0005, 0.0005)
                p["spd_x"] = max(-0.02, min(0.02, p["spd_x"]))
                p["spd_y"] = max(-0.02, min(0.02, p["spd_y"]))
            p["ox"] += p["spd_x"]
            p["oy"] += p["spd_y"]
            p["oz"] += p["spd_z"]
            p["ox"] = max(-0.25, min(0.25, p["ox"]))
            p["oy"] = max(-0.25, min(0.25, p["oy"]))
            bx = p["bx"] + p["ox"]
            by = p["by"] + p["oy"]
            bz = p["bz"] + p["oz"]
            norm = math.sqrt(bx*bx + by*by + bz*bz) or 1
            bx, by, bz = bx/norm, by/norm, bz/norm
            rx, ry, rz = self._rotate(bx, by, bz, self._angle_x, self._angle_y, self._angle_z)
            wave = math.sin(t * 0.05 + p["phase"]) * 4
            wx = self.cx + (rx * radius + wave * rx)
            wy = self.cy + (ry * radius * 0.55 + wave * ry)
            pts.append((wx, wy, rz, p["size"]))
        pts.sort(key=lambda v: v[2])
        for wx, wy, depth, size in pts:
            depth_norm = (depth + 1) / 2
            alpha = 0.25 + depth_norm * 0.75
            sz = size * (0.5 + depth_norm * 0.5)
            cr, cg, cb = self._cur_color
            rc = self._rgb_to_hex(cr * alpha, cg * alpha, cb * alpha)
            self.create_oval(wx - sz, wy - sz, wx + sz, wy + sz, fill=rc, outline="")
        core_r = 12 + 3 * math.sin(t * 0.05)
        self.create_oval(self.cx-core_r, self.cy-core_r, self.cx+core_r, self.cy+core_r, fill=color, outline="")
        inner = core_r * 0.4
        self.create_oval(self.cx-inner, self.cy-inner, self.cx+inner, self.cy+inner, fill="#ffffff", outline="")
        self.after(33, self._animate)

    def _draw_glow(self, radius, color):
        for i in range(6, 0, -1):
            r_ = radius * i / 6
            self.create_oval(self.cx-r_, self.cy-r_, self.cx+r_, self.cy+r_, fill=color, outline="")

    def _draw_ring(self, radius, alpha, color):
        cr, cg, cb = self._hex_to_rgb(color)
        rc = self._rgb_to_hex(cr*alpha*2.5, cg*alpha*2.5, cb*alpha*2.5)
        self.create_oval(self.cx-radius, self.cy-radius*0.45, self.cx+radius, self.cy+radius*0.45, outline=rc, width=1)

    def stop(self):
        self._running = False


class JarvisApp:
    MODES = {
        "NORMAL": {
            "color":  "#00d4ff",
            "status": "● NORMAL MOD — Günlük Kullanım",
            "orb":    "idle",
            "agent":  False,
            "aciklama": "Doğal sohbet, bilgi verme, bağlam takibi. Sistem değişikliği YOK.",
        },
        "KAPALI": {
            "color":  "#ff8800",
            "status": "● GELİŞİM MODU — Öğrenme & Güncelleme",
            "orb":    "learning",
            "agent":  False,
            "aciklama": "Öğrenme, bellek güncelleme, kullanıcı onaylı self-update.",
        },
        "SESSIZ": {
            "color":  "#aa44ff",
            "status": "● SESSİZ MOD — Kod & Araştırma",
            "orb":    "idle",
            "agent":  False,
            "aciklama": "Kod yazma, programlama öğrenme, dil araştırma.",
        },
        "AJAN": {
            "color":  "#00ff88",
            "status": "● AJAN MODU — Gözetimli Yardımcı",
            "orb":    "idle",
            "agent":  True,
            "aciklama": "Araştırma, görev planlama, adım adım çalışma. Her adımda onay.",
        },
    }

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("J.A.R.V.I.S  v7.0")
        self.root.geometry("720x920")
        self.root.configure(bg="#020b18")
        self.root.resizable(True, True)
        self.listening = False
        self.mode = "NORMAL"
        self.recognizer = sr.Recognizer() if SR_OK else None
        self.cmd_history = []
        self.hist_idx = -1
        self._build_ui()
        threading.Thread(target=self._delayed_init, daemon=True).start()

    def _build_ui(self):
        root = self.root
        top = tk.Frame(root, bg="#020b18")
        top.pack(fill="x", padx=24, pady=(16, 0))
        tk.Label(top, text="J.A.R.V.I.S", font=("Courier", 30, "bold"), fg="#00d4ff", bg="#020b18").pack(side="left")
        right_info = tk.Frame(top, bg="#020b18")
        right_info.pack(side="right")
        self.clock_lbl = tk.Label(right_info, text="", font=("Courier", 13, "bold"), fg="#00d4ff", bg="#020b18")
        self.clock_lbl.pack(anchor="e")
        self.date_lbl = tk.Label(right_info, text="", font=("Courier", 9), fg="#1a4a6a", bg="#020b18")
        self.date_lbl.pack(anchor="e")
        tk.Label(root, text="JUST A RATHER VERY INTELLIGENT SYSTEM  ·  v7.0",
                 font=("Courier", 8), fg="#1a4a6a", bg="#020b18").pack()
        self.status_lbl = tk.Label(root, text="● SİSTEM AKTİF", font=("Courier", 10, "bold"),
                                    fg="#00ff88", bg="#020b18")
        self.status_lbl.pack(pady=(6, 2))
        mf = tk.Frame(root, bg="#020b18")
        mf.pack(fill="x", padx=24, pady=4)
        for label, mode_key in [
            ("◈  NORMAL", "NORMAL"),
            ("📚  GELİŞİM", "KAPALI"),
            ("💻  SESSİZ", "SESSIZ"),
            ("⚡  AJAN", "AJAN"),
        ]:
            tk.Button(mf, text=label, font=("Courier", 9, "bold"), fg="#1a4a6a", bg="#040e1c",
                      relief="flat", activebackground="#071e38", activeforeground="#00d4ff",
                      padx=8, pady=7, command=lambda m=mode_key: self.set_mode(m)
                      ).pack(side="left", expand=True, fill="x", padx=2)
        orb_frame = tk.Frame(root, bg="#020b18")
        orb_frame.pack(pady=6)
        self.orb = OrbCanvas(orb_frame, size=210)
        self.orb.pack()
        self.orb_label = tk.Label(root, text="D İ N L İ Y O R U M",
                                   font=("Courier", 9, "bold"), fg="#00d4ff", bg="#020b18")
        self.orb_label.pack(pady=(0, 4))
        af = tk.Frame(root, bg="#040e1c", pady=6)
        af.pack(fill="x", padx=24, pady=2)
        tk.Label(af, text="AI MOTOR SİSTEMİ  v7.2  ·  Bellek + Mantık + DuckDuckGo + Wikipedia",
                 font=("Courier", 8), fg="#1a4a6a", bg="#040e1c").pack()
        ar = tk.Frame(af, bg="#040e1c")
        ar.pack(pady=2)
        self.ollama_lbl = tk.Label(ar, text="🔴 Ollama",
                                     font=("Courier", 8, "bold"), fg="#ff4444", bg="#040e1c", padx=6)
        self.ollama_lbl.pack(side="left")
        for lbl in ["💾 Bellek", "⚡ Mantık", "🌐 DuckDuckGo", "📖 Wikipedia", "🔗 Bağlam"]:
            tk.Label(ar, text=lbl, font=("Courier", 8, "bold"), fg="#00ff88", bg="#040e1c", padx=6).pack(side="left")
        tk.Label(root, text="KONUŞMA GEÇMİŞİ", font=("Courier", 8), fg="#1a4a6a", bg="#020b18").pack(pady=(8, 2))
        self.chat_area = scrolledtext.ScrolledText(root, font=("Courier", 10), fg="#7fd4f7", bg="#030f20",
                                                    height=7, relief="flat", bd=0, state="disabled", wrap="word")
        self.chat_area.pack(fill="x", padx=24)
        self.chat_area.tag_config("user",  foreground="#00ff88")
        self.chat_area.tag_config("ai",    foreground="#00d4ff")
        self.chat_area.tag_config("sys",   foreground="#1a6a4a")
        self.chat_area.tag_config("warn",  foreground="#ffaa00")
        self.chat_area.tag_config("error", foreground="#ff4444")
        self.response_lbl = tk.Label(root, text="Komut bekleniyor...",
                                      font=("Courier", 12), fg="#7fd4f7", bg="#040e1c",
                                      wraplength=660, justify="left", padx=16, pady=12)
        self.response_lbl.pack(fill="x", padx=24, pady=4)
        cf = tk.Frame(root, bg="#020b18")
        cf.pack(fill="x", padx=24, pady=4)
        self.cmd_entry = tk.Entry(cf, font=("Courier", 12), fg="#7fd4f7", bg="#040e1c",
                                   insertbackground="#00b4ff", relief="flat", bd=6)
        self.cmd_entry.pack(side="left", fill="x", expand=True)
        self.cmd_entry.bind("<Return>", lambda e: self.send_text_cmd())
        self.cmd_entry.bind("<Up>",     lambda e: self._hist_up())
        self.cmd_entry.bind("<Down>",   lambda e: self._hist_down())
        tk.Button(cf, text="GÖNDER ▶", font=("Courier", 9, "bold"), fg="#00d4ff", bg="#071e38",
                  relief="flat", padx=12, command=self.send_text_cmd).pack(side="right", padx=(6, 0))
        self.voice_btn = tk.Button(root, text="🎙  SESLİ KOMUT BAŞLAT",
                                    font=("Courier", 11, "bold"), fg="#1a4a6a", bg="#040e1c",
                                    relief="flat", pady=10, command=self.toggle_voice)
        self.voice_btn.pack(fill="x", padx=24, pady=4)
        tf = tk.Frame(root, bg="#020b18")
        tf.pack(fill="x", padx=24, pady=2)
        self.update_entry = tk.Entry(tf, font=("Courier", 10), fg="#ffaa00", bg="#040e1c",
                                      insertbackground="#ffaa00", relief="flat", bd=4, width=40)
        self.update_entry.insert(0, "Güncellemek istediğin özelliği yaz...")
        self.update_entry.pack(side="left", fill="x", expand=True)
        tk.Button(tf, text="⚙ GÜNCELLE", font=("Courier", 9, "bold"), fg="#ffaa00", bg="#040e1c",
                  relief="flat", padx=10, command=self._do_update).pack(side="right", padx=(6, 0))
        tk.Label(root, text="SİSTEM LOGU", font=("Courier", 8), fg="#1a4a6a", bg="#020b18").pack(pady=(6, 2))
        self.log_area = scrolledtext.ScrolledText(root, font=("Courier", 8), fg="#2a6a4a", bg="#020b18",
                                                   height=5, relief="flat", bd=0, state="disabled")
        self.log_area.pack(fill="both", expand=True, padx=24, pady=(0, 16))
        self.log("JARVIS v7.2 başlatıldı. Güçlendirilmiş beyin aktif.")
        self._update_clock()

    def log(self, msg, tag="sys"):
        self.log_area.config(state="normal")
        t = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_area.insert("end", f"[{t}] {msg}\n")
        self.log_area.see("end")
        self.log_area.config(state="disabled")

    def chat(self, who, msg):
        self.chat_area.config(state="normal")
        tags = {"user": "user", "ai": "ai", "warn": "warn", "error": "error"}
        tag = tags.get(who, "sys")
        prefix = {"user": "SEN   > ", "ai": "JARVIS> ", "warn": "UYARI > ", "error": "HATA  > "}.get(who, "SYS   > ")
        self.chat_area.insert("end", f"{prefix}{msg}\n", tag)
        self.chat_area.see("end")
        self.chat_area.config(state="disabled")

    def set_response(self, text):
        self.response_lbl.config(text=text)

    def set_orb(self, state):
        agent = self.mode == "AJAN"
        self.orb.set_state(state, agent=agent)
        labels = {"idle": "DİNLİYORUM", "thinking": "DÜŞÜNÜYORUM...", "error": "HATA ALGILANDI",
                  "learning": "📡 ARAŞTIRIYORUM...", "learned": "✅ ÖĞRENDİM!",
                  "sleep": "BEKLEME MODU", "agent_idle": "AJAN — HAZIR", "agent_think": "AJAN — ANALİZ"}
        key = f"agent_{state}" if agent and f"agent_{state}" in labels else state
        self.orb_label.config(text=labels.get(key, state.upper()))

    def set_mode(self, mode):
        eski_mod = self.mode
        self.mode = mode
        cfg = self.MODES.get(mode, self.MODES["NORMAL"])
        self.status_lbl.config(text=cfg["status"], fg=cfg["color"])
        self.set_orb(cfg["orb"])
        aciklama = cfg.get("aciklama", "")
        self.log(f"Mod: {eski_mod} → {mode}")
        self.chat("sys", f"━━ {mode} MOD ━━ {aciklama}")
        # Mod bazlı davranış bildirimi
        mod_mesajlari = {
            "NORMAL": f"Normal mod aktif. Doğal sohbet edebiliriz {KULLANICI_ISIM}!",
            "KAPALI": f"Geliştirme modu aktif. Öğrenebilirim, güncelleyebilirim — ama önce senin onayın lazım!",
            "SESSIZ": f"Sessiz mod aktif. Kod yazabilirim, araştırma yapabilirim. Ne üretmek istiyorsun?",
            "AJAN":   f"Ajan modu aktif. Görevini ver, adım adım çalışayım. Her adımda seni bilgilendiririm.",
        }
        if mode in mod_mesajlari and mode != eski_mod:
            self.root.after(100, lambda m=mod_mesajlari[mode]: self.reply(m))

    def _update_clock(self):
        now = datetime.datetime.now()
        self.clock_lbl.config(text=now.strftime("%H:%M:%S"))
        self.date_lbl.config(text=now.strftime("%d.%m.%Y  %A"))
        self.root.after(1000, self._update_clock)

    def _hist_up(self):
        if self.cmd_history:
            self.hist_idx = max(0, self.hist_idx - 1)
            self.cmd_entry.delete(0, "end")
            self.cmd_entry.insert(0, self.cmd_history[self.hist_idx])

    def _hist_down(self):
        if self.cmd_history:
            self.hist_idx = min(len(self.cmd_history) - 1, self.hist_idx + 1)
            self.cmd_entry.delete(0, "end")
            self.cmd_entry.insert(0, self.cmd_history[self.hist_idx])

    # Arka planda kendi kendine öğrenme konuları
    OTOMATIK_KONULAR = [
        # Teknoloji
        "yapay zeka", "kuantum bilgisayar", "uzay keşfi", "blockchain",
        "5G teknoloji", "elektrikli araçlar", "sanal gerçeklik", "artırılmış gerçeklik",
        "siber güvenlik", "bulut bilişim", "nesnelerin interneti", "robotik",
        "3D yazıcı", "drone teknolojisi", "otonom araç", "metaverse",
        # Bilim
        "kara delik", "Mars gezegeni", "DNA", "iklim değişikliği",
        "okyanus derinlikleri", "güneş enerjisi", "nöroloji", "evrim teorisi",
        "büyük patlama", "karanlık madde", "antimadde", "füzyon enerjisi",
        "kuantum mekaniği", "görelilik teorisi", "nanoteknoloji", "genetik mühendislik",
        "yapay organ", "uzay teleskop", "süperiletkenlik", "CRISPR",
        # Spor
        "Cristiano Ronaldo", "Lionel Messi", "NBA tarihi", "Formula 1",
        "tenis tarihi", "olimpiyat oyunları", "Tour de France", "UFC dövüş",
        "Muhammed Ali", "Michael Jordan", "Roger Federer", "LeBron James",
        # Tarih
        "Roma imparatorluğu", "Osmanlı tarihi", "Birinci Dünya Savaşı",
        "İkinci Dünya Savaşı", "Fransız devrimi", "Moğol imparatorluğu",
        "Mısır medeniyeti", "Yunan mitolojisi", "Viking tarihi", "Çin seddi",
        "Rönesans dönemi", "Sanayi devrimi", "Soğuk Savaş", "Ay'a yolculuk",
        # Ünlü İnsanlar
        "Albert Einstein", "Isaac Newton", "Nikola Tesla", "Stephen Hawking",
        "Elon Musk", "Steve Jobs", "Bill Gates", "Marie Curie",
        "Leonardo da Vinci", "Sigmund Freud", "Charles Darwin", "Alan Turing",
        "Neil Armstrong", "Galileo Galilei", "Aristoteles", "Sokrates",
        # Coğrafya
        "Amazon ormanı", "Antarktika", "Everest dağı", "Büyük Mercan Resifi",
        "Sahra çölü", "Atlantik okyanusu", "Pasifik okyanusu", "Nil nehri",
        "İzlanda volkanları", "Japonya kültürü", "Hindistan tarihi", "Brezilya",
        # Sağlık
        "kanser tedavisi", "Alzheimer hastalığı", "bağışıklık sistemi",
        "beyin nasıl çalışır", "uyku neden önemli", "beslenme bilimi",
        "meditasyon faydaları", "egzersiz bilimi", "vitamin eksikliği",
        # Sanat & Kültür
        "Beethoven hayatı", "Mozart hayatı", "Shakespeare eserleri",
        "Van Gogh tabloları", "Picasso sanatı", "sinema tarihi",
        "jazz müzik", "klasik müzik", "hip hop tarihi", "rock müzik tarihi",
        # Ekonomi & Finans
        "Bitcoin tarihi", "borsa nasıl çalışır", "enflasyon nedir",
        "küresel ekonomi", "kripto para", "merkez bankası", "altın neden değerli",
        # Felsefe
        "Platon felsefesi", "Nietzsche düşünceleri", "var oluş felsefesi",
        "etik felsefe", "mantık nedir", "bilinç nedir", "özgür irade",
        # Doğa
        "balinaların zekası", "karınca kolonileri", "ahtapot zekası",
        "göç eden kuşlar", "orkide bitkisi", "yağmur ormanı ekolojisi",
        "deniz altı volkanları", "Aurora Borealis", "kasırga oluşumu",
    ]

    def _delayed_init(self):
        time.sleep(0.5)
        init_ai()
        b = bellek_yukle()
        msg = (f"JARVIS v7.0 Beyin AKTİF! "
               f"Bilinen: {len(b['bilgiler'])} konu | Öğrenilen: {b['ogrenilen_sayisi']} | "
               f"Sohbet: {_SOHBET.get('toplam', 0)}")
        self.root.after(0, lambda: self.log(msg))
        self.root.after(0, lambda: self.chat("sys", msg))
        # Ollama gerçek bağlantı testi
        global _ollama_bagli, _ollama_son_kontrol
        _ollama_bagli = None   # Cache sıfırla, gerçek test yap
        _ollama_son_kontrol = 0
        ollama_bagli = ollama_aktif_mi()
        if ollama_bagli:
            om = f"🤖 Ollama BAĞLI — {OLLAMA_MODEL} — Gerçek AI modu aktif!"
            self.root.after(0, lambda: self.log(om))
            self.root.after(0, lambda: self.chat("sys", om))
            try: self.root.after(0, lambda: self.ollama_lbl.config(fg="#00ff88", text="🤖 Ollama ✓"))
            except: pass
        else:
            om = f"⚫ Ollama kapalı. Çalıştır: ollama pull {OLLAMA_MODEL}"
            self.root.after(0, lambda: self.log(om))
            self.root.after(0, lambda: self.chat("sys", "ℹ️ Ollama yok — Wikipedia/Web ile çalışıyorum."))
            try: self.root.after(0, lambda: self.ollama_lbl.config(fg="#ff4444", text="🔴 Ollama"))
            except: pass
        # Profil selamlama
        import datetime as _dtt
        saat = _dtt.datetime.now().hour
        gun_selam = "Günaydın" if saat < 12 else ("İyi günler" if saat < 18 else "İyi akşamlar")
        oturum_no = KULLANICI.get("oturumlar", 0) + 1
        _profil_guncelle("oturumlar", oturum_no)
        if oturum_no <= 1:
            hosgeldin = f"Merhaba {KULLANICI_ISIM}! Ben JARVIS v7.0. Seninle tanışmak güzel!"
        else:
            hosgeldin = f"{gun_selam} {KULLANICI_ISIM}! Bugün ne yapıyoruz?"
        self.root.after(1000, lambda: self.reply(hosgeldin))
        # Arka plan öğrenme thread'ini başlat
        threading.Thread(target=self._arkaplan_ogren, daemon=True).start()

    def _arkaplan_ogren(self):
        """Her 10 dakikada bir yeni konu araştır ve öğren"""
        self.oto_ogren_aktif = True
        konular = list(self.OTOMATIK_KONULAR)
        random.shuffle(konular)
        konu_idx = 0
        # İlk öğrenme 3 saniye sonra başlasın
        time.sleep(3)
        while self.oto_ogren_aktif:
            try:
                if self.mode == "KAPALI":
                    time.sleep(3)
                    continue
                konu = konular[konu_idx % len(konular)]
                konu_idx += 1
                # Zaten biliyor mu?
                b = bellek_yukle()
                konu_n = _normalize(konu)
                zaten_biliyor = any(konu_n in _normalize(k) for k in b.get("bilgiler", {}))
                if zaten_biliyor:
                    time.sleep(3)
                    continue
                # Öğrenme animasyonu başlat
                self.root.after(0, lambda: self.set_orb("learning"))
                self.root.after(0, lambda k=konu: self.log(f"[Oto-Öğrenme] Araştırıyorum: {k}"))
                # Web'den öğren
                cevap, kaynak = _web_ozet_al(konu)
                if cevap:
                    anahtar = _normalize(konu)[:60]
                    _bellek["bilgiler"][anahtar] = cevap
                    _bellek["kategoriler"][anahtar] = _kategori_tahmin(konu + " " + cevap)
                    _bellek["guvenilirlik"][anahtar] = _guvenilirlik_hesapla(kaynak, cevap)
                    _baglanti_kur(anahtar, cevap)
                    _bellek["ogrenilen_sayisi"] = _bellek.get("ogrenilen_sayisi", 0) + 1
                    bellek_kaydet(_bellek)
                    kat = _bellek["kategoriler"][anahtar]
                    msg = f"🧠 Oto-Öğrendim! [{kat.upper()}] {konu}: {cevap[:80]}..."
                    self.root.after(0, lambda: self.set_orb("learned"))
                    self.root.after(0, lambda m=msg: self.log(m))
                    self.root.after(3000, lambda: self.set_orb("idle"))
                else:
                    self.root.after(0, lambda: self.set_orb("idle"))
                    self.root.after(0, lambda k=konu: self.log(f"[Oto-Öğrenme] Bulunamadı: {k}"))
            except Exception as e:
                self.root.after(0, lambda: self.set_orb("idle"))
            # Her öğrenme arası 3 saniye bekle (sistemi yormamak için)
            time.sleep(3)

    def _do_update(self):
        desc = self.update_entry.get().strip()
        if not desc or desc.startswith("Güncellemek"):
            messagebox.showwarning("JARVIS", "Ne yapmamı istediğini yaz!")
            return
        # Geliştirme modunda değilse uyar
        if self.mode != "KAPALI":
            if not messagebox.askyesno("JARVIS", "Güncelleme için Geliştirme Modu önerilir.\nYine de devam?"):
                return
        # Güncellemeyi analiz et ve kullanıcıya göster
        analiz = self._guncelleme_analiz(desc)
        onay_mesaj = (
            f"📋 GÜNCELLEME ANALİZİ\n\n"
            f"Ne değişecek: {analiz['ne']}\n"
            f"Neden: {analiz['neden']}\n"
            f"Risk: {analiz['risk']}\n\n"
            f"Devam etmek istiyor musun?"
        )
        if messagebox.askyesno("JARVIS — Güncelleme Onayı", onay_mesaj):
            self.chat("sys", f"✅ Onaylandı: {desc}")
            self.set_orb("thinking")
            threading.Thread(target=self._run_update, args=(desc,), daemon=True).start()
        else:
            self.chat("sys", "❌ Güncelleme iptal edildi.")

    def _guncelleme_analiz(self, desc):
        """Güncelleme isteğini analiz et — ne değişecek, neden, risk"""
        d = _normalize(desc)
        analiz = {"ne": "", "neden": "", "risk": "Düşük"}
        if any(w in d for w in ["renk", "mavi", "yesil", "kirmizi", "mor"]):
            analiz["ne"] = "Küre rengi değişecek"
            analiz["neden"] = "Görsel tercih"
            analiz["risk"] = "Çok düşük — sadece renk"
        elif any(w in d for w in ["ses", "ahmet", "era", "pitch"]):
            analiz["ne"] = "Ses ayarları değişecek"
            analiz["neden"] = "Ses tercihi"
            analiz["risk"] = "Düşük"
        elif any(w in d for w in ["versiyon", "version"]):
            analiz["ne"] = "Versiyon numarası güncellenecek"
            analiz["neden"] = "Versiyon takibi"
            analiz["risk"] = "Çok düşük"
        elif any(w in d for w in ["bilgi", "ogren", "ekle"]):
            analiz["ne"] = "Yeni bilgi eklenecek"
            analiz["neden"] = "Bilgi tabanını genişletme"
            analiz["risk"] = "Çok düşük"
        elif any(w in d for w in ["hizlandir", "yavasla"]):
            analiz["ne"] = "Öğrenme hızı değişecek"
            analiz["neden"] = "Performans tercihi"
            analiz["risk"] = "Düşük"
        else:
            analiz["ne"] = f"'{desc[:50]}' değişikliği uygulanacak"
            analiz["neden"] = "Kullanıcı isteği"
            analiz["risk"] = "Orta — kod değişikliği"
        return analiz

    def _run_update(self, desc):
        ok, msg, source = ai_self_update(desc)
        if not ok:
            self.root.after(0, lambda: self.set_orb("error"))
            self.root.after(0, lambda: self.chat("error", msg))
            self.root.after(0, lambda: self.log(f"Güncelleme başarısız: {msg}"))

    def send_text_cmd(self):
        text = self.cmd_entry.get().strip()
        if text:
            self.cmd_entry.delete(0, "end")
            self.cmd_history.append(text)
            self.hist_idx = len(self.cmd_history)
            threading.Thread(target=self.process_command, args=(text,), daemon=True).start()

    def toggle_voice(self):
        if not SR_OK or not SD_OK:
            self.reply("Sesli komut için: pip install sounddevice speechrecognition")
            return
        if self.listening:
            self.listening = False
            self.voice_btn.config(text="🎙  SESLİ KOMUT BAŞLAT", fg="#1a4a6a")
            self.log("Mikrofon kapatıldı.")
        else:
            self.listening = True
            self.voice_btn.config(text="🔴  DİNLENİYOR...  (tıkla durdur)", fg="#00ff88")
            self.log("Mikrofon açıldı.")
            threading.Thread(target=self._listen_loop, daemon=True).start()

    def _listen_loop(self):
        while self.listening:
            try:
                audio_np = record_audio()
                if audio_np is None or np.abs(audio_np).mean() < 50:
                    continue
                audio_data = numpy_to_audio(audio_np)
                if audio_data is None:
                    continue
                text = ""
                for lang in ["tr-TR", "en-US"]:
                    try:
                        text = self.recognizer.recognize_google(audio_data, language=lang).lower()
                        break
                    except sr.UnknownValueError:
                        continue
                    except sr.RequestError:
                        break
                if text:
                    self.root.after(0, lambda t=text: self.log(f"Duyulan: {t}"))
                    self.process_command(text)
            except Exception:
                time.sleep(1)

    def reply(self, text):
        if not text:
            return
        self.root.after(0, lambda: self.set_response(text))
        self.root.after(0, lambda: self.chat("ai", text))
        speak(text)

    def process_command(self, text):
        self.root.after(0, lambda: self.chat("user", text))
        self.log(f"Komut: {text}")
        t = text.lower().strip()
        t_n = _normalize(t)  # Türkçe normalize

        # Mod bazlı davranış kontrolü
        if self.mode == "NORMAL":
            if t_n.startswith("guncelle ") or t_n.startswith("güncelle "):
                self.reply("Sistem degisikligi icin once Gelistirme Moduna gec: 'GELİŞİM' butonuna bas!")
                return

        if t.startswith("öğren:") or t.startswith("ogren:"):
            try:
                parca = text[6:].strip()
                if "=" in parca:
                    s, c = parca.split("=", 1)
                    self.reply(ogret(s.strip(), c.strip()))
                    self.root.after(0, lambda: self.set_orb("learned"))
                    self.root.after(2500, lambda: self.set_orb("idle"))
                else:
                    self.reply("Format: öğren: soru = cevap")
            except:
                self.reply("Format: öğren: soru = cevap")
            return

        if any(w in t for w in ["ne kadar biliyorsun", "kac sey ogrend", "istatistik", "ne biliyorsun", "bilgi tabanı"]):
            b = bellek_yukle()
            # Kategori dağılımı
            kat_say = {}
            for kat in b.get("kategoriler", {}).values():
                kat_say[kat] = kat_say.get(kat, 0) + 1
            kat_str = " | ".join([f"{k}:{v}" for k,v in sorted(kat_say.items(), key=lambda x:-x[1])[:4]])
            # Ortalama güvenilirlik
            guvenir_list = list(b.get("guvenilirlik", {}).values())
            ort_guv = int(sum(guvenir_list)/len(guvenir_list)) if guvenir_list else 0
            # Kullanıcının öğrettikleri
            kullanici_say = len(b.get("kullanici_bilgileri", {}))
            son_kaynak = b["arastirma_gecmisi"][-1]["kaynak"] if b.get("arastirma_gecmisi") else "Henüz yok"
            self.reply(
                f"🧠 Bilgi Tabanı Raporu:\n"
                f"📚 Toplam konu: {len(b['bilgiler'])} | "
                f"👤 Sen öğrettin: {kullanici_say} | "
                f"🌐 Araştırdım: {b['ogrenilen_sayisi']}\n"
                f"📂 Kategoriler: {kat_str}\n"
                f"⭐ Ort. güvenilirlik: %{ort_guv} | "
                f"🔗 Bağlantılar: {len(b.get('baglantilar', {}))} | "
                f"Son kaynak: {son_kaynak}"
            )
            return

        if any(w in t for w in ["hey jarvis", "jarvis uyan", "ajan mod"]):
            self.root.after(0, lambda: self.set_mode("AJAN"))
            self.reply("Ajan modu aktif! Gözetimli yardımcı modundayım. Ne yapalım?")
            return
        if any(w in t_n for w in ["sessiz mod", "kod modu", "gelistirme modu"]):
            self.root.after(0, lambda: self.set_mode("SESSIZ")); return
        if any(w in t_n for w in ["normal mod", "normal moda gec", "sohbet modu"]):
            self.root.after(0, lambda: self.set_mode("NORMAL")); return
        if any(w in t_n for w in ["ogrenme modu", "gelisim modu", "kapali mod", "guncelleme modu"]):
            self.root.after(0, lambda: self.set_mode("KAPALI")); return

        if t.startswith("güncelle ") or t.startswith("update "):
            desc = text[9:] if t.startswith("güncelle ") else text[7:]
            self.root.after(0, lambda: self.set_orb("thinking"))
            self.root.after(0, lambda: self.chat("sys", f"Güncelleniyor: {desc}"))
            threading.Thread(target=self._run_update, args=(desc,), daemon=True).start()
            return

        if t.startswith("google ") or t.startswith("ara "):
            query = re.sub(r"^(google|ara)\s+", "", t).strip()
            self.reply(web_search(query)); return

        # Şarkı sözü ara
        if any(w in t_n for w in ["sozleri", "sozu", "sarkinin sozu", "lyrics", "soz ara"]):
            sarki = re.sub(r"(sozleri|sozu|sarkinin sozu|lyrics|soz ara)", "", t).strip()
            if sarki:
                q = urllib.parse.quote(sarki + " sözleri")
                webbrowser.open(f"https://www.google.com/search?q={q}")
                webbrowser.open(f"https://genius.com/search?q={urllib.parse.quote(sarki)}")
                self.reply(f"🎵 '{sarki}' sözleri için Genius ve Google açıldı!")
            return

        # Çeviri komutu
        if any(w in t_n for w in ["cevir", "ingilizce", "turkce cevir", "translate"]):
            kelime = re.sub(r"(cevir|ingilizce|turkce cevir|translate|turkceye|ingilizceye)", "", t).strip()
            if kelime:
                q = urllib.parse.quote(f"{kelime} çeviri")
                webbrowser.open(f"https://translate.google.com/?sl=auto&tl=tr&text={urllib.parse.quote(kelime)}")
                self.reply(f"🌍 '{kelime}' için Google Çeviri açıldı!")
            return

        # Gelişmiş hesap makinesi
        if any(w in t_n for w in ["hesapla", "kac eder", "carpim", "toplam", "karekoku", "faktoryel"]):
            try:
                sayi_bul = re.findall(r"[\d.]+", t)
                if "karekoku" in t_n and sayi_bul:
                    s = float(sayi_bul[0])
                    self.reply(f"√{s} = {s**0.5:.4f}"); return
                if "faktoryel" in t_n and sayi_bul:
                    n = int(float(sayi_bul[0]))
                    import math as _math
                    self.reply(f"{n}! = {_math.factorial(min(n,20))}"); return
                if "yuzde" in t_n or "%" in t:
                    sayilar = re.findall(r"[\d.]+", t)
                    if len(sayilar) >= 2:
                        yuzde, taban = float(sayilar[0]), float(sayilar[1])
                        self.reply(f"%{yuzde} × {taban} = {yuzde*taban/100:.2f}"); return
            except: pass

        # Hatırlatıcı
        if any(w in t_n for w in ["hatirlat", "hatirlatici", "remind"]):
            sure_bul = re.search(r"(\d+)\s*(dakika|saat|saniye)", t)
            mesaj_bul = re.sub(r"hatirlat.*?(\d+\s*(dakika|saat|saniye))", "", t).strip()
            if sure_bul:
                miktar = int(sure_bul.group(1))
                birim = sure_bul.group(2)
                saniye = miktar * (60 if "dakika" in birim else 3600 if "saat" in birim else 1)
                mesaj = mesaj_bul if mesaj_bul else "Hatırlatıcı!"
                self.reply(f"⏰ {miktar} {birim} sonra hatırlatacağım: '{mesaj}'")
                def _hatirlat():
                    time.sleep(saniye)
                    speak(f"Hatırlatıcı! {mesaj}")
                    self.root.after(0, lambda: self.reply(f"🔔 HATIRLATICI: {mesaj}"))
                threading.Thread(target=_hatirlat, daemon=True).start()
                return

        # Sohbet özeti
        if any(w in t_n for w in ["ne konustuk", "gecmis", "ozet", "bugun ne sorduk"]):
            b = bellek_yukle()
            gecmis = b.get("konusma_gecmisi", [])[-10:]
            if gecmis:
                sorular = [g["soru"][:40] for g in gecmis]
                self.reply(f"📝 Son {len(sorular)} konuşma:\n" + "\n".join(f"• {s}" for s in sorular))
            else:
                self.reply("Henüz konuşma geçmişi yok.")
            return

        # Hava durumu gelişmiş
        if any(w in t_n for w in ["hava durumu", "hava nasil", "sicaklik"]):
            sehir = re.sub(r"(hava durumu|hava nasil|sicaklik|hava)", "", t).strip()
            if not sehir:
                sehir = "Istanbul"
            q = urllib.parse.quote(f"{sehir} hava durumu")
            webbrowser.open(f"https://www.google.com/search?q={q}")
            self.reply(f"🌤 {sehir} hava durumu Google'da açıldı!"); return

        # Wikipedia komutu
        if any(w in t_n for w in ["wikipedia", "vikipedi", "ansiklopedi"]):
            konu = re.sub(r"(wikipedia|vikipedi|ansiklopedi)", "", t).strip()
            if konu:
                webbrowser.open(f"https://tr.wikipedia.org/wiki/{urllib.parse.quote(konu)}")
                self.reply(f"📖 Wikipedia'da '{konu}' açıldı!")
            return

        if "indir " in t and self.mode in ("SESSIZ", "AJAN", "KAPALI"):
            pkg = t.replace("indir ", "").strip()
            self.root.after(0, lambda: self.set_orb("thinking"))
            result = download_package(pkg)
            self.root.after(0, lambda: self.set_orb("idle"))
            self.reply(result); return

        # ── SESSİZ MOD: Kod yazma ─────────────────────────────
        if self.mode == "SESSIZ" and any(w in t_n for w in ["kod yaz", "yaz bana", "script yaz", "fonksiyon yaz", "program yaz"]):
            konu = re.sub(r"(kod yaz|yaz bana|script yaz|fonksiyon yaz|program yaz)[:\s]*", "", t_n).strip()
            self.root.after(0, lambda: self.set_orb("thinking"))
            def _kod_yaz():
                # Önce web'den araştır
                arastirma, _ = _web_ozet_al(konu + " python code example")
                if not arastirma:
                    arastirma, _ = _web_ozet_al(konu + " python")
                # Ollama varsa gerçek kod yaz
                if ollama_aktif_mi():
                    prompt = f"Python ile '{konu}' için kısa, çalışan bir kod yaz. Sadece kod ve kısa açıklama ver."
                    cevap = _ollama_sor(prompt, [])
                    if cevap:
                        self.root.after(0, lambda: self.set_orb("learned"))
                        msg = "💻 [" + konu + "] için kod:\n\n" + cevap
                        self.root.after(0, lambda m=msg: self.reply(m))
                        self.root.after(2000, lambda: self.set_orb("idle"))
                        return
                # Ollama yoksa temel şablon
                sablonlar = {
                    "hesap": "Hesap makinesi icin: def hesap(a,b,op): return eval(str(a)+op+str(b))",
                    "liste": "Liste icin: liste=[]; liste.append('eleman'); print(liste)",
                    "dosya": "Dosya icin: open('dosya.txt','w').write('Merhaba!')",
                }
                for k, v in sablonlar.items():
                    if k in konu:
                        msg2 = "Temel sablon: " + v
                        self.root.after(0, lambda m=msg2: self.reply(m))
                        self.root.after(0, lambda: self.set_orb("idle"))
                        return
                msg3 = "Kod yazamiyorum — Ollama kur: ollama pull gemma:2b"
                self.root.after(0, lambda m=msg3: self.reply(m))
            threading.Thread(target=_kod_yaz, daemon=True).start()
            return

        # ── AJAN MOD: Görev planlama ──────────────────────────
        if self.mode == "AJAN" and any(w in t_n for w in ["gorev", "plan yap", "adim adim", "proje", "hedef"]):
            konu = re.sub(r"(gorev|plan yap|adim adim|proje|hedef)[:\s]*", "", t_n).strip()
            def _plan_yap():
                self.root.after(0, lambda: self.set_orb("thinking"))
                self.root.after(0, lambda: self.chat("sys", f"📋 Görev analiz ediliyor: {konu}"))
                if ollama_aktif_mi():
                    prompt = f"'{konu}' görevi için adım adım plan yap. Her adımı numaralandır. Kısa ve net olsun."
                    cevap = _ollama_sor(prompt, [])
                    if cevap:
                        plan_msg = "GOREV PLANI - " + konu + ": " + cevap
                        self.root.after(0, lambda m=plan_msg: self.reply(m))
                        self.root.after(0, lambda: self.set_orb("idle"))
                        return
                # Basit plan şablonu
                # Basit plan sablonu
                plan = ("GOREV PLANI - " + konu + ":\n"
                       "1. Konuyu arastir\n"
                       "2. Gerekli kaynaklari topla\n"
                       "3. Adim adim uygula\n"
                       "4. Test et ve dogrula\n"
                       "5. Sonucu raporla\n"
                       "Hangi adimdan baslayalim?")
                self.root.after(0, lambda: self.reply(plan))
            return

        app_cmds = {
            ("chrome", "tarayıcı", "browser"): ("start chrome", "Chrome açıldı."),
            ("spotify",): ("start spotify:", "Spotify açıldı."),
            ("discord",): ("start discord:", "Discord açıldı."),
        }
        for keys, (cmd, msg) in app_cmds.items():
            if any(k in t for k in keys):
                subprocess.Popen(cmd, shell=True); self.reply(msg); return

        web_cmds = {
            ("youtube",):          "https://youtube.com",
            ("instagram",):        "https://instagram.com",
            ("twitter", "x.com"): "https://x.com",
            ("gmail", "mail"):     "https://mail.google.com",
            ("whatsapp",):         "https://web.whatsapp.com",
            ("hava",):             "https://weather.com",
            ("netflix",):          "https://netflix.com",
            ("twitch",):           "https://twitch.tv",
            ("github",):           "https://github.com",
            ("chatgpt",):          "https://chat.openai.com",
            ("minecraft",):        "https://minecraft.net",
        }

        # Minecraft uygulaması olarak aç
        if "minecraft" in t_n and any(w in t_n for w in ["ac", "baslat", "oyna", "gir"]):
            subprocess.Popen("start minecraft:", shell=True)
            self.reply("⛏️ Minecraft başlatılıyor! Biraz bekle."); return
        for keys, url in web_cmds.items():
            if any(k in t for k in keys):
                webbrowser.open(url); self.reply(f"✅ {url} açıldı."); return

        system_cmds = {
            ("notepad", "not defteri"):           ["notepad.exe"],
            ("hesap", "calculator"):              ["calc.exe"],
            ("dosya", "explorer"):                ["explorer.exe"],
            ("görev yöneticisi", "task manager"): ["taskmgr.exe"],
            ("ekran görüntüsü", "screenshot"):    ["snippingtool"],
        }
        for keys, cmd in system_cmds.items():
            if any(k in t for k in keys):
                subprocess.Popen(cmd); self.reply(f"✅ {cmd[0]} açıldı."); return

        ps_key = lambda k: ["powershell", "-Command",
                             f"$wsh=New-Object -ComObject WScript.Shell;$wsh.SendKeys([char]{k})"]
        if "ses artır" in t or "sesi artır" in t:
            for _ in range(5): subprocess.run(ps_key(175), capture_output=True)
            self.reply("🔊 Ses artırıldı."); return
        if "ses azalt" in t or "sesi azalt" in t:
            for _ in range(5): subprocess.run(ps_key(174), capture_output=True)
            self.reply("🔉 Ses azaltıldı."); return
        if "sessiz" in t and "mod" not in t:
            subprocess.run(ps_key(173), capture_output=True); self.reply("🔇 Sessiz."); return
        if "sonraki" in t:
            subprocess.run(ps_key(176), capture_output=True); self.reply("⏭ Sonraki şarkı."); return
        if "önceki" in t:
            subprocess.run(ps_key(177), capture_output=True); self.reply("⏮ Önceki şarkı."); return

        if "alarm" in t:
            mins = 5
            for w in t.split():
                if w.isdigit(): mins = int(w); break
            self.reply(f"⏰ {mins} dakika sonra alarm kuruldu.")
            def _alarm():
                time.sleep(mins * 60)
                speak(f"Alarm! {mins} dakika doldu!")
                self.root.after(0, lambda: self.set_response(f"⏰ ALARM! {mins} dakika doldu!"))
            threading.Thread(target=_alarm, daemon=True).start()
            return

        if "bilgisayarı kapat" in t:
            self.reply("⚠️ 30 saniye sonra kapanıyor!"); subprocess.run(["shutdown", "/s", "/t", "30"]); return
        if "yeniden başlat" in t or "restart" in t:
            self.reply("🔄 Yeniden başlatılıyor."); subprocess.run(["shutdown", "/r", "/t", "30"]); return
        if "ekranı kilitle" in t or "kilitle" in t:
            self.reply("🔒 Ekran kilitleniyor."); subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"]); return
        if "iptal" in t:
            subprocess.run(["shutdown", "/a"], capture_output=True); self.reply("✅ Kapatma iptal edildi."); return

        if "temizle" in t:
            self.chat_area.config(state="normal")
            self.chat_area.delete("1.0", "end")
            self.chat_area.config(state="disabled")
            self.reply("🧹 Temizlendi."); return

        # ── Yeni Skill öğret (OpenJarvis ilhamlı dosya tabanlı yetenek) ──
        if t_n.startswith("skill ogret") or t_n.startswith("yetenek ogret"):
            try:
                icerik = t.split(":", 1)[1].strip()
                tetik_str, cevap_str = icerik.split("=", 1)
                tetikleyiciler = [x.strip() for x in tetik_str.split(",") if x.strip()]
                cevap_str = cevap_str.strip()
                if not tetikleyiciler or not cevap_str:
                    self.reply("Format: skill öğret: tetik1, tetik2 = cevap")
                    return
                skill_id = f"skill_{len(_SKILLS)+1}_{int(time.time())}"
                skill_veri = {
                    "tetikleyiciler": tetikleyiciler,
                    "cevap": cevap_str,
                    "kategori": "kullanici_skill",
                    "olusturma": datetime.datetime.now().isoformat()
                }
                yol = os.path.join(SKILLS_DIZINI, f"{skill_id}.json")
                if _guvenli_json_yaz(yol, skill_veri):
                    _SKILLS.append(skill_veri)
                    self.reply(f"🧩 Yeni skill öğrendim! '{tetikleyiciler[0]}' dediğinde artık '{cevap_str[:50]}' diyeceğim.")
                else:
                    self.reply("Skill kaydedilemedi, bir sorun oluştu.")
            except Exception as e:
                self.reply(f"Format hatası: skill öğret: tetik1, tetik2 = cevap  ({e})")
            return

        # Skill listesi
        if any(w in t_n for w in ["skillerini goster", "yeteneklerini goster", "skill listesi"]):
            if _SKILLS:
                liste = ", ".join(s["tetikleyiciler"][0] for s in _SKILLS[:10])
                self.reply(f"🧩 {len(_SKILLS)} özel yeteneğim var: {liste}")
            else:
                self.reply("Henüz özel bir skill öğrenmedim. 'skill öğret: tetik = cevap' ile öğretebilirsin!")
            return

        # Kendini geliştirme analizi
        if any(w in t_n for w in ["kendini gelistir", "eksiklerini", "gelistirme onerisi", "ne yapmalısın"]):
            self.root.after(0, lambda: self.set_orb("thinking"))
            oneriler = _gelistirme_analiz()
            if oneriler:
                satirlar = ["🔧 Kendimi analiz ettim, işte önerilerim:"]
                for i, o in enumerate(oneriler, 1):
                    satirlar.append(f"{i}. [{o['oncelik'].upper()}] {o['oneri']}")
                satirlar.append("Bu önerileri uygulamak ister misin?")
                metin = " | ".join(satirlar)
            else:
                metin = "✅ Analiz tamamlandı! Şu an iyi durumdayım."
            self.root.after(0, lambda: self.set_orb("idle"))
            self.reply(metin); return

        # Profil göster / güncelle
        if any(w in t_n for w in ["profilim", "beni tan", "beni biliyor musun"]):
            p = KULLANICI
            metin = (f"👤 {p.get('isim','?')} — "
                     f"🎮 {p.get('favori_oyun','?')} — "
                     f"🎨 {p.get('favori_renk','?')} — "
                     f"💬 {_SOHBET.get('toplam',0)} sohbet")
            self.reply(metin); return

        # ── Ollama / AI durumu ────────────────────────────────
        if any(w in t_n for w in ["ollama", "ai durumu", "ai aktif mi", "yapay zeka durumu", "ollama kurulu mu", "ollama test"]):
            def _test_ollama():
                self.root.after(0, lambda: self.set_orb("thinking"))
                global _ollama_bagli, _ollama_son_kontrol
                _ollama_bagli = None  # cache sıfırla — gerçek test yap
                _ollama_son_kontrol = 0
                bagli = ollama_aktif_mi()
                if bagli:
                    test = _ollama_sor("Merhaba! Tek cümleyle kendini tanıt.", [])
                    if test:
                        msg = f"🤖 Ollama GERÇEKTEN BAĞLI! Model: {OLLAMA_MODEL} | Cevap: {test[:80]}"
                        try: self.root.after(0, lambda: self.ollama_lbl.config(fg="#00ff88", text="🤖 Ollama ✓"))
                        except: pass
                    else:
                        msg = f"⚠️ Ollama bağlı (model: {OLLAMA_MODEL}) ama cevap gelmedi. 'ollama serve' çalışıyor mu kontrol et."
                else:
                    msg = f"⚫ Ollama KAPALI/Bağlantı yok. Kontrol et: 1) 'ollama serve' çalışıyor mu  2) 'ollama pull {OLLAMA_MODEL}' yapıldı mı"
                    try: self.root.after(0, lambda: self.ollama_lbl.config(fg="#ff4444", text="🔴 Ollama"))
                    except: pass
                self.root.after(0, lambda: self.set_orb("idle"))
                self.root.after(0, lambda: self.reply(msg))
            threading.Thread(target=_test_ollama, daemon=True).start()
            return

        # ── Kim olduğunu sor ──────────────────────────────────
        if any(w in t_n for w in ["benim ismim ne", "ben kim", "beni tanıyor musun", "adim ne", "benim adim ne"]):
            p = KULLANICI
            self.reply(f"Tabii tanıyorum! Adın {p.get('isim','?')}, favori oyunun {p.get('favori_oyun','?')}, favori rengin {p.get('favori_renk','?')}. Seninle {_SOHBET.get('toplam',0)} kez konuştuk!")
            return

        # ── İsim güncelle ─────────────────────────────────────
        if any(w in t_n for w in ["adimi kaydet", "ismimi degistir", "adim degistir"]):
            yeni_isim = re.sub(r"(adimi kaydet|ismimi degistir|adim degistir)[:\s]*", "", t_n).strip().capitalize()
            if yeni_isim and len(yeni_isim) > 1:
                _profil_guncelle("isim", yeni_isim)
                self.reply(f"✅ Adını '{yeni_isim}' olarak kaydettim!")
            else:
                self.reply("Nasıl kaydedeyim? Örnek: 'adımı kaydet Mehmet'")
            return

        # ── Sohbet istatistik ──────────────────────────────────
        if any(w in t_n for w in ["kac kez konustuk", "kac sohbet", "sohbet gecmisi"]):
            self.reply(f"💬 Şimdiye kadar {_SOHBET.get('toplam',0)} kez konuştuk! Son {len(_SOHBET.get('gecmis',[]))} mesajı hatırlıyorum.")
            return

        # ── Kendini geliştir önerisi uygula ───────────────────
        if any(w in t_n for w in ["onerileri uygula", "gelistirmeyi uygula", "evet uygula"]):
            oneriler = _gelistirme_analiz()
            if oneriler:
                for o in oneriler:
                    if "oto-ogren" in o.get("oneri","").lower() or "ogrenme" in o.get("kategori","").lower():
                        if not self.oto_ogren_aktif:
                            self.oto_ogren_aktif = True
                            threading.Thread(target=self._arkaplan_ogren, daemon=True).start()
                self.reply("✅ Öneriler uygulandı! Arka plan öğrenmesi hızlandırıldı.")
            else:
                self.reply("Uygulanacak öneri yok, zaten iyi durumdayım!")
            return

        if any(w in t_n for w in ["oto ogren", "otomatik ogren", "kendi kendine ogren", "arka plan ogren", "arka plan"]):
            if any(w in t_n for w in ["kapat", "dur", "durdur", "durdur"]):
                self.oto_ogren_aktif = False
                self.reply("⏹ Arka plan öğrenmesi durduruldu.")
            else:
                self.oto_ogren_aktif = True
                threading.Thread(target=self._arkaplan_ogren, daemon=True).start()
                self.reply("▶ Arka plan öğrenmesi başlatıldı! Her 10 dakikada yeni konu öğreneceğim.")
            return

        self.root.after(0, lambda: self.set_orb("thinking"))
        self.root.after(0, lambda: self.reply("🧠 Düşünüyorum..."))

        def _ask():
            self.root.after(0, lambda: self.set_orb("learning"))
            answer, source = _ask_ai_ve_kaydet(text)
            ikon_map = {
                "JARVIS-Mantık": "⚡", "JARVIS-Bellek": "💾",
                "Wikipedia TR": "📖", "Wikipedia EN": "📖",
                "DuckDuckGo": "🌐", "JARVIS-Öğreniyor": "❓",
                "JARVIS-Bağlam": "🔗", "Ollama-AI": "🤖", "JARVIS-Soru": "🤔", "JARVIS-Analiz": "🧐", "JARVIS-Plan": "📋", "JARVIS-Tahmin": "💡", "JARVIS-Skill": "🧩",
            }
            ikon = ikon_map.get(source, "🤖")
            yeni_ogrendi = source in ("Wikipedia TR", "Wikipedia EN", "DuckDuckGo")
            if yeni_ogrendi:
                # Turuncu → Yeşil → Mavi animasyon sırası
                self.root.after(0, lambda: self.set_orb("learned"))
                self.root.after(2500, lambda: self.set_orb("idle"))
            else:
                self.root.after(0, lambda: self.set_orb("idle"))
            self.root.after(0, lambda: self.reply(f"{ikon} {answer}"))
            self.log(f"[{source}] {answer[:60]}...")
            speak(answer)

        threading.Thread(target=_ask, daemon=True).start()

    def run(self):
        self.oto_ogren_aktif = True
        self.root.mainloop()
        self.oto_ogren_aktif = False
        if hasattr(self, "orb"):
            self.orb.stop()


if __name__ == "__main__":
    print("=" * 55)
    print("  J.A.R.V.I.S  v7.2  —  Güçlendirilmiş Beyin")
    print("  Bellek + Mantık + DuckDuckGo + Wikipedia")
    print("=" * 55)
    app = JarvisApp()
    app.run()
