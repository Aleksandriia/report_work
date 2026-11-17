@echo off
chcp 65001 >nul
echo Начинаем сборку приложения для Windows...

echo Проверка зависимостей...
pip install pyinstaller matplotlib

echo Сборка...
if exist icon.ico (
    pyinstaller --noconfirm --windowed --onefile ^
        --name="DailyReport" ^
        --icon="icon.ico" ^
        main.py
) else (
    echo Иконка icon.ico не найдена, собираем без иконки.
    pyinstaller --noconfirm --windowed --onefile ^
        --name="DailyReport" ^
        main.py
)

echo Готово! Приложение находится в папке dist\DailyReport.exe
pause