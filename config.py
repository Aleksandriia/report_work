import sys
import platform
import os

IS_MAC = platform.system() == "Darwin"

# ─── Безопасное сохранение данных ───
# Если приложение собрано как .exe или .app, сохраняем данные в домашнюю папку пользователя
if getattr(sys, 'frozen', False):
    if IS_MAC:
        APP_DIR = os.path.expanduser("~/Library/Application Support/DailyReport")
    else:
        APP_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser("~")), "DailyReport")
    
    if not os.path.exists(APP_DIR):
        os.makedirs(APP_DIR)
        
    DATA_FILE = os.path.join(APP_DIR, "reports.json")
    TEMPLATES_FILE = os.path.join(APP_DIR, "templates.json")
    SETTINGS_FILE = os.path.join(APP_DIR, "settings.json") # если добавила напоминалки
else:
    # Если запускаем из исходников (main.py), сохраняем рядом с кодом
    DATA_FILE = "reports.json"
    TEMPLATES_FILE = "templates.json"
    SETTINGS_FILE = "settings.json"

FONT = "SF Pro Text" if IS_MAC else "Segoe UI"
FONT_MONO = "Menlo" if IS_MAC else "Consolas"

DEFAULT_TEMPLATES = [
    "Тестирование критических путей нового релиза",
    "Протестированы тикеты",
    "Заведен тикет",
    "Актуализация задач",
    "Перенос и актуализация тест-кейсов в новые тикеты",
    "Тестирование смежного функционала",
]

TEMPLATES = []
REPORTS = []