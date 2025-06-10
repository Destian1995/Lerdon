from lerdon_libraries import *
# ==========================
# 1. Определяем путь к папке “файлов” (storage) на Android
# ==========================
if platform == 'android':
    from android.storage import app_storage_path
    # модуль android.storage даёт гарантированный путь к директории /data/data/<package>/files/
    try:
        storage_dir = app_storage_path()
    except ImportError:
        # На старых версиях p4a этот модуль может отсутствовать,
        # в таком случае fallback на os.getcwd(), но с осторожностью:
        storage_dir = os.getcwd()
else:
    # На десктопе (разработка) просто каталог с этим скриптом
    storage_dir = os.path.dirname(__file__)

# ==========================
# 2. Пути к файлам базы
# ==========================
# Поскольку мы переместили game_data.db в assets/, при установке APK
# Kivy помещает его внутрь /assets/game_data.db. Чтобы получить путь до
# “упакованного” asset-файла, используем resource_find.

# resource_find вернёт путь вида:
#   - при запуске на настольной ОС: абсолютный путь ../assets/game_data.db
#   - при запуске внутри APK: путь вида '/data/app/.../base.apk/assets/game_data.db'
original_asset_path = resource_find('game_data.db')
# Если по какой-то причине resource_find вернул None — база не упакована
if original_asset_path is None:
    raise FileNotFoundError("❌ Couldn't find game_data.db in assets. Check the source.include_patterns and assets folder/.")

# Путь, куда будем копировать базу для фактической работы:
copied_db = os.path.join(storage_dir, 'game_data.db')

# ==========================
# 3. Копируем базу при первом запуске
# ==========================
# Если файла нет в storage_dir → копируем из assets
if not os.path.exists(copied_db):
    try:
        # Если запускаемся на Android, original_asset_path будет указывать во внутрь APK (read-only),
        # но можно копировать напрямую из ресурса:
        shutil.copyfile(original_asset_path, copied_db)
        print(f"✅ Database copying success: {copied_db}")
    except Exception as e:
        raise RuntimeError(f"❌ Database copying error: {e}")

# ==========================
# 4. Задаём глобальный db_path
# ==========================
# В дальнейшем остальные модули (например, ваши DAO/ORM или SQL-запросы)
# могут просто импортировать db_path из этого файла
db_path = copied_db
