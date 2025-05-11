#!/bin/bash

# === Настройки ===
APP_NAME="lerdon"
SPEC_FILE="buildozer.spec"
LOG_FILE="buildozer.log"

# Путь к NDK
NDK_ZIP="$HOME/.buildozer/android/platform/android-ndk-r25b-linux.zip"

MIN_DISK_SPACE_MB=5120  # Минимум 5 ГБ свободного места

# === Переменные окружения для Buildozer и P4A ===
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export ANDROIDSDK=$HOME/.buildozer/android/platform/android-sdk
export ANDROIDNDK=$HOME/.buildozer/android/platform/android-ndk-r25b
export ANDROIDAPI=34
export ANDROIDMINAPI=21

# Установка временной зоны
export TZ=:/usr/share/zoneinfo/Etc/GMT-4
START_TIME=$(date +%s)
echo "⏰ Текущее время в Саратове: $(date '+%Y-%m-%d %H:%M:%S')"
echo "🚀 Старт сборки: $(date '+%Y-%m-%d %H:%M:%S')"

# === Функция для вывода ошибок и выхода ===
error_exit() {
    echo "❌ Ошибка: $1" >&2
    echo "📜 Последние 50 строк лога ($LOG_FILE):"
    tail -n 50 "$LOG_FILE"
    exit 1
}

# === Вспомогательная функция: показывает время выполнения шагов ===
log_time() {
    local END_TIME=$(date +%s)
    local DURATION=$((END_TIME - START_TIME))
    echo "⏱️ Шаг завершён за $DURATION сек."
    START_TIME=$(date +%s)
}

# === Проверка установленного buildozer ===
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

# === Частичная очистка: сохраняем NDK/SDK, удаляем остальное ===
echo "🧹 Очистка временных файлов сборки..."

# Сохраняем папку под NDK и SDK
mkdir -p ~/.buildozer/android/platform

# Удаляем временную сборку
rm -rf ~/Lerdon/.buildozer
mkdir -p ~/Lerdon/.buildozer
log_time

# === Принятие лицензии Android SDK автоматически ===
echo "📜 Автоматическое принятие лицензии Android SDK..."
SDK_LICENSE_DIR="$HOME/.buildozer/android/platform/android-sdk/licenses"
mkdir -p "$SDK_LICENSE_DIR"

# Добавляем оба хэша для совместимости
LICENSE_CONTENT="8933bad161af4178b1185d1a37fbf4f9829056a34\nd56f5187e9b55dd56f65f0f5a4df33d351c9b0d5"
echo -e "$LICENSE_CONTENT" > "$SDK_LICENSE_DIR/android-sdk-license"
log_time

# === Проверка наличия NDK ===
echo "📦 Проверка наличия NDK..."
if [ ! -f "$NDK_ZIP" ]; then
    error_exit "Файл NDK отсутствует: $NDK_ZIP. Загрузите android-ndk-r25b-linux.zip и положите в ~/.buildozer/android/platform/"
else
    echo "✅ Найден NDK-файл: $(basename "$NDK_ZIP")"
fi
log_time

# === Создание spec файла при необходимости ===
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

sed -i "s/version = $CURRENT_VERSION/version = $NEW_VERSION/" "$SPEC_FILE" || \
    error_exit "Не удалось обновить версию в $SPEC_FILE"
echo "🆕 Версия обновлена с $CURRENT_VERSION на $NEW_VERSION"
log_time

# === Укажи Python 3.11 в buildozer.spec ===
echo "🔧 Настройка Python 3.11 в buildozer.spec..."
if ! grep -q '^p4a.python_version = 3.11' "$SPEC_FILE"; then
    if grep -q '^p4a.python_version = ' "$SPEC_FILE"; then
        sed -i 's/^p4a.python_version =.*/p4a.python_version = 3.11/' "$SPEC_FILE"
    else
        echo "p4a.python_version = 3.11" >> "$SPEC_FILE"
    fi
fi

if ! grep -q '^p4a.whitelist = python3.11' "$SPEC_FILE"; then
    if grep -q '^p4a.whitelist = ' "$SPEC_FILE"; then
        sed -i 's/^p4a.whitelist =.*/p4a.whitelist = python3.11/' "$SPEC_FILE"
    else
        echo "p4a.whitelist = python3.11" >> "$SPEC_FILE"
    fi
fi

# Убедимся, что архитектура включает x86_64
if ! grep -q '^android.archs =.*x86_64' "$SPEC_FILE"; then
    echo "🔧 Указываем все три архитектуры: arm64-v8a, armeabi-v7a, x86_64"
    sed -i 's/^android.archs =.*/android.archs = arm64-v8a, armeabi-v7a, x86_64/' "$SPEC_FILE"
fi
log_time

# === Сборка APK с сохранением лога ===
echo "📦 Начинаем сборку APK... Это занимает 30-35 минут!"
START_BUILD_TIME=$(date +%s)
buildozer -v android debug > "$LOG_FILE" 2>&1
BUILD_EXIT_CODE=$?
END_BUILD_TIME=$(date +%s)
BUILD_DURATION=$((END_BUILD_TIME - START_BUILD_TIME))

# === Проверка результата сборки ===
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
