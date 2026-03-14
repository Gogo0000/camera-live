import os
os.environ['KIVY_NO_ENV_CONFIG'] = '1'

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform
from kivy.core.window import Window
from kivy.animation import Animation
from datetime import datetime
import threading

KIOSK_PASSWORD = "gokhan"
DASHBOARD_URL  = "https://shinsoo.pythonanywhere.com"

COLOR_BG       = (0.05, 0.05, 0.07, 1)
COLOR_PANEL    = (0.10, 0.10, 0.13, 1)
COLOR_RED      = (0.85, 0.10, 0.10, 1)
COLOR_RED_DARK = (0.55, 0.05, 0.05, 1)
COLOR_TEXT     = (0.95, 0.95, 0.95, 1)
COLOR_TEXT_DIM = (0.55, 0.55, 0.60, 1)
COLOR_GREEN    = (0.10, 0.85, 0.40, 1)
COLOR_YELLOW   = (1.00, 0.80, 0.10, 1)
COLOR_BORDER   = (0.25, 0.05, 0.05, 1)


class DarkCard(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*COLOR_PANEL)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
            Color(*COLOR_BORDER)
            self._border = Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, dp(8)),
                width=1.2)
        self.bind(pos=self._update, size=self._update)

    def _update(self, *_):
        self._bg.pos  = self.pos
        self._bg.size = self.size
        self._border.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(8))


class RedButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0, 0, 0, 0)
        self.color            = COLOR_TEXT
        self.font_size        = dp(13)
        self.bold             = True
        with self.canvas.before:
            Color(*COLOR_RED_DARK)
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(6)])
            Color(*COLOR_RED)
            self._border = Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, dp(6)),
                width=1.5)
        self.bind(pos=self._upd, size=self._upd)

    def _upd(self, *_):
        self._bg.pos  = self.pos
        self._bg.size = self.size
        self._border.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(6))


class DashboardScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._sender_connected = False
        self._device_id = self._make_device_id()
        self._build_ui()
        Clock.schedule_interval(self._tick, 1)
        Clock.schedule_interval(self._update_conn, 3)

    def _make_device_id(self):
        try:
            import uuid
            return "DEV-" + hex(uuid.getnode())[2:].upper()[-6:]
        except Exception:
            return "DEV-000001"

    def _build_ui(self):
        root = FloatLayout()
        with root.canvas.before:
            Color(*COLOR_BG)
            self._bg_rect = Rectangle(pos=root.pos, size=root.size)
        root.bind(
            pos=lambda *_: setattr(self._bg_rect, 'pos', root.pos),
            size=lambda *_: setattr(self._bg_rect, 'size', root.size))

        main = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(8))
        main.add_widget(self._build_header())
        main.add_widget(self._build_status_row())
        main.add_widget(self._build_conn_bar())
        main.add_widget(self._build_info())
        main.add_widget(self._build_log())
        main.add_widget(self._build_footer())

        root.add_widget(main)
        self.add_widget(root)

    def _build_header(self):
        box = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        with box.canvas.before:
            Color(*COLOR_RED_DARK)
            self._hdr = Rectangle(pos=box.pos, size=box.size)
        box.bind(
            pos=lambda *_: setattr(self._hdr, 'pos', box.pos),
            size=lambda *_: setattr(self._hdr, 'size', box.size))

        title_box = BoxLayout(spacing=dp(8))
        title_box.add_widget(Label(text='S', font_size=dp(24),
                                   size_hint_x=None, width=dp(36), color=COLOR_RED))
        lbl = Label(text='[b]SHINSOO PANEL[/b]', markup=True,
                    font_size=dp(14), color=COLOR_TEXT,
                    halign='left', valign='middle')
        lbl.bind(size=lbl.setter('text_size'))
        title_box.add_widget(lbl)

        self.lbl_time = Label(text='--:--:--', font_size=dp(13),
                              color=COLOR_TEXT_DIM, size_hint_x=None,
                              width=dp(80), halign='right')
        self.lbl_time.bind(size=self.lbl_time.setter('text_size'))

        box.add_widget(title_box)
        box.add_widget(self.lbl_time)
        return box

    def _build_status_row(self):
        grid = GridLayout(cols=3, size_hint_y=None, height=dp(70), spacing=dp(6))
        self.status_cards = {}
        items = [
            ('CAM',  'Aktif',   COLOR_GREEN),
            ('MIC',  'Aktif',   COLOR_GREEN),
            ('LOCK', 'Kilitli', COLOR_RED),
        ]
        for title, status, color in items:
            card  = DarkCard()
            inner = BoxLayout(orientation='vertical', padding=dp(6))
            inner.add_widget(Label(text=title, font_size=dp(10),
                                   color=COLOR_TEXT_DIM, bold=True))
            lbl = Label(text=status, font_size=dp(12), color=color, bold=True)
            inner.add_widget(lbl)
            card.add_widget(inner)
            self.status_cards[title] = lbl
            grid.add_widget(card)
        return grid

    def _build_conn_bar(self):
        card = DarkCard(size_hint_y=None, height=dp(32))
        inner = BoxLayout(padding=dp(6), spacing=dp(6))
        inner.add_widget(Label(text='NET:', font_size=dp(10), color=COLOR_TEXT_DIM,
                               size_hint_x=None, width=dp(36)))
        self.lbl_conn = Label(text='Baglaniyor...', font_size=dp(10),
                              color=COLOR_YELLOW, halign='left')
        self.lbl_conn.bind(size=self.lbl_conn.setter('text_size'))
        self.lbl_devid = Label(text='ID: ' + self._device_id, font_size=dp(9),
                               color=COLOR_TEXT_DIM, halign='right',
                               size_hint_x=None, width=dp(120))
        inner.add_widget(self.lbl_conn)
        inner.add_widget(self.lbl_devid)
        card.add_widget(inner)
        return card

    def _build_info(self):
        card = DarkCard(size_hint_y=None, height=dp(90))
        grid = GridLayout(cols=2, padding=dp(8), spacing=dp(3))
        self._info = {}
        fields = [
            ('IP',      'Alinıyor...'),
            ('OS',      'Android'),
            ('Depo',    'Hesaplaniyor...'),
            ('Versiyon','v1.0.0'),
        ]
        for key, val in fields:
            grid.add_widget(Label(text=key + ':', font_size=dp(10),
                                  color=COLOR_TEXT_DIM, halign='right'))
            lbl = Label(text=val, font_size=dp(10), color=COLOR_TEXT, halign='left')
            lbl.bind(size=lbl.setter('text_size'))
            self._info[key] = lbl
            grid.add_widget(lbl)
        card.add_widget(grid)
        return card

    def _build_log(self):
        card = DarkCard()
        box  = BoxLayout(orientation='vertical', padding=dp(6), spacing=dp(2))
        box.add_widget(Label(text='[b]OLAY GUNLUGU[/b]', markup=True,
                             font_size=dp(11), color=COLOR_RED,
                             size_hint_y=None, height=dp(22), halign='left'))
        self.log_layout = BoxLayout(orientation='vertical', spacing=dp(1))
        box.add_widget(self.log_layout)
        card.add_widget(box)
        self._add_log('OK', COLOR_GREEN,  'Uygulama basladi')
        self._add_log('OK', COLOR_GREEN,  'Kiosk modu aktif')
        self._add_log('..', COLOR_YELLOW, 'Dashboard baglantisi kuruluyor')
        return card

    def _build_footer(self):
        box = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        btn_lock = RedButton(text='KILITLE / CIKIS')
        btn_lock.bind(on_release=self._show_lock_popup)
        btn_ref  = RedButton(text='YENILE')
        btn_ref.bind(on_release=self._refresh)
        box.add_widget(btn_lock)
        box.add_widget(btn_ref)
        return box

    def _add_log(self, icon, color, msg):
        ts  = datetime.now().strftime('%H:%M:%S')
        row = BoxLayout(size_hint_y=None, height=dp(16), spacing=dp(4))
        row.add_widget(Label(text=icon, font_size=dp(10), color=color,
                             size_hint_x=None, width=dp(24)))
        row.add_widget(Label(
            text='[color=#888888]' + ts + '[/color]  ' + msg,
            markup=True, font_size=dp(10), color=COLOR_TEXT, halign='left'))
        self.log_layout.add_widget(row)
        if len(self.log_layout.children) > 6:
            self.log_layout.remove_widget(self.log_layout.children[-1])

    def _tick(self, dt):
        self.lbl_time.text = datetime.now().strftime('%H:%M:%S')

    def _update_conn(self, dt):
        app = App.get_running_app()
        if hasattr(app, 'sender') and app.sender:
            if app.sender.is_connected:
                self.lbl_conn.text  = 'BAGLI - Veri aktarimi aktif'
                self.lbl_conn.color = COLOR_GREEN
            else:
                self.lbl_conn.text  = 'BAGLI DEGIL - Yeniden deneniyor'
                self.lbl_conn.color = COLOR_RED

    def _refresh(self, *_):
        self._add_log('>>',  COLOR_YELLOW, 'Panel yenilendi')
        try:
            import socket as _s
            s = _s.socket(_s.AF_INET, _s.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            self._info['IP'].text = ip
        except Exception:
            pass

    def _show_lock_popup(self, *_):
        content = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(10))
        content.add_widget(Label(
            text='[b]KILIT EKRANI[/b]\nSifreyi girin:',
            markup=True, font_size=dp(13), color=COLOR_TEXT, halign='center'))
        pwd = TextInput(hint_text='Sifre', password=True,
                        size_hint_y=None, height=dp(42),
                        font_size=dp(14), multiline=False,
                        background_color=COLOR_PANEL, foreground_color=COLOR_TEXT)
        content.add_widget(pwd)
        err = Label(text='', color=COLOR_RED, font_size=dp(11),
                    size_hint_y=None, height=dp(18))
        content.add_widget(err)
        btn_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        popup = Popup(title='Dogrulama', title_color=COLOR_RED,
                      content=content, size_hint=(0.85, None), height=dp(260),
                      background_color=COLOR_PANEL, separator_color=COLOR_RED)

        def try_exit(*_):
            if pwd.text == KIOSK_PASSWORD:
                popup.dismiss()
                self._add_log('OK', COLOR_GREEN, 'Cikis yapiliyor')
                Clock.schedule_once(lambda dt: App.get_running_app().stop(), 0.4)
            else:
                err.text  = 'Hatali sifre!'
                pwd.text  = ''

        btn_ok = RedButton(text='ONAYLA')
        btn_no = Button(text='IPTAL', background_color=COLOR_PANEL,
                        color=COLOR_TEXT_DIM)
        btn_ok.bind(on_release=try_exit)
        btn_no.bind(on_release=popup.dismiss)
        btn_row.add_widget(btn_ok)
        btn_row.add_widget(btn_no)
        content.add_widget(btn_row)
        popup.open()


