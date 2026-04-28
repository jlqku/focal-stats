[app]
title = 焦段统计
package.name = focalstats
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttc
version = 1.0
requirements = python3,kivy,Pillow,android
orientation = portrait
fullscreen = 0
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.arch = arm64-v8a
p4a.branch = develop
[buildozer]
log_level = 2
warn_on_root = 0
