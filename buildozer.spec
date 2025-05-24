[app]

# Название моего тайтла
title = Лэрдон

# Package name (без пробелов и спецсимволов)
package.name = lerdon

# Domain (должен быть уникальным)
package.domain = com.lerdon

# Source code directory
source.dir = .

# Include files (расширения файлов для включения)
source.include_exts = py,png,jpg,ttf,mp3,mp4,db,sqlite3,json,txt

android.add_assets = files/menu/dossier
# Include patterns (шаблоны для включения файлов)
source.include_patterns = \
    assets/*, \
    files/*, \
    files/menu/dossier/*.png, \
    game_data.db, \
    *.py

# Main source file
source.main = main.py

# Requirements (зависимости)
requirements = python3==3.11.0,kivy==2.1.0,pyjnius==1.5.0,cython==0.29.33,android,ffpyplayer,ffmpeg
p4a.python_version = 3.11
p4a.whitelist = python3.11


# Application version
version = 0.99.70

# Application author
author = Vladislav Lerdon Team

# Image file
icon.filename = %(source.dir)s/assets/icon.png
presplash.filename = %(source.dir)s/assets/splash.png

orientation = landscape

# Application description
description = Стратегическая игра Lerdon с элементами экономики и политики.

# Android permissions
android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# Android API level
android.api = 34

# Minimum Android API level
android.minapi = 21

# NDK API level
android.ndk_api = 21

# Версия NDK
android.ndk = 25b

# Использовать конкретную версию SDK
android.sdk = 34
android.build_tools = 34

# Fullscreen mode
fullscreen = 1

# Log уровень
log_level = 2

# Не очищать сборку при каждом запуске (позволит быстрее отлаживать)
buildozer.build_logfile = buildozer.log

# Архитектура Android
android.archs = x86, arm64-v8a, armeabi-v7a, x86_64
