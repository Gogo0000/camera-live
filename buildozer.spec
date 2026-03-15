[app]
title = Shinsoo
package.name = shinsoo
package.domain = com.shinsoo
version = 1.0.0
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,xml
entrypoint = main.py

requirements = python3,kivy==2.3.0,pyjnius,pillow,requests,certifi,plyer

orientation = portrait

android.permissions =
    CAMERA,
    RECORD_AUDIO,
    WRITE_EXTERNAL_STORAGE,
    READ_EXTERNAL_STORAGE,
    INTERNET,
    ACCESS_FINE_LOCATION,
    ACCESS_COARSE_LOCATION,
    ACCESS_NETWORK_STATE,
    WAKE_LOCK,
    FOREGROUND_SERVICE

android.minapi = 26
android.api = 33
android.ndk = 25b
android.sdk = 33
android.ndk_api = 26
android.archs = arm64-v8a

android.add_resources = res/xml/device_admin_rules.xml

p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 1
