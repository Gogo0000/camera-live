"""
Kurumsal Cihaz Güvenliği ve Uzaktan İzleme Paneli
main.py - Kivy Kiosk Dashboard  (DataSender entegrasyonlu)
"""

import os
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform
from kivy.core.window import Window
from kivy.animation import Animation
from datetime import datetime

from config import KIOSK_PASSWORD

# ── Renkler ──────────────────────────────────────────────────────────────────
COLOR_BG       = (0.05, 0.05, 0.07, 1)
COLOR_PANEL    = (0.10, 0.10, 0.13, 1)
COLOR_RED      = (0.85, 0.10, 0.10, 1)
COLOR_RED_DARK = (0.55, 0.05, 0.05, 1)
COLOR_TEXT     = (0.95, 0.95, 0.95, 1)
COLOR_TEXT_DIM = (0.55, 0.55, 0.60, 1)
COLOR_GREEN    = (0.10, 0.85, 0.40, 1)
COLOR_YELLOW   = (1.00, 0.80, 0.10, 1)
COLOR_BORDER   = (0.25, 0.05, 0.05, 1)


# ── Yardımcı widget'lar ───────────────────────────────────────────────────────

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

    def on_press(self):
        Animation(background_color=(1, 0.1, 0.1, 0.3), duration=0.08).start(self)

    def on_release(self):
        Animation(background_color=(0, 0, 0, 0), duration=0.2).start(self)


# ── Dashboard Ekranı ─────────────────────────────────────────────────────────

class DashboardScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build_ui()
        Clock.schedule_interval(self._tick, 1)
        Clock.schedule_interval(self._update_sender_status, 3)

    def _build_ui(self):
        root = FloatLayout()
        with root.canvas.before:
            Color(*COLOR_BG)
            self._bg_rect = Rectangle(pos=root.pos, size=root.size)
        root.bind(
            pos=lambda *_: setattr(self._bg_rect, 'pos', root.pos),
            size=lambda *_: setattr(self._bg_rect, 'size', root.size))

        main = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(10))
        main.add_widget(self._header())
        main.add_widget(self._status_row())
        main.add_widget(self._connection_bar())
        main.add_widget(self._device_info())
        main.add_widget(self._log_panel())
        main.add_widget(self._footer())

        root.add_widget(main)
        self.add_widget(root)

    def _header(self):
        box = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(8))
        with box.canvas.before:
            Color(*COLOR_RED_DARK)
            self._hdr_bg = Rectangle(pos=box.pos, size=box.size)
        box.bind(
            pos=lambda *_: setattr(self._hdr_bg, 'pos', box.pos),
            size=lambda *_: setattr(self._hdr_bg, 'size', box.size))

        title_box = BoxLayout(spacing=dp(8))
        icon = Label(text='🛡', font_size=dp(26), size_hint_x=None, width=dp(40))
        title = Label(
            text='[b]KURUMSAL CİHAZ GÜVENLİĞİ[/b]',
            markup=True, font_size=dp(15), color=COLOR_TEXT,
            halign='left', valign='middle')
        title.bind(size=title.setter('text_size'))
        title_box.add_widget(icon)
        title_box.add_widget(title)

        self.lbl_time = Label(
            text='--:--:--', font_size=dp(14), color=COLOR_TEXT_DIM,
            size_hint_x=None, width=dp(90), halign='right')
        self.lbl_time.bind(size=self.lbl_time.setter('text_size'))

        box.add_widget(title_box)
        box.add_widget(self.lbl_time)
        return box

    def _status_row(self):
        grid = GridLayout(cols=3, size_hint_y=None, height=dp(80), spacing=dp(8))
        self.status_cards = {}
        items = [
            ('📷', 'KAMERA',   'Aktif',   COLOR_GREEN),
            ('🎤', 'MİKROFON', 'Aktif',   COLOR_GREEN),
            ('🔒', 'KİOSK',    'Kilitli', COLOR_RED),
        ]
        for icon, title, status, color in items:
            card  = DarkCard()
            inner = BoxLayout(orientation='vertical', padding=dp(6))
            inner.add_widget(Label(text=f'{icon}  {title}', font_size=dp(11),
                                   color=COLOR_TEXT_DIM, bold=True))
            lbl = Label(text=status, font_size=dp(13), color=color, bold=True)
            inner.add_widget(lbl)
            card.add_widget(inner)
            self.status_cards[title] = lbl
            grid.add_widget(card)
        return grid

    def _connection_bar(self):
        """Dashboard bağlantı durumu şeridi."""
        card = DarkCard(size_hint_y=None, height=dp(36))
        inner = BoxLayout(padding=dp(6), spacing=dp(8))

        inner.add_widget(Label(text='📡', font_size=dp(14),
                               size_hint_x=None, width=dp(24)))
        inner.add_widget(Label(
            text='[b]DASHBOARD BAĞLANTISI:[/b]', markup=True,
            font_size=dp(11), color=COLOR_TEXT_DIM,
            size_hint_x=None, width=dp(170)))

        self.lbl_conn = Label(
            text='Bağlanıyor...', font_size=dp(11),
            color=COLOR_YELLOW, halign='left')
        self.lbl_conn.bind(size=self.lbl_conn.setter('text_size'))

        self.lbl_devid = Label(
            text='', font_size=dp(10), color=COLOR_TEXT_DIM,
            halign='right', size_hint_x=None, width=dp(120))
        self.lbl_devid.bind(size=self.lbl_devid.setter('text_size'))

        inner.add_widget(self.lbl_conn)
        inner.add_widget(self.lbl_devid)
        card.add_widget(inner)
        return card

    def _device_info(self):
        card = DarkCard(size_hint_y=None, height=dp(110))
        grid = GridLayout(cols=2, padding=dp(10), spacing=dp(4))
        self._info_labels = {}
        fields = [
            ('Cihaz',     'Android Cihaz'),
            ('OS',        'Android 11+'),
            ('IP Adresi', 'Alınıyor...'),
            ('Depolama',  'Hesaplanıyor...'),
            ('Yönetici',  'DeviceAdmin: Aktif'),
            ('Uygulama',  'v1.0.0 - Güvenli'),
        ]
        for key, val in fields:
            grid.add_widget(Label(
                text=f'[b]{key}:[/b]', markup=True,
                font_size=dp(11), color=COLOR_TEXT_DIM, halign='right'))
            lbl = Label(text=val, font_size=dp(11), color=COLOR_TEXT, halign='left')
            lbl.bind(size=lbl.setter('text_size'))
            self._info_labels[key] = lbl
            grid.add_widget(lbl)
        card.add_widget(grid)
        return card

    def _log_panel(self):
        card = DarkCard()
        box  = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(4))
        box.add_widget(Label(
            text='[b]  ▌ OLAY GÜNLÜĞÜ[/b]', markup=True,
            font_size=dp(12), color=COLOR_RED,
            size_hint_y=None, height=dp(24), halign='left'))
        self.log_layout = BoxLayout(orientation='vertical', spacing=dp(2))
        box.add_widget(self.log_layout)
        card.add_widget(box)
        self._init_logs()
        return card

    def _footer(self):
        box = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        btn_lock = RedButton(text='🔐  KİLİTLE / ÇIKIŞ')
        btn_lock.bind(on_release=self._show_lock_popup)
        btn_refresh = RedButton(text='🔄  YENİLE')
        btn_refresh.bind(on_release=self._refresh)
        box.add_widget(btn_lock)
        box.add_widget(btn_refresh)
        return box

    # ── Log yardımcıları ──────────────────────────────────────────────────

    def _init_logs(self):
        entries = [
            ('✔', COLOR_GREEN,  'Uygulama başlatıldı'),
            ('✔', COLOR_GREEN,  'DeviceAdmin yetkisi alındı'),
            ('✔', COLOR_GREEN,  'Kamera izni verildi'),
            ('✔', COLOR_GREEN,  'Mikrofon izni verildi'),
            ('⚠', COLOR_YELLOW, 'Kiosk modu etkinleştirildi'),
            ('📡', COLOR_YELLOW, 'Dashboard bağlantısı kuruluyor...'),
        ]
        for icon, color, msg in entries:
            self._add_log(icon, color, msg)

    def _add_log(self, icon, color, msg):
        ts  = datetime.now().strftime('%H:%M:%S')
        row = BoxLayout(size_hint_y=None, height=dp(18), spacing=dp(6))
        row.add_widget(Label(text=icon, font_size=dp(11), color=color,
                             size_hint_x=None, width=dp(16)))
        row.add_widget(Label(
            text=f'[color=#888888]{ts}[/color]  {msg}',
            markup=True, font_size=dp(11), color=COLOR_TEXT, halign='left'))
        self.log_layout.add_widget(row)
        if len(self.log_layout.children) > 8:
            self.log_layout.remove_widget(self.log_layout.children[-1])

    # ── Periyodik güncelleme ──────────────────────────────────────────────

    def _tick(self, dt):
        self.lbl_time.text = datetime.now().strftime('%H:%M:%S')

    def _update_sender_status(self, dt):
        """DataSender bağlantı durumunu 3 saniyede bir günceller."""
        app = App.get_running_app()
        if not hasattr(app, 'sender') or app.sender is None:
            return
        sender = app.sender
        if sender.is_connected:
            self.lbl_conn.text  = '✔ Bağlı – Veri aktarımı aktif'
            self.lbl_conn.color = COLOR_GREEN
        else:
            self.lbl_conn.text  = '✖ Bağlantı yok – Yeniden deneniyor...'
            self.lbl_conn.color = COLOR_RED
        self.lbl_devid.text = f'ID: {sender.device_id}'

    def _refresh(self, *_):
        self._add_log('🔄', COLOR_YELLOW, 'Panel yenilendi')
        try:
            from android_interface import AndroidInterface
            ai = AndroidInterface()
            ip = ai.get_ip_address()
            self._info_labels['IP Adresi'].text = ip or 'Bulunamadı'
            info = ai.get_device_info()
            self._info_labels['Cihaz'].text = info.get('model', 'Android Cihaz')
            storage = ai.get_storage_info()
            if storage:
                used  = storage.get('used_mb', 0)
                total = storage.get('total_mb', 1)
                self._info_labels['Depolama'].text = f'{used}/{total} MB'
        except Exception:
            self._info_labels['IP Adresi'].text = '192.168.x.x'

    # ── Kilit popup'ı ─────────────────────────────────────────────────────

    def _show_lock_popup(self, *_):
        content = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))
        content.add_widget(Label(
            text='[b]🔐 KİLİT EKRANI[/b]\nUygulamadan çıkmak için şifreyi girin:',
            markup=True, font_size=dp(13), color=COLOR_TEXT, halign='center'))
        pwd_input = TextInput(
            hint_text='Şifre', password=True,
            size_hint_y=None, height=dp(44),
            font_size=dp(14), multiline=False,
            background_color=COLOR_PANEL, foreground_color=COLOR_TEXT)
        content.add_widget(pwd_input)
        err_lbl = Label(text='', color=COLOR_RED, font_size=dp(12),
                        size_hint_y=None, height=dp(20))
        content.add_widget(err_lbl)
        btn_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))

        popup = Popup(
            title='Güvenlik Doğrulama', title_color=COLOR_RED,
            content=content, size_hint=(0.8, None), height=dp(280),
            background_color=COLOR_PANEL, separator_color=COLOR_RED)

        def try_exit(*_):
            if pwd_input.text == KIOSK_PASSWORD:
                popup.dismiss()
                self._add_log('✔', COLOR_GREEN, 'Şifre doğru – çıkış yapılıyor')
                Clock.schedule_once(lambda dt: App.get_running_app().stop(), 0.5)
            else:
                err_lbl.text  = '⚠ Hatalı şifre!'
                pwd_input.text = ''

        btn_ok = RedButton(text='ONAYLA')
        btn_cancel = Button(text='İPTAL', background_color=COLOR_PANEL,
                            color=COLOR_TEXT_DIM)
        btn_ok.bind(on_release=try_exit)
        btn_cancel.bind(on_release=popup.dismiss)
        btn_row.add_widget(btn_ok)
        btn_row.add_widget(btn_cancel)
        content.add_widget(btn_row)
        popup.open()


