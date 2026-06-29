"""
JARVIS Konuşma Motoru
Daha doğal ve akıllı konuşma kalıpları
"""
import random

# Kullanıcı adına göre hitap
def hitap(isim=""):
    if isim:
        return random.choice([
            f"{isim}",
            f"Efendim",
            f"{isim} Bey" if isim else "Efendim",
        ])
    return random.choice(["Efendim", "Buyurun", ""])

# Onay cümleleri
ONAY = [
    "Tabii!", "Elbette!", "Hemen bakıyorum!", "Anlaşıldı!",
    "Olur!", "Tamam!", "Hemen halledelim!"
]

# Bilmeme ifadeleri  
BILMIYORUM = [
    "Bu konuda bilgim yok ama araştırabilirim.",
    "Henüz öğrenemedim bunu.",
    "Bilmiyorum ama öğrenmek isterim!",
    "Bu konuda araştırma yapayım.",
]

# Düşünme ifadeleri
DUSUNUYOR = [
    "Düşünüyorum...",
    "Araştırıyorum...",
    "Bir saniye...",
    "Bakıyorum...",
]

# Selamlama
def selamla(isim="", saat=None):
    if saat is None:
        import datetime
        saat = datetime.datetime.now().hour
    
    if saat < 12:
        baslangic = "Günaydın"
    elif saat < 18:
        baslangic = "İyi günler"
    else:
        baslangic = "İyi akşamlar"
    
    if isim:
        return f"{baslangic} {isim}! Nasıl yardımcı olabilirim?"
    return f"{baslangic}! Nasıl yardımcı olabilirim?"

def onay_cumlesi():
    return random.choice(ONAY)

def bilmiyorum_cumlesi():
    return random.choice(BILMIYORUM)

def dusunuyor_cumlesi():
    return random.choice(DUSUNUYOR)

# Cevabı güzelleştir
def guzellestir(cevap, isim=""):
    """Cevabın başına veya sonuna doğal eklemeler yap"""
    if len(cevap) > 200:
        return cevap  # Uzun cevaplara dokunma
    
    # Kısa cevaplara hitap ekle
    if isim and random.random() < 0.3:
        return f"{cevap}"
    return cevap
