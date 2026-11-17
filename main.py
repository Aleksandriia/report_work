import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import matplotlib
matplotlib.use('TkAgg')

matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['font.sans-serif'] = ['Arial', 'Helvetica']

from config import IS_MAC, FONT, TEMPLATES
from logic import (
    load_data, save_data, load_templates, save_templates, 
    calc_hours, format_hours, build_comment_from_blocks, 
    find_record_by_date, sort_reports, show_merge_dialog,
    load_settings, save_settings
)
from widgets import CalendarPopup, TaskBlocksFrame
from windows import (
    TemplatesWindow, ImportWindow, AnalyticsWindow, 
    SalaryCalculator, VacationCalculator, PomodoroWindow, 
    ReminderWindow, EditWindow, DailyReminderSettings
)

# ─── Глобальные переменные приложения ───
reports = []
current_month_filter = None

root = None
listbox = None
total_label = None
combo_filter = None

entry_date = None
entry_start = None
entry_end = None
var_lunch = None
task_blocks = None
text_extra = None

# ═══════════════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ГЛАВНОГО ОКНА
# ═══════════════════════════════════════════════════════════

def refresh_combobox_values():
    def _update(widget):
        if isinstance(widget, ttk.Combobox):
            widget.configure(values=TEMPLATES)
        for child in widget.winfo_children():
            _update(child)
    if root:
        _update(root)

def get_unique_months():
    months = set()
    for r in reports:
        try:
            d = datetime.strptime(r["date"], "%d.%m.%Y")
            months.add((d.year, d.month))
        except: pass
    return sorted(months)

def month_label(year, month):
    names = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
    return f"{names[month-1]} {year}"

def update_month_filter():
    if combo_filter:
        combo_filter['values'] = ["Все"] + [month_label(y, m) for y, m in get_unique_months()]

def refresh_list():
    if not listbox: return
    listbox.delete(0, tk.END)
    sort_reports(reports)
    
    for r in reports:
        if current_month_filter is not None:
            try:
                d = datetime.strptime(r["date"], "%d.%m.%Y")
                filter_key = f"{d.month:02d}.{d.year}"
                if filter_key != current_month_filter: continue
            except: continue
        
        lunch_mark = " 🍽" if r.get("lunch", False) else ""
        tickets_mark = f" 🎫{r.get('tickets', '')}" if r.get('tickets') else ""
        listbox.insert(tk.END, f"{r['date']}  |  {r['start']}–{r['end']}  ({format_hours(r['hours'])}){lunch_mark}{tickets_mark}  |  {r['comment'][:45]}...")
    
    update_month_filter()
    if total_label:
        total_label.config(text=f"{listbox.size()} из {len(reports)}")

def _clear_form():
    if task_blocks: task_blocks.clear(); task_blocks.add_block()
    if text_extra: text_extra.delete("1.0", tk.END)

