import platform
import os

IS_MAC = platform.system() == "Darwin"

DATA_FILE = "reports.json"
TEMPLATES_FILE = "templates.json"

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

# Глобальные списки, которые будут заполняться при запуске
TEMPLATES = []
REPORTS = []