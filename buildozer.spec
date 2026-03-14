# ──────────────────────────────────────────────────────────────────────────────
# buildozer.spec
# Kurumsal Cihaz Güvenliği ve Uzaktan İzleme Paneli
# Buildozer v1.5+  |  python-for-android (p4a)
#
# APK oluşturmak için:
#   pip install buildozer cython
#   buildozer android debug         ← test APK'sı
#   buildozer android release       ← imzalı APK
# ──────────────────────────────────────────────────────────────────────────────

[app]

# ── Kimlik ────────────────────────────────────────────────────────────────────
title           = Kurumsal Güvenlik Paneli
package.name    = kurumsalguvenlik
package.domain  = com.kurumsal

# ── Sürüm ─────────────────────────────────────────────────────────────────────
version         = 1.0.0

# ── Kaynak ────────────────────────────────────────────────────────────────────
source.dir      = .
source.include_exts = py,png,jpg,kv,atlas,xml
source.exclude_dirs = tests,bin,venv,.git,__pycache__

# ── Giriş noktası ─────────────────────────────────────────────────────────────
# main.py kök dizinde olmalıdır.
entrypoint = main.py

# ── Python ────────────────────────────────────────────────────────────────────
requirements =
    python3,
    kivy==2.3.0,
    pyjnius,
    pillow,
    requests,
    certifi

# ── Hedef platform ────────────────────────────────────────────────────────────
[buildozer]
log_level = 2
warn_on_root = 1

[app:android]

# ── Minimum / Hedef API seviyeleri ────────────────────────────────────────────
android.minapi     = 26
android.api        = 33
android.ndk        = 25b
android.sdk        = 33
android.ndk_api    = 26

# ── Mimari (armeabi-v7a + arm64-v8a) ─────────────────────────────────────────
android.archs = arm64-v8a, armeabi-v7a

# ── İzinler ───────────────────────────────────────────────────────────────────
# Tüm gerekli izinler eksiksiz tanımlanmıştır.
android.permissions =
    CAMERA,
    RECORD_AUDIO,
    WRITE_EXTERNAL_STORAGE,
    READ_EXTERNAL_STORAGE,
    INTERNET,
    ACCESS_NETWORK_STATE,
    ACCESS_WIFI_STATE,
    BIND_DEVICE_ADMIN,
    WAKE_LOCK,
    RECEIVE_BOOT_COMPLETED,
    FOREGROUND_SERVICE

# ── Manifest ek özellikleri ───────────────────────────────────────────────────
# Device Admin receiver ve kiosk modu için zorunlu tanımlamalar.
android.add_activities = com.kurumsal.kurumsalguvenlik.MainActivity

android.manifest.uses-feature =
    android.hardware.camera,
    android.hardware.camera.autofocus,
    android.hardware.microphone

# ── Özel AndroidManifest.xml ek satırları ─────────────────────────────────────
# Bu satırlar <application> bloğuna eklenir.
android.manifest.additions = """
    <receiver
        android:name=".DeviceAdminReceiver"
        android:description="@string/app_description"
        android:label="@string/app_name"
        android:exported="true"
        android:permission="android.permission.BIND_DEVICE_ADMIN">
        <meta-data
            android:name="android.app.device_admin"
            android:resource="@xml/device_admin_rules" />
        <intent-filter>
            <action android:name="android.app.action.DEVICE_ADMIN_ENABLED" />
        </intent-filter>
    </receiver>

    <service
        android:name=".SecurityMonitorService"
        android:exported="false"
        android:foregroundServiceType="camera|microphone">
        <intent-filter>
            <action android:name="com.kurumsal.guvenlik.MONITOR" />
        </intent-filter>
    </service>
"""

# ── Uygulama bayrağı: HOME uygulaması (tam kiosk) ─────────────────────────────
# Kiosk modunu güçlendirmek için MAIN + HOME kategorisi eklenir.
# Bu sayede cihaz yeniden başlatıldığında uygulama otomatik açılır.
android.manifest.application_flags =
    android:name="com.kurumsal.kurumsalguvenlik.MainApplication",
    android:theme="@style/Theme.NoActionBar"

# ── Varlıklar / Statik dosyalar ───────────────────────────────────────────────
# res/xml/device_admin_rules.xml p4a tarafından kopyalanır.
android.add_src =
    src/com/kurumsal/kurumsalguvenlik/DeviceAdminReceiver.java

# XML kaynak dosyaları (res/xml/ altına kopyalanır)
android.add_resources = res/xml/device_admin_rules.xml

# ── python-for-android bootstrap ─────────────────────────────────────────────
# sdl2: Kivy için önerilen bootstrap
p4a.bootstrap = sdl2

# ── Gradle ────────────────────────────────────────────────────────────────────
android.gradle_dependencies =
    androidx.core:core:1.10.1,
    androidx.appcompat:appcompat:1.6.1

# ── İmzalama (release) ────────────────────────────────────────────────────────
# Serbest bırakmadan önce aşağıdaki değerleri doldurun:
# android.keystore      = /path/to/your.keystore
# android.keystore_pass = YOUR_KEYSTORE_PASSWORD
# android.key_alias     = YOUR_KEY_ALIAS
# android.key_alias_pass= YOUR_KEY_ALIAS_PASSWORD

# ── iOS (devre dışı) ──────────────────────────────────────────────────────────
[app:ios]
ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master
ios.ios_deploy_url = https://github.com/phonegap/ios-deploy
ios.ios_deploy_branch = 1.10.0
