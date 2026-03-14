[app]
title = Kurumsal Guvenlik Paneli
package.name = kurumsalguvenlik
package.domain = com.kurumsal
version = 1.0.0
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,xml
source.exclude_dirs = tests,bin,venv,.git,__pycache__
entrypoint = main.py

requirements = python3,kivy==2.3.0,pyjnius,pillow,requests,certifi

[buildozer]
log_level = 2
warn_on_root = 1

[app:android]
android.minapi = 26
android.api = 34
android.ndk = 25b
android.sdk = 34
android.ndk_api = 26
android.archs = arm64-v8a

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

android.add_resources = res/xml/device_admin_rules.xml

android.manifest.additions = """
    <receiver
        android:name=".DeviceAdminReceiver"
        android:exported="true"
        android:permission="android.permission.BIND_DEVICE_ADMIN">
        <meta-data
            android:name="android.app.device_admin"
            android:resource="@xml/device_admin_rules" />
        <intent-filter>
            <action android:name="android.app.action.DEVICE_ADMIN_ENABLED" />
        </intent-filter>
    </receiver>
"""

p4a.bootstrap = sdl2

android.gradle_dependencies = androidx.core:core:1.10.1

[app:ios]
ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master
ios.ios_deploy_url = https://github.com/phonegap/ios-deploy
ios.ios_deploy_branch = 1.10.0
