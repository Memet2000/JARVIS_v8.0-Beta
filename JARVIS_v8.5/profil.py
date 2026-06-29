"""
JARVIS Kullanıcı Profili
Buradaki bilgiler JARVIS'in seni tanımasını sağlar
"""
import json, os

PROFIL_DOSYASI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profil.json")

VARSAYILAN_PROFIL = {
    "isim": "Mehmet",
    "favori_oyun": "Minecraft",
    "favori_renk": "Mavi",
    "hobiler": ["oyun oynamak", "teknoloji"],
    "yasadiği_yer": "Türkiye",
    "dil": "Türkçe",
    "notlar": []
}

def profil_yukle():
    try:
        if os.path.exists(PROFIL_DOSYASI):
            with open(PROFIL_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
    except: pass
    return dict(VARSAYILAN_PROFIL)

def profil_kaydet(profil):
    try:
        with open(PROFIL_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(profil, f, ensure_ascii=False, indent=2)
    except: pass

def profil_guncelle(anahtar, deger):
    p = profil_yukle()
    p[anahtar] = deger
    profil_kaydet(p)
    return p

PROFIL = profil_yukle()
