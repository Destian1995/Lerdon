#!/bin/bash

# === Настройки ===
APP_NAME="lerdon"
SPEC_FILE="buildozer.spec"
LOG_FILE="buildozer.log"
MIN_DISK_SPACE_MB=5120  # Минимум 5 ГБ

# Путь к NDK
NDK_ZIP="$HOME/.buildozer/android/platform/android-ndk-r25b-linux.zip"

# Переменные окружения
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export ANDROID_SDK_ROOT="$HOME/.buildozer/android/platform/android-sdk"
export ANDROIDSDK="$ANDROID_SDK_ROOT"
export ANDROIDNDK="$HOME/.buildozer/android/platform/android-ndk-r25b"
export ANDROIDAPI=34
export ANDROIDMINAPI=21
export TZ=:/usr/share/zoneinfo/Etc/GMT-4

START_TIME=$(date +%s)
echo "⏰ Текущее время: $(date '+%Y-%m-%d %H:%M:%S')"
echo "🚀 Старт сборки: $(date '+%Y-%m-%d %H:%M:%S')"

# === Функция для вывода ошибок ===
error_exit() {
    echo "❌ Ошибка: $1" >&2
    echo "📜 Последние 50 строк лога ($LOG_FILE):"
    tail -n 50 "$LOG_FILE"
    exit 1
}

# === Время выполнения шагов ===
log_time() {
    local END_TIME=$(date +%s)
    local DURATION=$((END_TIME - START_TIME))
    echo "⏱️ Шаг завершён за $DURATION сек."
    START_TIME=$(date +%s)
}

# === Проверка buildozer ===
echo "🔍 Проверка установленного buildozer..."
if ! command -v buildozer &> /dev/null; then
    error_exit "'buildozer' не установлен. Установите его: pip3 install buildozer"
fi
log_time

# === Проверка места на диске ===
echo "💾 Проверка свободного места на диске..."
DISK_FREE=$(df -m . | awk 'NR==2 {print $4}')
if (( DISK_FREE < MIN_DISK_SPACE_MB )); then
    error_exit "Недостаточно места на диске. Требуется минимум $MIN_DISK_SPACE_MB МБ, доступно: ${DISK_FREE} МБ"
fi
log_time

# === Частичная очистка ===
echo "🧹 Очистка временных файлов сборки..."
mkdir -p ~/.buildozer/android/platform
rm -rf ~/Lerdon/.buildozer
mkdir -p ~/Lerdon/.buildozer
log_time

# === Принятие лицензии ===
echo "📜 Автоматическое принятие лицензии Android SDK..."
SDK_LICENSE_DIR="$HOME/.buildozer/android/platform/android-sdk/licenses"
mkdir -p "$SDK_LICENSE_DIR"
LICENSE_CONTENT="8933bad161af4178b1185d1a37fbf4f9829056a34"
echo -e "$LICENSE_CONTENT" > "$SDK_LICENSE_DIR/android-sdk-license"
log_time

# === Проверка NDK ===
echo "📦 Проверка наличия NDK..."
if [ ! -f "$NDK_ZIP" ]; then
    error_exit "Файл NDK отсутствует: $NDK_ZIP"
else
    echo "✅ Найден NDK-файл: $(basename "$NDK_ZIP")"
fi
log_time

# === Проверка spec файла ===
echo "⚙️ Проверка buildozer.spec..."
if [ ! -f "$SPEC_FILE" ]; then
    echo "📝 Создание нового buildozer.spec..."
    buildozer init >> "$LOG_FILE" 2>&1 || error_exit "Не удалось создать buildozer.spec"
else
    echo "✅ Используется существующий buildozer.spec"
fi
log_time

# === Обновление версии приложения ===
echo "🔄 Обновление версии приложения..."
CURRENT_VERSION=$(grep '^version = ' "$SPEC_FILE" | cut -d' ' -f3 | tr -d '"')
NEW_VERSION=$(echo "$CURRENT_VERSION" | awk -F. '{$NF = $NF + 1} 1' OFS=.)
sed -i "s/version = $CURRENT_VERSION/version = $NEW_VERSION/" "$SPEC_FILE" || error_exit "Не удалось обновить версию в $SPEC_FILE"
echo "🆕 Версия обновлена с $CURRENT_VERSION на $NEW_VERSION"
log_time

# === Настройка Python и архитектур ===
echo "🔧 Настройка Python 3.11 и архитектур..."
sed -i 's/^p4a.python_version =.*/p4a.python_version = 3.11/' "$SPEC_FILE" 2>/dev/null || echo "p4a.python_version = 3.11" >> "$SPEC_FILE"
sed -i 's/^p4a.whitelist =.*/p4a.whitelist = python3.11/' "$SPEC_FILE" 2>/dev/null || echo "p4a.whitelist = python3.11" >> "$SPEC_FILE"
sed -i 's/^android.archs =.*/android.archs = x86, arm64-v8a, armeabi-v7a, x86_64/' "$SPEC_FILE" 2>/dev/null || echo "android.archs = x86, arm64-v8a, armeabi-v7a, x86_64" >> "$SPEC_FILE"
log_time

# === Сборка APK ===
echo "📦 Начинаем сборку APK... Это занимает 35-40 минут!"
START_BUILD_TIME=$(date +%s)
buildozer -v android debug > "$LOG_FILE" 2>&1
BUILD_EXIT_CODE=$?
END_BUILD_TIME=$(date +%s)
BUILD_DURATION=$((END_BUILD_TIME - START_BUILD_TIME))

# === Проверка результата ===
echo "⏱️ Сборка завершена за $BUILD_DURATION сек."
if [ $BUILD_EXIT_CODE -eq 0 ]; then
    echo "✅ Сборка успешно завершена!"
    APK_PATH=$(find ~/Lerdon/bin -name "*-$NEW_VERSION-debug.apk" | head -n1)
    if [ -f "$APK_PATH" ]; then
        echo "📲 APK готов: $APK_PATH"
    else
        error_exit "Файл APK не найден после успешной сборки"
    fi
else
    error_exit "Ошибка при сборке APK (код: $BUILD_EXIT_CODE)"
fi

exit 0
