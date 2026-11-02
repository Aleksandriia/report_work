import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
from datetime import datetime
import calendar
import os
import re

DATA_FILE = "reports.json"

# ─── Шаблоны комментариев ───
TEMPLATES = [
    "Тестирование критических путей нового релиза",
    "Протестированы тикеты",
    "Заведен тикет",
    "Созданы тикеты",
    "Найден критический баг, заведен тикет",
    "Актуализация задач",
    "Перенос и актуализация тест-кейсов в новые тикеты",
    "Продолжение прохождения критических путей",
    "Тестирование смежного функционала",
    "Планирование протокола регресс-тестирования",
    "Знакомство с selenium тестами, создание и запуск первого теста",
    "Попытки восстановить utms после краша",
]

# ─── Загрузка / сохранение ───
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ─── Подсчёт часов ───
def calc_hours(start, end, lunch=False):
    try:
        t1 = datetime.strptime(start, "%H:%M")
        t2 = datetime.strptime(end, "%H:%M")
        diff = (t2 - t1).total_seconds() / 3600
        if diff < 0:
            diff += 24
        if lunch:
            diff -= 1.0
        return round(diff, 1)
    except:
        return 0.0

def format_hours(h):
    if h == int(h):
        return f"{int(h)} часов"
    return f"{h} часов"

# ─── Поиск записи по дате ───
def find_record_by_date(date_str):
    for i, r in enumerate(reports):
        if r["date"] == date_str:
            return i, r
    return None, None

# ─── Сборка комментария из блоков ───
def build_comment_from_blocks(blocks, extra_text):
    """blocks = [(template, tickets), ...]"""
    parts = []
    for template, tickets in blocks:
        if template and tickets:
            parts.append(f"{template} {tickets}")
        elif template:
            parts.append(template)
        elif tickets:
            parts.append(tickets)
    
    if extra_text:
        parts.append(extra_text)
    
    result = ". ".join(parts)
    if result and not result.endswith("."):
        result += "."
    return result

# ─── Парсинг комментария в блоки ───
def parse_comment_to_blocks(comment):
    """Пытается разбить комментарий на блоки (шаблон + тикеты)"""
    blocks = []
    remaining = comment
    
    for template in TEMPLATES:
        # Ищем шаблон в комментарии
        pattern = re.escape(template)
        match = re.search(pattern, remaining, re.IGNORECASE)
        if match:
            # Вырезаем шаблон из оставшегося текста
            before = remaining[:match.start()].strip(". ,")
            after = remaining[match.end():].strip(". ,")
            
            # Ищем тикеты после шаблона (числа 3+ цифр)
            tickets_match = re.search(r'[\d,\s]+', after)
            tickets = ""
            if tickets_match:
                tickets = tickets_match.group().strip(", ")
                # Убираем найденные тикеты из after
                after = after[tickets_match.end():].strip(". ,")
            
            if template or tickets:
                blocks.append((template, tickets))
            
            remaining = after
            if before:
                # Текст до шаблона — добавляем как доп. комментарий
                pass
    
    # Оставшийся текст — доп. комментарий
    extra = remaining.strip(". ,")
    
    return blocks, extra

