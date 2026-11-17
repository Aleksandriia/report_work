#!/bin/bash

echo "Начинаем сборку приложения для macOS..."

# 1. Установка зависимостей
echo "Проверка зависимостей..."
/opt/homebrew/bin/pip3.11 install pyinstaller matplotlib

# 2. Очистка старых сборок
rm -rf build dist DailyReport.spec

# 3. Проверка наличия иконки
ICON_ARG=""
if [ -f "icon.icns" ]; then
    ICON_ARG="--icon=icon.icns"
    echo "Иконка найдена."
fi

# 4. Сборка
echo "Сборка..."
/opt/homebrew/bin/pyinstaller --noconfirm --windowed --onedir \
    --name="DailyReport" \
    --osx-bundle-identifier "com.aleksandria.dailyreport" \
    $ICON_ARG \
    --collect-all matplotlib \
    --hidden-import matplotlib.backends.backend_tkagg \
    main.py

echo "Готово! Приложение находится в папке dist/DailyReport.app"