def add_record():
    date = entry_date.get().strip(); start = entry_start.get().strip(); end = entry_end.get().strip()
    lunch = var_lunch.get(); blocks = task_blocks.get_blocks(); extra = text_extra.get("1.0", tk.END).strip()

    if not date or not start or not end:
        messagebox.showwarning("Внимание", "Заполните дату и время!"); return

    comment = build_comment_from_blocks(blocks, extra)
    if not comment:
        messagebox.showwarning("Внимание", "Добавьте хотя бы один блок задач!"); return

    hours = calc_hours(start, end, lunch)
    all_tickets = []
    for _, tickets in blocks:
        if tickets: all_tickets.extend([t.strip() for t in tickets.split(",") if t.strip()])
    tickets_str = ", ".join(all_tickets)
    
    idx, existing = find_record_by_date(reports, date)
    
    if existing is not None:
        total = round(existing["hours"] + hours, 1)
        action = show_merge_dialog(root, date, existing["hours"], hours, total)
        if action == "cancel": return
        elif action == "merge":
            merged = {
                "date": date, "start": existing["start"], "end": end,
                "hours": total, "lunch": existing.get("lunch", True) or lunch,
                "comment": existing["comment"] + ", " + comment,
                "tickets": (existing.get("tickets", "") + ", " + tickets_str).strip(", "),
                "blocks": existing.get("blocks", []) + blocks
            }
            reports[idx] = merged; sort_reports(reports); save_data(reports); refresh_list(); _clear_form()
            messagebox.showinfo("Готово", f"Запись за {date} объединена! Итого: {format_hours(total)}")
            return
    
    record = {"date": date, "start": start, "end": end, "hours": hours, "lunch": lunch, "comment": comment, "tickets": tickets_str, "blocks": blocks}
    if existing is not None: reports[idx] = record; msg = f"Запись за {date} заменена! ({format_hours(hours)})"
    else:
        reports.append(record); lunch_text = " (с учётом обеда)" if lunch else ""
        msg = f"Запись за {date} добавлена! ({format_hours(hours)}){lunch_text}"

    sort_reports(reports); save_data(reports); refresh_list(); _clear_form()
    messagebox.showinfo("Готово", msg)

def delete_selected():
    sel = listbox.curselection()
    if not sel:
        messagebox.showwarning("Внимание", "Выберите запись!"); return
    idx = sel[0]
    if messagebox.askyesno("Удалить", f"Удалить запись за {reports[idx]['date']}?"):
        reports.pop(idx); save_data(reports); refresh_list()

def edit_selected():
    sel = listbox.curselection()
    if not sel: return
    idx = sel[0]
    
    def on_save(updated, merge_idx=None):
        if merge_idx is not None: reports[merge_idx] = updated
        else: reports[idx] = updated
        save_data(reports); refresh_list()
        messagebox.showinfo("Готово", f"Запись за {updated['date']} обновлена!")
    
    EditWindow(root, reports, reports[idx], on_save, original_date=reports[idx]["date"])

def on_filter_change(event):
    global current_month_filter
    sel = combo_filter.get()
    if sel == "Все": current_month_filter = None
    else:
        names = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
        parts = sel.split()
        current_month_filter = f"{names.index(parts[0])+1:02d}.{parts[1]}"
    refresh_list()

def show_context_menu(event):
    idx = listbox.nearest(event.y)
    if idx >= 0 and idx < len(reports):
        listbox.selection_clear(0, tk.END); listbox.selection_set(idx); listbox.activate(idx)
        context_menu.post(event.x_root, event.y_root)

# ─── Функции экспорта ───
def export_all():
    path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")], initialfile="report_work.txt")
    if not path: return
    with open(path, "w", encoding="utf-8") as f:
        for r in reports:
            f.write(f"{r['date']}\nотработано с {r['start']} до {r['end']} ({format_hours(r['hours'])})\nКомментарий {r['comment']}\n" + "-"*60 + "\n")
    messagebox.showinfo("Экспорт", f"Всё экспортировано в {path}")

