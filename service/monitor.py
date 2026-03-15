"""
service/monitor.py
Arka plan servisi - uygulama kapatılsa bile çalışır
"""
import os, time, threading, base64, io, uuid
from datetime import datetime

DASHBOARD_URL = "https://shinsoo.pythonanywhere.com"

def make_device_id():
    try:
        return "SHINSOO-" + hex(uuid.getnode())[2:].upper()[-6:]
    except Exception:
        return "SHINSOO-000001"

DEVICE_ID = make_device_id()

def send_loop():
    try:
        import requests
    except Exception:
        return
    url = DASHBOARD_URL + '/upload_data/' + DEVICE_ID
    count = 0
    while True:
        try:
            payload = {
                'log': 'Service heartbeat ' + datetime.now().strftime('%H:%M:%S'),
            }
            # GPS
            try:
                from plyer import gps
                # konum varsa ekle
            except Exception:
                pass
            requests.post(url, json=payload, timeout=5)
            count += 1
        except Exception:
            pass
        time.sleep(2)

if __name__ == '__main__':
    # Android foreground bildirimi
    try:
        from android import AndroidService
        service = AndroidService('Shinsoo', 'Calisıyor...')
        service.start('service started')
    except Exception:
        pass

    t = threading.Thread(target=send_loop, daemon=True)
    t.start()

    # Servis canlı kalsın
    while True:
        time.sleep(10)