# ─── Календарь (popup) ───
class CalendarPopup:
    def __init__(self, parent, callback, initial_date=None):
        self.top = tk.Toplevel(parent)
        self.top.title("Выберите дату")
        self.top.geometry("300x300")
        self.top.resizable(False, False)
        self.top.configure(bg="#2d2d2d")
        self.callback = callback
        
        if initial_date:
            try:
                self.current_date = datetime.strptime(initial_date, "%d.%m.%Y")
            except:
                self.current_date = datetime.now()
        else:
            self.current_date = datetime.now()
        
        self._build_calendar()
    
    def _build_calendar(self):
        for widget in self.top.winfo_children():
            widget.destroy()
        
        year = self.current_date.year
        month = self.current_date.month
        
        header = tk.Frame(self.top, bg="#2d2d2d")
        header.pack(fill="x", pady=10, padx=10)
        
        btn_prev = tk.Button(header, text="◀", width=3, bg="#3d3d3d", fg="white",
                            activebackground="#0078d4", activeforeground="white",
                            relief="flat", font=("Segoe UI", 10),
                            command=lambda: self._change_month(-1))
        btn_prev.pack(side="left")
        
        month_name = calendar.month_name[month]
        lbl_month = tk.Label(header, text=f"{month_name} {year}", 
                            bg="#2d2d2d", fg="white",
                            font=("Segoe UI", 12, "bold"))
        lbl_month.pack(side="left", expand=True)
        
        btn_next = tk.Button(header, text="▶", width=3, bg="#3d3d3d", fg="white",
                            activebackground="#0078d4", activeforeground="white",
                            relief="flat", font=("Segoe UI", 10),
                            command=lambda: self._change_month(1))
        btn_next.pack(side="right")
        
        days_header = tk.Frame(self.top, bg="#2d2d2d")
        days_header.pack(fill="x", padx=10)
        
        for i, day_name in enumerate(["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]):
            lbl = tk.Label(days_header, text=day_name, width=4,
                          bg="#2d2d2d", fg="#aaaaaa",
                          font=("Segoe UI", 9, "bold"))
            lbl.grid(row=0, column=i, padx=2, pady=5)
        
        days_frame = tk.Frame(self.top, bg="#2d2d2d")
        days_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        cal = calendar.monthcalendar(year, month)
        for row_idx, week in enumerate(cal):
            for col_idx, day in enumerate(week):
                if day == 0:
                    continue
                
                btn = tk.Button(days_frame, text=str(day), width=4, height=1,
                               bg="#3d3d3d", fg="white",
                               activebackground="#0078d4", activeforeground="white",
                               relief="flat", font=("Segoe UI", 10),
                               command=lambda d=day: self._select_date(d))
                btn.grid(row=row_idx+1, column=col_idx, padx=2, pady=2, sticky="nsew")
        
        for i in range(7):
            days_frame.columnconfigure(i, weight=1)
        
        btn_today = tk.Button(self.top, text="Сегодня", width=10,
                             bg="#0078d4", fg="white",
                             activebackground="#005a9e",
                             relief="flat", font=("Segoe UI", 10),
                             command=lambda: self._select_date(datetime.now().day))
        btn_today.pack(pady=10)
    
    def _change_month(self, delta):
        if delta == -1:
            if self.current_date.month == 1:
                self.current_date = self.current_date.replace(year=self.current_date.year-1, month=12)
            else:
                self.current_date = self.current_date.replace(month=self.current_date.month-1)
        else:
            if self.current_date.month == 12:
                self.current_date = self.current_date.replace(year=self.current_date.year+1, month=1)
            else:
                self.current_date = self.current_date.replace(month=self.current_date.month+1)
        self._build_calendar()
    
    def _select_date(self, day):
        date_str = f"{day:02d}.{self.current_date.month:02d}.{self.current_date.year}"
        self.callback(date_str)
        self.top.destroy()

# ─── Диалог объединения ───
def show_merge_dialog(date_str, existing_hours, new_hours, total_hours):
    dialog = tk.Toplevel(root)
    dialog.title("Запись уже существует")
    dialog.geometry("420x220")
    dialog.resizable(False, False)
    dialog.configure(bg="#1e1e1e")
    dialog.transient(root)
    dialog.grab_set()
    
    result = {"action": "cancel"}
    
    ttk.Label(dialog, text=f"⚠ За {date_str} уже есть запись ({format_hours(existing_hours)})",
              font=("Segoe UI", 11, "bold")).pack(pady=15)
    ttk.Label(dialog, text=f"Новая запись: {format_hours(new_hours)}").pack()
    ttk.Label(dialog, text=f"Суммарно будет: {format_hours(total_hours)} часов",
              foreground="#ffaa00").pack(pady=5)
    
    btn_frame = ttk.Frame(dialog)
    btn_frame.pack(pady=20, fill="x", padx=20)
    
    def on_merge():
        result["action"] = "merge"
        dialog.destroy()
    def on_replace():
        result["action"] = "replace"
        dialog.destroy()
    def on_cancel():
        result["action"] = "cancel"
        dialog.destroy()
    
    ttk.Button(btn_frame, text="🔗 Объединить", command=on_merge).pack(side="left", expand=True, padx=5)
    ttk.Button(btn_frame, text="🔄 Заменить", command=on_replace).pack(side="left", expand=True, padx=5)
    ttk.Button(btn_frame, text="❌ Отмена", command=on_cancel).pack(side="left", expand=True, padx=5)
    
    dialog.wait_window()
    return result["action"]

# ─── Контейнер блоков задач ───
class TaskBlocksFrame:
    def __init__(self, parent, style_prefix=""):
        self.parent = parent
        self.style_prefix = style_prefix
        self.blocks = []  # list of (combo_var, entry_tickets, frame)
        
        self.container = ttk.Frame(parent)
        self.container.pack(fill="x", pady=5)
        
        self.btn_add = ttk.Button(self.container, text="+ Добавить блок задачи", 
                                  command=self.add_block)
        self.btn_add.pack(fill="x", pady=5)
    
    def add_block(self, template="", tickets=""):
        block_frame = ttk.Frame(self.container)
        block_frame.pack(fill="x", pady=2)
        
        combo_var = tk.StringVar(value=template)
        combo = ttk.Combobox(block_frame, textvariable=combo_var, 
                            values=TEMPLATES, width=30, state="readonly")
        combo.pack(side="left", padx=(0, 5))
        
        entry_tickets = ttk.Entry(block_frame, width=20)
        entry_tickets.pack(side="left", padx=(0, 5))
        entry_tickets.insert(0, tickets)
        
        def remove_block():
            block_frame.destroy()
            self.blocks = [(v, e, f) for v, e, f in self.blocks if f != block_frame]
        
        btn_remove = ttk.Button(block_frame, text="✕", width=3, command=remove_block)
        btn_remove.pack(side="left")
        
        self.blocks.append((combo_var, entry_tickets, block_frame))
    
    def get_blocks(self):
        """Возвращает список (template, tickets)"""
        result = []
        for combo_var, entry, frame in self.blocks:
            template = combo_var.get()
            tickets = entry.get().strip()
            if template or tickets:
                result.append((template, tickets))
        return result
    
    def clear(self):
        for _, _, frame in self.blocks:
            frame.destroy()
        self.blocks = []
    
    def set_blocks(self, blocks):
        """Заполняет блоки из списка (template, tickets)"""
        self.clear()
        for template, tickets in blocks:
            self.add_block(template, tickets)

# ─── Окно редактирования ───
class EditWindow:
    def __init__(self, parent, record, on_save, original_date=None):
        self.top = tk.Toplevel(parent)
        self.top.title("Редактировать запись")
        self.top.geometry("600x600")
        self.top.resizable(False, False)
        self.top.configure(bg="#1e1e1e")
        self.top.transient(parent)
        self.on_save = on_save
        self.original_date = original_date or record["date"]
        
        style = ttk.Style()
        style.configure("Edit.TFrame", background="#1e1e1e")
        style.configure("Edit.TLabel", background="#1e1e1e", foreground="white", font=("Segoe UI", 10))
        style.configure("Edit.TEntry", fieldbackground="#2d2d2d", foreground="white")
        style.configure("Edit.TButton", font=("Segoe UI", 10), padding=8)
        style.configure("Edit.TCheckbutton", background="#1e1e1e", foreground="white", font=("Segoe UI", 10))
        style.configure("Edit.TLabelframe", background="#1e1e1e", foreground="white")
        style.configure("Edit.TLabelframe.Label", background="#1e1e1e", foreground="white", font=("Segoe UI", 11, "bold"))
        style.configure("Edit.TCombobox", fieldbackground="#2d2d2d", foreground="white")
        
        frame = ttk.LabelFrame(self.top, text="Редактирование", padding=15, style="Edit.TLabelframe")
        frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Дата
        date_frame = ttk.Frame(frame, style="Edit.TFrame")
        date_frame.pack(fill="x", pady=5)
        
        ttk.Label(date_frame, text="Дата:", style="Edit.TLabel").pack(side="left", padx=(0, 10))
        self.entry_date = ttk.Entry(date_frame, width=12, style="Edit.TEntry")
        self.entry_date.pack(side="left")
        self.entry_date.insert(0, record["date"])
        
        def open_cal():
            CalendarPopup(self.top, 
                         lambda d: self.entry_date.delete(0, tk.END) or self.entry_date.insert(0, d),
                         self.entry_date.get())
        
        ttk.Button(date_frame, text="📅", width=3, command=open_cal).pack(side="left", padx=10)
        
        # Время
        time_frame = ttk.Frame(frame, style="Edit.TFrame")
        time_frame.pack(fill="x", pady=10)
        
        ttk.Label(time_frame, text="Начало:", style="Edit.TLabel").pack(side="left", padx=(0, 5))
        self.entry_start = ttk.Entry(time_frame, width=8, style="Edit.TEntry")
        self.entry_start.pack(side="left")
        self.entry_start.insert(0, record["start"])
        
        ttk.Label(time_frame, text="Конец:", style="Edit.TLabel").pack(side="left", padx=(20, 5))
        self.entry_end = ttk.Entry(time_frame, width=8, style="Edit.TEntry")
        self.entry_end.pack(side="left")
        self.entry_end.insert(0, record["end"])
        
        self.var_lunch = tk.BooleanVar(value=record.get("lunch", True))
        ttk.Checkbutton(time_frame, text="Вычесть 1 час обеда", 
                       variable=self.var_lunch, style="Edit.TCheckbutton").pack(side="left", padx=(30, 0))
        
        # Блоки задач
        ttk.Label(frame, text="Блоки задач:", style="Edit.TLabel").pack(anchor="w", pady=(10, 2))
        self.task_blocks = TaskBlocksFrame(frame, style_prefix="Edit.")
        
        # Парсим существующий комментарий в блоки
        blocks, extra = parse_comment_to_blocks(record["comment"])
        if blocks:
            self.task_blocks.set_blocks(blocks)
        else:
            # Если не удалось распарсить — создаем один блок с полным комментарием
            self.task_blocks.add_block("", record["comment"])
        
        # Доп. комментарий
        ttk.Label(frame, text="Доп. комментарий:", style="Edit.TLabel").pack(anchor="w", pady=(10, 2))
        self.text_extra = tk.Text(frame, height=4, font=("Segoe UI", 10),
                                  bg="#2d2d2d", fg="white", insertbackground="white",
                                  relief="flat", borderwidth=1)
        self.text_extra.pack(fill="x", pady=5)
        if extra:
            self.text_extra.insert("1.0", extra)
        
        # Кнопки
        btn_frame = ttk.Frame(frame, style="Edit.TFrame")
        btn_frame.pack(fill="x", pady=10)
        
        def save():
            date = self.entry_date.get().strip()
            start = self.entry_start.get().strip()
            end = self.entry_end.get().strip()
            lunch = self.var_lunch.get()
            blocks = self.task_blocks.get_blocks()
            extra = self.text_extra.get("1.0", tk.END).strip()
            
            if not date or not start or not end:
                messagebox.showwarning("Внимание", "Заполните дату и время!", parent=self.top)
                return
            
            comment = build_comment_from_blocks(blocks, extra)
            if not comment:
                messagebox.showwarning("Внимание", "Добавьте хотя бы один блок задач!", parent=self.top)
                return
            
            # Собираем все тикеты из блоков
            all_tickets = []
            for _, tickets in blocks:
                if tickets:
                    all_tickets.extend([t.strip() for t in tickets.split(",") if t.strip()])
            tickets_str = ", ".join(all_tickets)
            
            hours = calc_hours(start, end, lunch)
            updated = {
                "date": date,
                "start": start,
                "end": end,
                "hours": hours,
                "lunch": lunch,
                "comment": comment,
                "tickets": tickets_str,
                "blocks": blocks
            }
            
            if date != self.original_date:
                idx, existing = find_record_by_date(date)
                if existing is not None:
                    total = round(existing["hours"] + hours, 1)
                    action = show_merge_dialog(date, existing["hours"], hours, total)
                    if action == "cancel":
                        return
                    elif action == "merge":
                        merged_comment = existing["comment"] + ", " + comment
                        merged_tickets = (existing.get("tickets", "") + ", " + tickets_str).strip(", ")
                        merged = {
                            "date": date,
                            "start": existing["start"],
                            "end": end,
                            "hours": total,
                            "lunch": existing.get("lunch", True) or lunch,
                            "comment": merged_comment,
                            "tickets": merged_tickets
                        }
                        self.on_save(merged, merge_idx=idx)
                        self.top.destroy()
                        return
            
            self.on_save(updated)
            self.top.destroy()
        
        ttk.Button(btn_frame, text="💾 Сохранить", command=save).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="❌ Отмена", command=self.top.destroy).pack(side="left", padx=5)

# ─── Главное окно ───
root = tk.Tk()
root.title("Ежедневный отчёт")
root.geometry("800x850")
root.resizable(False, False)
root.configure(bg="#1e1e1e")

style = ttk.Style()
style.theme_use("clam")

style.configure("TFrame", background="#1e1e1e")
style.configure("TLabel", background="#1e1e1e", foreground="white", font=("Segoe UI", 10))
style.configure("TLabelframe", background="#1e1e1e", foreground="white", borderwidth=0)
style.configure("TLabelframe.Label", background="#1e1e1e", foreground="white", 
                font=("Segoe UI", 11, "bold"))
style.configure("TButton", font=("Segoe UI", 10), padding=8)
style.configure("TEntry", fieldbackground="#2d2d2d", foreground="white", 
                borderwidth=1, relief="flat")
style.configure("TCheckbutton", background="#1e1e1e", foreground="white", font=("Segoe UI", 10))
style.configure("TCombobox", fieldbackground="#2d2d2d", foreground="white")

reports = load_data()

# ─── Форма ввода ───
frame_form = ttk.LabelFrame(root, text="Новая запись", padding=15)
frame_form.pack(fill="x", padx=15, pady=10)

# Дата
date_frame = ttk.Frame(frame_form)
date_frame.pack(fill="x", pady=5)

ttk.Label(date_frame, text="Дата:").pack(side="left", padx=(0, 10))
entry_date = ttk.Entry(date_frame, width=12)
entry_date.pack(side="left")
entry_date.insert(0, datetime.now().strftime("%d.%m.%Y"))

def open_calendar():
    CalendarPopup(root, lambda d: entry_date.delete(0, tk.END) or entry_date.insert(0, d), 
                  entry_date.get())

btn_calendar = ttk.Button(date_frame, text="📅", width=3, command=open_calendar)
btn_calendar.pack(side="left", padx=10)

# Время
time_frame = ttk.Frame(frame_form)
time_frame.pack(fill="x", pady=10)

ttk.Label(time_frame, text="Начало:").pack(side="left", padx=(0, 5))
entry_start = ttk.Entry(time_frame, width=8)
entry_start.pack(side="left")
entry_start.insert(0, "08:00")

ttk.Label(time_frame, text="Конец:").pack(side="left", padx=(20, 5))
entry_end = ttk.Entry(time_frame, width=8)
entry_end.pack(side="left")
entry_end.insert(0, "17:00")

var_lunch = tk.BooleanVar(value=True)
chk_lunch = ttk.Checkbutton(time_frame, text="Вычесть 1 час обеда", variable=var_lunch)
chk_lunch.pack(side="left", padx=(30, 0))

# Блоки задач
ttk.Label(frame_form, text="Блоки задач:").pack(anchor="w", pady=(10, 2))
task_blocks = TaskBlocksFrame(frame_form)
task_blocks.add_block()  # Один пустой блок по умолчанию

# Доп. комментарий
ttk.Label(frame_form, text="Доп. комментарий:").pack(anchor="w", pady=(10, 2))
text_extra = tk.Text(frame_form, height=3, font=("Segoe UI", 10), 
                     bg="#2d2d2d", fg="white", insertbackground="white",
                     relief="flat", borderwidth=1)
text_extra.pack(fill="x", pady=5)

# ─── Кнопки ───
frame_btn = ttk.Frame(root)
frame_btn.pack(fill="x", padx=15, pady=10)

def add_record():
    date = entry_date.get().strip()
    start = entry_start.get().strip()
    end = entry_end.get().strip()
    lunch = var_lunch.get()
    blocks = task_blocks.get_blocks()
    extra = text_extra.get("1.0", tk.END).strip()

    if not date or not start or not end:
        messagebox.showwarning("Внимание", "Заполните дату и время!")
        return

    comment = build_comment_from_blocks(blocks, extra)
    if not comment:
        messagebox.showwarning("Внимание", "Добавьте хотя бы один блок задач!")
        return

    hours = calc_hours(start, end, lunch)
    
    # Собираем все тикеты
    all_tickets = []
    for _, tickets in blocks:
        if tickets:
            all_tickets.extend([t.strip() for t in tickets.split(",") if t.strip()])
    tickets_str = ", ".join(all_tickets)
    
    idx, existing = find_record_by_date(date)
    
    if existing is not None:
        total = round(existing["hours"] + hours, 1)
        action = show_merge_dialog(date, existing["hours"], hours, total)
        
        if action == "cancel":
            return
        elif action == "merge":
            merged = {
                "date": date,
                "start": existing["start"],
                "end": end,
                "hours": total,
                "lunch": existing.get("lunch", True) or lunch,
                "comment": existing["comment"] + ", " + comment,
                "tickets": (existing.get("tickets", "") + ", " + tickets_str).strip(", "),
                "blocks": existing.get("blocks", []) + blocks
            }
            reports[idx] = merged
            save_data(reports)
            refresh_list()
            _clear_form()
            messagebox.showinfo("Готово", f"Запись за {date} объединена! Итого: {format_hours(total)}")
            return
    
    record = {
        "date": date,
        "start": start,
        "end": end,
        "hours": hours,
        "lunch": lunch,
        "comment": comment,
        "tickets": tickets_str,
        "blocks": blocks
    }
    
    if existing is not None:
        reports[idx] = record
        msg = f"Запись за {date} заменена! ({format_hours(hours)})"
    else:
        reports.append(record)
        lunch_text = " (с учётом обеда)" if lunch else ""
        msg = f"Запись за {date} добавлена! ({format_hours(hours)}){lunch_text}"
    
    save_data(reports)
    refresh_list()
    _clear_form()
    messagebox.showinfo("Готово", msg)

def _clear_form():
    task_blocks.clear()
    task_blocks.add_block()
    text_extra.delete("1.0", tk.END)

btn_add = ttk.Button(frame_btn, text="➕ Добавить запись", command=add_record)
btn_add.pack(side="left", padx=5)

def delete_selected():
    sel = listbox.curselection()
    if not sel:
        messagebox.showwarning("Внимание", "Выберите запись!")
        return
    idx = sel[0]
    if messagebox.askyesno("Удалить", f"Удалить запись за {reports[idx]['date']}?"):
        reports.pop(idx)
        save_data(reports)
        refresh_list()

btn_del = ttk.Button(frame_btn, text="🗑 Удалить", command=delete_selected)
btn_del.pack(side="left", padx=5)

# ─── Список записей + контекстное меню ───
frame_list = ttk.LabelFrame(root, text="Записи", padding=10)
frame_list.pack(fill="both", expand=True, padx=15, pady=10)

listbox = tk.Listbox(frame_list, font=("Segoe UI", 10), bg="#2d2d2d", fg="white",
                     selectbackground="#0078d4", selectforeground="white",
                     activestyle="none", borderwidth=0, relief="flat")
listbox.pack(fill="both", expand=True)

context_menu = tk.Menu(root, tearoff=0, bg="#2d2d2d", fg="white",
                       activebackground="#0078d4", activeforeground="white",
                       font=("Segoe UI", 10), borderwidth=1)
context_menu.add_command(label="✏️ Редактировать", command=lambda: edit_selected())
context_menu.add_separator()
context_menu.add_command(label="🗑 Удалить", command=lambda: delete_selected())

def show_context_menu(event):
    idx = listbox.nearest(event.y)
    if idx >= 0 and idx < len(reports):
        listbox.selection_clear(0, tk.END)
        listbox.selection_set(idx)
        listbox.activate(idx)
        context_menu.post(event.x_root, event.y_root)

listbox.bind("<Button-3>", show_context_menu)

def edit_selected():
    sel = listbox.curselection()
    if not sel:
        return
    idx = sel[0]
    
    def on_save(updated, merge_idx=None):
        if merge_idx is not None:
            reports[merge_idx] = updated
        else:
            reports[idx] = updated
        save_data(reports)
        refresh_list()
        messagebox.showinfo("Готово", f"Запись за {updated['date']} обновлена!")
    
    EditWindow(root, reports[idx], on_save, original_date=reports[idx]["date"])

def refresh_list():
    listbox.delete(0, tk.END)
    for r in reports:
        lunch_mark = " 🍽" if r.get("lunch", False) else ""
        tickets_mark = f" 🎫{r.get('tickets', '')}" if r.get('tickets') else ""
        listbox.insert(tk.END, f"{r['date']}  |  {r['start']}–{r['end']}  ({format_hours(r['hours'])}){lunch_mark}{tickets_mark}  |  {r['comment'][:45]}...")

refresh_list()

# ─── Экспорт ───
frame_export = ttk.Frame(root)
frame_export.pack(fill="x", padx=15, pady=10)

def export_all():
    path = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Text files", "*.txt")],
        initialfile="report_work.txt"
    )
    if not path:
        return
    with open(path, "w", encoding="utf-8") as f:
        for r in reports:
            f.write(f"{r['date']}\n")
            f.write(f"отработано с {r['start']} до {r['end']} ({format_hours(r['hours'])})\n")
            f.write(f"Комментарий {r['comment']}\n")
            f.write("-" * 60 + "\n")
    messagebox.showinfo("Экспорт", f"Всё экспортировано в {path}")