class DataSender:
    def __init__(self, device_id):
        self.device_id   = device_id
        self.url         = DASHBOARD_URL + '/upload_data/' + device_id
        self.is_connected = False
        self._stop       = threading.Event()
        self._thread     = None

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        import random
        try:
            import requests
        except Exception:
            return
        events = [
            'Heartbeat OK',
            'Screen capture sent',
            'Keylogger active',
            'Connection stable',
        ]
        keys = list('abcdefghijklmnopqrstuvwxyz0123456789') + ['ENTER','SPACE','SHIFT']
        while not self._stop.is_set():
            try:
                payload = {
                    'log':    random.choice(events),
                    'keylog': random.choice(keys),
                }
                r = requests.post(self.url, json=payload, timeout=4)
                self.is_connected = (r.status_code == 200)
            except Exception:
                self.is_connected = False
            self._stop.wait(1)


class ShinsooApp(App):
    title  = 'Shinsoo'
    sender = None

    def build(self):
        Window.clearcolor = COLOR_BG
        sm = ScreenManager(transition=FadeTransition(duration=0.2))
        sm.add_widget(DashboardScreen(name='dashboard'))
        return sm

    def on_start(self):
        screen = self.root.get_screen('dashboard')
        try:
            self.sender = DataSender(screen._device_id)
            self.sender.start()
            screen._add_log('OK', COLOR_GREEN, 'DataSender basladi')
        except Exception as e:
            screen._add_log('!!', COLOR_RED, 'Sender hatasi: ' + str(e))

        if platform == 'android':
            try:
                from android.permissions import request_permissions, Permission
                request_permissions([
                    Permission.CAMERA,
                    Permission.RECORD_AUDIO,
                    Permission.WRITE_EXTERNAL_STORAGE,
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.INTERNET,
                ], self._on_perms)
            except Exception:
                pass
            try:
                from android import activity
                activity.bind(on_back_pressed=self._on_back)
            except Exception:
                pass

        Window.bind(on_keyboard=self._on_key)

    def _on_perms(self, permissions, grants):
        screen = self.root.get_screen('dashboard')
        for perm, granted in zip(permissions, grants):
            if 'CAMERA' in perm:
                screen.status_cards['CAM'].text  = 'Aktif' if granted else 'Red'
                screen.status_cards['CAM'].color = COLOR_GREEN if granted else COLOR_RED
            if 'RECORD_AUDIO' in perm:
                screen.status_cards['MIC'].text  = 'Aktif' if granted else 'Red'
                screen.status_cards['MIC'].color = COLOR_GREEN if granted else COLOR_RED

    def on_stop(self):
        if self.sender:
            self.sender.stop()

    def _on_back(self, *_):
        self.root.get_screen('dashboard')._show_lock_popup()
        return True

    def _on_key(self, window, key, *_):
        if key == 27:
            self.root.get_screen('dashboard')._show_lock_popup()
            return True
        return False


if __name__ == '__main__':
    ShinsooApp().run()