def export_range():
    win = tk.Toplevel(root); win.title("Экспорт по диапазону"); win.geometry("400x250"); win.resizable(False, False)
    if not IS_MAC: win.configure(bg="#1e1e1e")
    win.transient(root)
    if IS_MAC: win.lift(); win.focus_force()
    
    ttk.Label(win, text="Дата от:").pack(pady=(15, 2))
    frame_from = ttk.Frame(win); frame_from.pack()
    e_from = ttk.Entry(frame_from, width=12); e_from.pack(side="left")
    ttk.Button(frame_from, text="📅", width=3, command=lambda: CalendarPopup(win, lambda d: e_from.delete(0, tk.END) or e_from.insert(0, d), e_from.get())).pack(side="left", padx=5)
    
    ttk.Label(win, text="Дата до:").pack(pady=(10, 2))
    frame_to = ttk.Frame(win); frame_to.pack()
    e_to = ttk.Entry(frame_to, width=12); e_to.pack(side="left")
    ttk.Button(frame_to, text="📅", width=3, command=lambda: CalendarPopup(win, lambda d: e_to.delete(0, tk.END) or e_to.insert(0, d), e_to.get())).pack(side="left", padx=5)

    def do_export():
        try:
            df = datetime.strptime(e_from.get().strip(), "%d.%m.%Y"); dt = datetime.strptime(e_to.get().strip(), "%d.%m.%Y")
        except: messagebox.showerror("Ошибка", "Неверный формат даты!"); return
        filtered = [r for r in reports if df <= datetime.strptime(r["date"], "%d.%m.%Y") <= dt]
        if not filtered: messagebox.showinfo("Результат", "Нет записей за этот период."); return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")], initialfile=f"report_{e_from.get()}_{e_to.get()}.txt")
        if not path: return
        with open(path, "w", encoding="utf-8") as f:
            for r in filtered:
                f.write(f"{r['date']}\nотработано с {r['start']} до {r['end']} ({format_hours(r['hours'])})\nКомментарий {r['comment']}\n" + "-"*60 + "\n")
        messagebox.showinfo("Экспорт", f"Экспортировано {len(filtered)} записей в {path}"); win.destroy()

    ttk.Button(win, text="📄 Экспортировать", command=do_export).pack(pady=20)

last_reminder_date = None

# --- Фоновая проверка. Напоминание ---
def check_daily_reminder():
    """Фоновая проверка: не пора ли напомнить о заполнении отчета"""
    global last_reminder_date
    
    settings = load_settings()
    if not settings.get("daily_reminder_enabled"):
        root.after(60000, check_daily_reminder) # Проверить через минуту
        return

    now = datetime.now()
    target_time = settings.get("daily_reminder_time", "18:30")
    current_time_str = now.strftime("%H:%M")

    # Если время совпало и мы еще не напоминали сегодня
    if current_time_str == target_time and last_reminder_date != now.strftime("%d.%m.%Y"):
        last_reminder_date = now.strftime("%d.%m.%Y")
        
        # Проверяем, есть ли запись за сегодня
        today_str = now.strftime("%d.%m.%Y")
        has_record = any(r["date"] == today_str for r in reports)
        
        if not has_record:
            root.bell()
            messagebox.showwarning("⏰ Напоминание", 
                                   f"Привет! Уже {target_time}, а отчета за сегодня ({today_str}) еще нет.\n\nПора записать свои задачи!")

    # Проверяем каждую минуту
    root.after(60000, check_daily_reminder)

# ═══════════════════════════════════════════════════════════
# ПОСТРОЕНИЕ ИНТЕРФЕЙСА
# ═══════════════════════════════════════════════════════════

def build_menu():
    menubar = tk.Menu(root)
    if IS_MAC:
        app_menu = tk.Menu(menubar, tearoff=0, name="apple")
        menubar.add_cascade(label="Отчёт", menu=app_menu)
        app_menu.add_command(label="О программе", command=lambda: messagebox.showinfo("О программе", "Ежедневный отчёт v1.0"))
        app_menu.add_separator()
    root.config(menu=menubar)

    file_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="📁 Файл", menu=file_menu)
    file_menu.add_command(label="📥 Импорт из txt...", command=lambda: ImportWindow(root, reports, on_import_success=refresh_list))
    file_menu.add_separator()
    file_menu.add_command(label="📄 Экспорт ВСЁ в txt", command=export_all)
    file_menu.add_command(label="📄 Экспорт по диапазону...", command=export_range)
    file_menu.add_separator()
    file_menu.add_command(label="🚪 Выход", command=root.quit)

    settings_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="⚙ Настройки", menu=settings_menu)
    settings_menu.add_command(label="📝 Управление шаблонами...", command=lambda: TemplatesWindow(root, on_close=refresh_combobox_values))

    analytics_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="📊 Аналитика", menu=analytics_menu)
    analytics_menu.add_command(label="📈 Открыть аналитику", command=lambda: AnalyticsWindow(root, reports))

    tools_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="🧰 Инструменты", menu=tools_menu)
    tools_menu.add_command(label="💰 Калькулятор зарплаты", command=lambda: SalaryCalculator(root, reports))
    tools_menu.add_command(label="🏖️ Калькулятор отпуска", command=lambda: VacationCalculator(root))
    tools_menu.add_separator()
    tools_menu.add_command(label="⏱ Помодоро (Таймер)", command=lambda: PomodoroWindow(root))
    tools_menu.add_command(label="🔔 Создать напоминание", command=lambda: ReminderWindow(root))

    tools_menu.add_separator()
    tools_menu.add_command(label="⏰ Настройка ежедневного напоминания", 
                           command=lambda: DailyReminderSettings(root, on_save=lambda: messagebox.showinfo("Готово", "Настройки напоминания сохранены!")))

    help_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="❓ Справка", menu=help_menu)
    help_menu.add_command(label="О программе", command=lambda: messagebox.showinfo("О программе", "Ежедневный отчёт v1.0\n\nПриложение для ведения отчётов о работе."))

