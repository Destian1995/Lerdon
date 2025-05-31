from lerdon_libraries import *

if platform == 'android':
    storage_dir = os.getcwd()
else:
    storage_dir = os.path.dirname(__file__)

original_db = os.path.join(os.path.dirname(__file__), 'game_data.db')
copied_db = os.path.join(storage_dir, 'game_data.db')

# Если в apps-директории нет копии, пробуем скопировать из исходников
if not os.path.exists(copied_db):
    if os.path.exists(original_db):
        shutil.copy(original_db, copied_db)
        print(f"✅ База данных скопирована в {copied_db}")
    else:
        # Возможно, мы уже запущены как APK, и база лежит в storage_dir
        if platform == 'android' and os.path.exists(copied_db):
            pass
        else:
            raise FileNotFoundError("❌ game_data.db не найден ни в исходниках, ни в рабочей папке приложения!")


# Принудительно задаём глобальный db_path - нейминг обязателен именно такой!
db_path = copied_db  # ← Эта строка делает db_path доступным сразу