def export_range():
    win = tk.Toplevel(root)
    win.title("Экспорт по диапазону")
    win.geometry("400x250")
    win.resizable(False, False)
    win.configure(bg="#1e1e1e")
    win.transient(root)
    
    ttk.Label(win, text="Дата от:").pack(pady=(15, 2))
    frame_from = ttk.Frame(win)
    frame_from.pack()
    e_from = ttk.Entry(frame_from, width=12)
    e_from.pack(side="left")
    
    def open_cal_from():
        CalendarPopup(win, lambda d: e_from.delete(0, tk.END) or e_from.insert(0, d), e_from.get())
    ttk.Button(frame_from, text="📅", width=3, command=open_cal_from).pack(side="left", padx=5)
    
    ttk.Label(win, text="Дата до:").pack(pady=(10, 2))
    frame_to = ttk.Frame(win)
    frame_to.pack()
    e_to = ttk.Entry(frame_to, width=12)
    e_to.pack(side="left")
    
    def open_cal_to():
        CalendarPopup(win, lambda d: e_to.delete(0, tk.END) or e_to.insert(0, d), e_to.get())
    ttk.Button(frame_to, text="📅", width=3, command=open_cal_to).pack(side="left", padx=5)

    def do_export():
        d_from = e_from.get().strip()
        d_to = e_to.get().strip()
        try:
            df = datetime.strptime(d_from, "%d.%m.%Y")
            dt = datetime.strptime(d_to, "%d.%m.%Y")
        except:
            messagebox.showerror("Ошибка", "Неверный формат даты!")
            return

        filtered = [r for r in reports
                    if df <= datetime.strptime(r["date"], "%d.%m.%Y") <= dt]

        if not filtered:
            messagebox.showinfo("Результат", "Нет записей за этот период.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            initialfile=f"report_{d_from}_{d_to}.txt"
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            for r in filtered:
                f.write(f"{r['date']}\n")
                f.write(f"отработано с {r['start']} до {r['end']} ({format_hours(r['hours'])})\n")
                f.write(f"Комментарий {r['comment']}\n")
                f.write("-" * 60 + "\n")
        messagebox.showinfo("Экспорт", f"Экспортировано {len(filtered)} записей в {path}")
        win.destroy()

    ttk.Button(win, text="📄 Экспортировать", command=do_export).pack(pady=20)

btn_exp_all = ttk.Button(frame_export, text="📄 Экспорт ВСЁ в txt", command=export_all)
btn_exp_all.pack(side="left", padx=5)

btn_exp_range = ttk.Button(frame_export, text="📄 Экспорт по диапазону", command=export_range)
btn_exp_range.pack(side="left", padx=5)

root.mainloop()