def build_main_form():
    global entry_date, entry_start, entry_end, var_lunch, task_blocks, text_extra
    
    if IS_MAC:
        frame_form = tk.Frame(root); frame_form.pack(fill="x", padx=15, pady=10)
        tk.Label(frame_form, text="Новая запись", font=(FONT, 12, "bold")).pack(anchor="w", pady=(0, 10))
    else:
        frame_form = ttk.LabelFrame(root, text="Новая запись", padding=15); frame_form.pack(fill="x", padx=15, pady=10)

    date_frame = ttk.Frame(frame_form); date_frame.pack(fill="x", pady=5)
    ttk.Label(date_frame, text="Дата:").pack(side="left", padx=(0, 10))
    entry_date = ttk.Entry(date_frame, width=12); entry_date.pack(side="left")
    entry_date.insert(0, datetime.now().strftime("%d.%m.%Y"))
    ttk.Button(date_frame, text="📅", width=3, command=lambda: CalendarPopup(root, lambda d: entry_date.delete(0, tk.END) or entry_date.insert(0, d), entry_date.get())).pack(side="left", padx=10)

    time_frame = ttk.Frame(frame_form); time_frame.pack(fill="x", pady=10)
    ttk.Label(time_frame, text="Начало:").pack(side="left", padx=(0, 5))
    entry_start = ttk.Entry(time_frame, width=8); entry_start.pack(side="left"); entry_start.insert(0, "08:00")
    ttk.Label(time_frame, text="Конец:").pack(side="left", padx=(20, 5))
    entry_end = ttk.Entry(time_frame, width=8); entry_end.pack(side="left"); entry_end.insert(0, "17:00")

    var_lunch = tk.BooleanVar(value=True)
    ttk.Checkbutton(time_frame, text="Вычесть 1 час обеда", variable=var_lunch).pack(side="left", padx=(30, 0))

    ttk.Label(frame_form, text="Блоки задач:").pack(anchor="w", pady=(10, 2))
    task_blocks = TaskBlocksFrame(frame_form); task_blocks.add_block()

    ttk.Label(frame_form, text="Доп. комментарий:").pack(anchor="w", pady=(10, 2))
    if IS_MAC: text_extra = tk.Text(frame_form, height=3, font=(FONT, 10), relief="solid", borderwidth=1)
    else: text_extra = tk.Text(frame_form, height=3, font=(FONT, 10), bg="#2d2d2d", fg="white", insertbackground="white", relief="flat", borderwidth=1)
    text_extra.pack(fill="x", pady=5)

