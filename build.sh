#!/bin/bash

echo "Начинаем сборку приложения для macOS..."

# 1. Установка зависимостей
echo "Проверка зависимостей..."
/opt/homebrew/bin/pip3.11 install pyinstaller matplotlib

# 2. Очистка старых сборок
rm -rf build dist DailyReport.spec

# 3. Проверка наличия иконки (чтобы сборка не упала, если её нет)
ICON_ARG=""
if [ -f "icon.icns" ]; then
    ICON_ARG="--icon=icon.icns"
    echo "Иконка найдена, используем её."
else
    echo "Иконка icon.icns не найдена, собираем без иконки."
fi

# 4. Сборка
echo "🔨 Сборка (это может занять пару минут)..."
/opt/homebrew/bin/pyinstaller --noconfirm --windowed --onefile \
    --name="DailyReport" \
    $ICON_ARG \
    main.py

echo "Готово! Приложение находится в папке dist/DailyReport.app"