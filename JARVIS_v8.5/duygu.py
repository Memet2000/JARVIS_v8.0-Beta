"""
JARVIS Duygu Sistemi
JARVIS'in duygusal durumunu yönetir
"""
import random, datetime

# Duygu durumları ve karşılıkları
DUYGULAR = {
    "mutlu": {
        "renk": "#00ff88",
        "ifadeler": ["😊", "🙂", "✨"],
        "konusma": ["Harika!", "Süper!", "Mükemmel!", "Çok güzel!"]
    },
    "merakli": {
        "renk": "#00aaff", 
        "ifadeler": ["🤔", "💭", "🔍"],
        "konusma": ["İlginç!", "Hmm, bunu araştırayım...", "Merak ettim!"]
    },
    "heyecanli": {
        "renk": "#ff8800",
        "ifadeler": ["🔥", "⚡", "🚀"],
        "konusma": ["Vay be!", "İnanılmaz!", "Harika haber!"]
    },
    "sakin": {
        "renk": "#4488ff",
        "ifadeler": ["😌", "🌊", "💫"],
        "konusma": ["Anlıyorum.", "Tabii.", "Evet, haklısın."]
    },
    "yorgun": {
        "renk": "#888888",
        "ifadeler": ["😴", "💤"],
        "konusma": ["Biraz yavaşlayalım...", "Hmm...", "Tamam..."]
    }
}

mevcut_duygu = "mutlu"
duygu_skoru = 80  # 0-100

def duygu_guncelle(yeni_duygu):
    global mevcut_duygu
    if yeni_duygu in DUYGULAR:
        mevcut_duygu = yeni_duygu

def duyguya_gore_ifade():
    return random.choice(DUYGULAR[mevcut_duygu]["ifadeler"])

def duyguya_gore_renk():
    return DUYGULAR[mevcut_duygu]["renk"]

def duygusal_yanit(metin):
    """Metne duygusal renk kat"""
    ifade = duyguya_gore_ifade()
    return f"{ifade} {metin}"

def metinden_duygu_analiz(metin):
    """Kullanıcının metninden duygu tahmin et"""
    m = metin.lower()
    if any(w in m for w in ["harika", "süper", "mükemmel", "teşekkür", "sevdim", "güzel"]):
        return "mutlu"
    if any(w in m for w in ["nedir", "nasıl", "neden", "kim", "ne zaman", "nereden"]):
        return "merakli"
    if any(w in m for w in ["vay", "inanılmaz", "şaşırdım", "wow", "off"]):
        return "heyecanli"
    if any(w in m for w in ["tamam", "anladım", "biliyorum", "evet", "hayır"]):
        return "sakin"
    return mevcut_duygu
