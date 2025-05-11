#!/bin/bash

# === Настройки ===
APP_NAME="lerdon"
SPEC_FILE="buildozer.spec"
LOG_FILE="buildozer.log"
NDK_ZIP="$HOME/.buildozer/android/platform/android-ndk-r25b-linux.zip"
MIN_DISK_SPACE_MB=5120  # Минимум 5 ГБ свободного места
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
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
}

# === Начало ===
START_TIME=$(date +%s)
echo "🚀 Старт сборки: $(date '+%Y-%m-%d %H:%M:%S')"

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

# === Частичная очистка: сохраняем NDK, удаляем остальное ===
echo "🧹 Очистка временных файлов сборки..."
mkdir -p ~/.buildozer/android/platform

# Удаляем только проектную часть .buildozer
rm -rf ~/Lerdon/.buildozer
mkdir -p ~/Lerdon/.buildozer
log_time

# === Принятие лицензии Android SDK автоматически ===
echo "📜 Автоматическое принятие лицензии Android SDK..."
SDK_LICENSE_DIR="$HOME/.buildozer/android/platform/android-sdk/licenses"
mkdir -p "$SDK_LICENSE_DIR"
echo -e "\nd56f5187e9b55dd56f65f0f5a4df33d351c9b0d5" > "$SDK_LICENSE_DIR/android-sdk-license"
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

# === Сборка APK с сохранением лога ===
echo "📦 Начинаем сборку APK... Это может занять несколько минут!"
START_BUILD_TIME=$(date +%s)
buildozer -v android debug > "$LOG_FILE" 2>&1
BUILD_EXIT_CODE=$?
END_BUILD_TIME=$(date +%s)
BUILD_DURATION=$((END_BUILD_TIME - START_BUILD_TIME))
echo "⏱️ Сборка завершена за $BUILD_DURATION секунд."

# === Проверка успешности сборки ===
APK_PATH="bin/${APP_NAME}-${NEW_VERSION}-debug.apk"
if [ $BUILD_EXIT_CODE -eq 0 ] && [ -f "$APK_PATH" ]; then
    echo "✅ Сборка успешно завершена!"
    echo "📲 APK найден: $APK_PATH"
else
    error_exit "Сборка завершилась с ошибкой (код: $BUILD_EXIT_CODE)"
fi