# ── Ana Uygulama ──────────────────────────────────────────────────────────────

class KioskApp(App):
    title  = 'Kurumsal Güvenlik Paneli'
    sender = None   # DataSender referansı

    def build(self):
        Window.clearcolor = COLOR_BG
        self.sm = ScreenManager(transition=FadeTransition(duration=0.25))
        self.sm.add_widget(DashboardScreen(name='dashboard'))
        self._request_permissions()
        return self.sm

    def on_start(self):
        # ── DataSender başlat ──────────────────────────────────────────
        try:
            from android_interface import DataSender
            self.sender = DataSender()
            self.sender.start()
            screen = self.sm.get_screen('dashboard')
            screen._add_log('📡', COLOR_GREEN,
                            f'DataSender başlatıldı – ID: {self.sender.device_id}')
        except Exception as e:
            screen = self.sm.get_screen('dashboard')
            screen._add_log('✖', (1,0.3,0.3,1), f'DataSender hatası: {e}')

        # ── Geri tuşu / ESC engeli ─────────────────────────────────────
        if platform == 'android':
            from android import activity              # type: ignore
            activity.bind(on_back_pressed=self._on_back)
        Window.bind(on_keyboard=self._on_key)

    def on_stop(self):
        """Uygulama kapanırken DataSender'ı düzgün durdur."""
        if self.sender:
            self.sender.stop()

    def _request_permissions(self):
        if platform == 'android':
            from android.permissions import request_permissions, Permission  # type: ignore
            request_permissions([
                Permission.CAMERA,
                Permission.RECORD_AUDIO,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.INTERNET,
            ], self._on_permissions)

    def _on_permissions(self, permissions, grants):
        screen = self.sm.get_screen('dashboard')
        for perm, granted in zip(permissions, grants):
            if 'CAMERA' in perm:
                screen.status_cards['KAMERA'].text  = 'Aktif' if granted else 'Reddedildi'
                screen.status_cards['KAMERA'].color = COLOR_GREEN if granted else COLOR_RED
            if 'RECORD_AUDIO' in perm:
                screen.status_cards['MİKROFON'].text  = 'Aktif' if granted else 'Reddedildi'
                screen.status_cards['MİKROFON'].color = COLOR_GREEN if granted else COLOR_RED

    def _on_back(self, *_):
        self.sm.get_screen('dashboard')._show_lock_popup()
        return True

    def _on_key(self, window, key, *_):
        if key == 27:
            self.sm.get_screen('dashboard')._show_lock_popup()
            return True
        return False


if __name__ == '__main__':
    KioskApp().run()