def build_bottom_section():
    global combo_filter, total_label, listbox, context_menu
    
    frame_btn = ttk.Frame(root); frame_btn.pack(fill="x", padx=15, pady=10)
    ttk.Button(frame_btn, text="➕ Добавить запись", command=add_record).pack(side="left", padx=5)
    ttk.Button(frame_btn, text="🗑 Удалить", command=delete_selected).pack(side="left", padx=5)

    filter_frame = ttk.Frame(root); filter_frame.pack(fill="x", padx=15, pady=(0, 5))
    ttk.Label(filter_frame, text="Показать:").pack(side="left", padx=(0, 5))
    combo_filter = ttk.Combobox(filter_frame, state="readonly", width=20); combo_filter.pack(side="left"); combo_filter.set("Все")
    combo_filter.bind("<<ComboboxSelected>>", on_filter_change)

    ttk.Label(filter_frame, text="Всего записей:").pack(side="left", padx=(20, 5))
    total_label = ttk.Label(filter_frame, text="0"); total_label.pack(side="left")

    if IS_MAC:
        frame_list = tk.Frame(root); frame_list.pack(fill="both", expand=True, padx=15, pady=10)
        tk.Label(frame_list, text="Записи", font=(FONT, 12, "bold")).pack(anchor="w", pady=(0, 10))
    else:
        frame_list = ttk.LabelFrame(root, text="Записи", padding=10); frame_list.pack(fill="both", expand=True, padx=15, pady=10)

    if IS_MAC: listbox = tk.Listbox(frame_list, font=(FONT, 12), relief="solid", borderwidth=1)
    else: listbox = tk.Listbox(frame_list, font=(FONT, 10), bg="#2d2d2d", fg="white", selectbackground="#0078d4", selectforeground="white", activestyle="none", borderwidth=0, relief="flat")
    listbox.pack(fill="both", expand=True)
    listbox.bind("<Button-3>", show_context_menu)
    if IS_MAC: listbox.bind("<Control-Button-1>", show_context_menu)

    context_menu = tk.Menu(root, tearoff=0)
    context_menu.add_command(label="✏️ Редактировать", command=edit_selected)
    context_menu.add_separator()
    context_menu.add_command(label="🗑 Удалить", command=delete_selected)

# ═══════════════════════════════════════════════════════════
# ТОЧКА ВХОДА
# ═══════════════════════════════════════════════════════════

def main():
    global root, reports, TEMPLATES
    
    root = tk.Tk()
    root.title("Ежедневный отчёт"); root.geometry("800x850")
    if not IS_MAC: root.configure(bg="#1e1e1e")

    style = ttk.Style()
    if IS_MAC:
        try: style.theme_use("aqua")
        except tk.TclError: style.theme_use("default")
    else:
        style.theme_use("clam")
        style.configure("TFrame", background="#1e1e1e"); style.configure("TLabel", background="#1e1e1e", foreground="white", font=(FONT, 10))
        style.configure("TLabelframe", background="#1e1e1e", foreground="white", borderwidth=0); style.configure("TLabelframe.Label", background="#1e1e1e", foreground="white", font=(FONT, 11, "bold"))
        style.configure("TButton", font=(FONT, 10), padding=8); style.configure("TEntry", fieldbackground="#2d2d2d", foreground="white", borderwidth=1, relief="flat")
        style.configure("TCheckbutton", background="#1e1e1e", foreground="white", font=(FONT, 10)); style.configure("TCombobox", fieldbackground="#2d2d2d", foreground="white")

    reports.extend(load_data())
    TEMPLATES.extend(load_templates())

    build_menu(); build_main_form(); build_bottom_section()

    root.bind("<Control-i>", lambda e: ImportWindow(root, reports, on_import_success=refresh_list))
    root.bind("<Control-n>", lambda e: entry_date.focus())
    root.bind("<Control-s>", lambda e: export_all())

    refresh_list()
    root.update_idletasks(); root.update()
    # Запускаем фоновую проверку напоминаний
    root.after(1000, check_daily_reminder)
    
    root.mainloop()

if __name__ == "__main__":
    main()