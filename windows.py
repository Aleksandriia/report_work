import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from config import FONT, IS_MAC, TEMPLATES
from logic import (
    calc_hours, format_hours, parse_txt_file, parse_comment_to_blocks, 
    build_comment_from_blocks, sort_reports, save_data, save_templates,
    find_record_by_date, show_merge_dialog
)
from widgets import CalendarPopup, TaskBlocksFrame

# ─── Окно управления шаблонами ───
class TemplatesWindow:
    def __init__(self, parent, on_close):
        self.top = tk.Toplevel(parent)
        self.top.title("Управление шаблонами")
        self.top.geometry("650x550")
        self.top.resizable(False, False)
        if IS_MAC:
            self.top.update_idletasks()
            self.top.lift()
            self.top.focus_force()
        self.top.transient(parent)
        self.on_close = on_close
        
        frame = ttk.LabelFrame(self.top, text="Шаблоны комментариев", padding=15)
        frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        self.listbox = tk.Listbox(frame, font=(FONT, 10), bg="#2d2d2d", fg="white",
                                  selectbackground="#0078d4", selectforeground="white",
                                  activestyle="none", borderwidth=0, relief="flat", height=15)
        self.listbox.pack(fill="both", expand=True, pady=(0, 10))
        
        self._refresh_list()
        
        input_frame = ttk.Frame(frame)
        input_frame.pack(fill="x", pady=5)
        
        ttk.Label(input_frame, text="Шаблон:").pack(side="left", padx=(0, 5))
        self.entry_new = ttk.Entry(input_frame, width=55)
        self.entry_new.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        btn_frame1 = ttk.Frame(frame)
        btn_frame1.pack(fill="x", pady=5)
        
        btn_frame2 = ttk.Frame(frame)
        btn_frame2.pack(fill="x", pady=5)
        
        def add_template():
            text = self.entry_new.get().strip()
            if not text:
                messagebox.showwarning("Внимание", "Введите текст шаблона!")
                return
            TEMPLATES.append(text)
            save_templates(TEMPLATES)
            self.entry_new.delete(0, tk.END)
            self._refresh_list()
            if self.on_close: self.on_close()
        
        def edit_template():
            sel = self.listbox.curselection()
            if not sel:
                messagebox.showwarning("Внимание", "Выберите шаблон!")
                return
            idx = sel[0]
            text = self.entry_new.get().strip()
            if not text:
                messagebox.showwarning("Внимание", "Введите новый текст!")
                return
            TEMPLATES[idx] = text
            save_templates(TEMPLATES)
            self.entry_new.delete(0, tk.END)
            self._refresh_list()
            if self.on_close: self.on_close()
        
        def delete_template():
            sel = self.listbox.curselection()
            if not sel:
                messagebox.showwarning("Внимание", "Выберите шаблон!")
                return
            idx = sel[0]
            if messagebox.askyesno("Удалить", f"Удалить шаблон:\n{TEMPLATES[idx]}?"):
                TEMPLATES.pop(idx)
                save_templates(TEMPLATES)
                self.entry_new.delete(0, tk.END)
                self._refresh_list()
                if self.on_close: self.on_close()
        
        def move_up():
            sel = self.listbox.curselection()
            if not sel or sel[0] == 0:
                return
            idx = sel[0]
            TEMPLATES[idx], TEMPLATES[idx-1] = TEMPLATES[idx-1], TEMPLATES[idx]
            save_templates(TEMPLATES)
            self._refresh_list()
            self.listbox.selection_set(idx-1)
            if self.on_close: self.on_close()
        
        def move_down():
            sel = self.listbox.curselection()
            if not sel or sel[0] >= len(TEMPLATES)-1:
                return
            idx = sel[0]
            TEMPLATES[idx], TEMPLATES[idx+1] = TEMPLATES[idx+1], TEMPLATES[idx]
            save_templates(TEMPLATES)
            self._refresh_list()
            self.listbox.selection_set(idx+1)
            if self.on_close: self.on_close()
        
        def on_select(event):
            sel = self.listbox.curselection()
            if sel:
                self.entry_new.delete(0, tk.END)
                self.entry_new.insert(0, TEMPLATES[sel[0]])
        
        self.listbox.bind("<<ListboxSelect>>", on_select)
        
        ttk.Button(btn_frame1, text="➕ Добавить", command=add_template).pack(side="left", padx=5)
        ttk.Button(btn_frame1, text="✏️ Редактировать", command=edit_template).pack(side="left", padx=5)
        ttk.Button(btn_frame1, text="🗑 Удалить", command=delete_template).pack(side="left", padx=5)
        
        ttk.Button(btn_frame2, text="⬆ Вверх", command=move_up).pack(side="left", padx=5)
        ttk.Button(btn_frame2, text="⬇ Вниз", command=move_down).pack(side="left", padx=5)
        
        ttk.Button(self.top, text="Закрыть", command=self.top.destroy).pack(pady=10)
    
    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        for i, t in enumerate(TEMPLATES):
            self.listbox.insert(tk.END, f"{i+1}. {t}")

# ─── Окно импорта ───
class ImportWindow:
    def __init__(self, parent, reports, on_import_success):
        self.reports = reports
        self.on_import_success = on_import_success
        self.top = tk.Toplevel(parent)
        self.top.title("Импорт записей")
        self.top.geometry("700x600")
        self.top.resizable(False, False)
        if IS_MAC:
            self.top.update_idletasks()
            self.top.lift()
            self.top.focus_force()
        self.top.transient(parent)
        
        frame = ttk.LabelFrame(self.top, text="Предпросмотр импорта", padding=15)
        frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=(0, 10))
        
        self.file_label = ttk.Label(btn_frame, text="Файл не выбран")
        self.file_label.pack(side="left", padx=(0, 10))
        
        self.imported_records = []
        self.check_vars = []
        
        self.list_container = ttk.Frame(frame)
        self.list_container.pack(fill="both", expand=True)
        
        import_btn_frame = ttk.Frame(frame)
        import_btn_frame.pack(fill="x", pady=(10, 0))
        
        self.import_btn = ttk.Button(import_btn_frame, text="📥 Импортировать выбранные", 
                                      command=lambda: None, state="disabled")
        self.import_btn.pack(side="left", padx=5)
        
        self.count_label = ttk.Label(import_btn_frame, text="")
        self.count_label.pack(side="left", padx=10)
        
        def choose_file():
            path = filedialog.askopenfilename(
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            if not path:
                return
            
            self.imported_records = parse_txt_file(path)
            self.file_label.config(text=f"📄 {os.path.basename(path)} ({len(self.imported_records)} записей)")
            
            for widget in self.list_container.winfo_children():
                widget.destroy()
            
            if not self.imported_records:
                ttk.Label(self.list_container, text="❌ Записи не найдены в файле").pack(pady=20)
                self.import_btn.config(state="disabled")
                self.count_label.config(text="")
                return
            
            canvas = tk.Canvas(self.list_container, bg="#1e1e1e", highlightthickness=0, height=350)
            scrollbar = ttk.Scrollbar(self.list_container, orient="vertical", command=canvas.yview)
            self.scroll_frame = ttk.Frame(canvas)
            
            self.scroll_frame.bind("<Configure>", 
                lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            
            canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            self.check_vars = []
            for i, rec in enumerate(self.imported_records):
                var = tk.BooleanVar(value=True)
                self.check_vars.append(var)
                
                row = ttk.Frame(self.scroll_frame)
                row.pack(fill="x", pady=2)
                
                ttk.Checkbutton(row, variable=var, 
                               command=lambda: update_count()).pack(side="left")
                ttk.Label(row, text=f"{rec['date']}  |  {rec['start']}–{rec['end']}  |  {rec['comment'][:60]}...").pack(side="left", padx=5)
            
            self.import_btn.config(state="normal", command=do_import)
            update_count()
        
        def update_count():
            count = sum(1 for v in self.check_vars if v.get())
            self.count_label.config(text=f"Выбрано: {count} из {len(self.imported_records)}")
        
        def do_import():
            if not self.imported_records:
                messagebox.showwarning("Внимание", "Сначала выберите файл!")
                return
            
            imported_count = 0
            skipped_count = 0
            
            for i, rec in enumerate(self.imported_records):
                if not self.check_vars[i].get():
                    continue
                
                date = rec["date"]
                start = rec["start"]
                end = rec["end"]
                comment = rec["comment"]
                
                idx, existing = find_record_by_date(self.reports, date)
                
                if existing is not None:
                    action = show_merge_dialog(self.top, date, existing["hours"], 
                                              calc_hours(start, end, True), 
                                              round(existing["hours"] + calc_hours(start, end, True), 1))
                    if action == "cancel":
                        skipped_count += 1
                        continue
                    elif action == "merge":
                        hours = calc_hours(start, end, True)
                        merged = {
                            "date": date,
                            "start": existing["start"],
                            "end": end,
                            "hours": round(existing["hours"] + hours, 1),
                            "lunch": True,
                            "comment": existing["comment"] + ", " + comment,
                            "tickets": "",
                            "blocks": []
                        }
                        self.reports[idx] = merged
                        imported_count += 1
                        continue
                
                hours = calc_hours(start, end, True)
                blocks, extra = parse_comment_to_blocks(comment, TEMPLATES)
                if not blocks:
                    blocks = [("", comment)]
                
                record = {
                    "date": date, "start": start, "end": end,
                    "hours": hours, "lunch": True,
                    "comment": comment, "tickets": "", "blocks": blocks
                }
                
                if existing is not None:
                    self.reports[idx] = record
                else:
                    self.reports.append(record)
                imported_count += 1

            sort_reports(self.reports)
            save_data(self.reports)
            if self.on_import_success: self.on_import_success()
            messagebox.showinfo("Импорт завершён", 
                               f"Импортировано: {imported_count}\nПропущено: {skipped_count}")
            self.top.destroy()
        
        ttk.Button(btn_frame, text="📂 Выбрать файл", command=choose_file).pack(side="left")
        ttk.Button(self.top, text="Отмена", command=self.top.destroy).pack(pady=10)

# ─── Окно аналитики ───
class AnalyticsWindow:
    def __init__(self, parent, reports):
        self.reports = reports
        self.top = tk.Toplevel(parent)
        self.top.title("📊 Аналитика работы")
        self.top.geometry("1400x900")
        self.top.resizable(False, False)
        if IS_MAC:
            self.top.update_idletasks()
            self.top.lift()
            self.top.focus_force()
        self.top.transient(parent)
        
        top_frame = ttk.Frame(self.top)
        top_frame.pack(fill="x", padx=15, pady=10)
        
        ttk.Label(top_frame, text="Период:").pack(side="left", padx=(0, 5))
        
        self.combo_period = ttk.Combobox(top_frame, 
            values=["Последние 7 дней", "Последние 30 дней", "Текущий месяц", "Всё время"],
            state="readonly", width=20)
        self.combo_period.pack(side="left", padx=5)
        self.combo_period.set("Всё время")
        self.combo_period.bind("<<ComboboxSelected>>", lambda e: self.draw())
        
        ttk.Button(top_frame, text="🔄 Обновить", command=self.draw).pack(side="left", padx=10)
        
        stats_frame = ttk.Frame(self.top)
        stats_frame.pack(fill="x", padx=15, pady=5)
        
        self.stat_labels = {}
        stats = [
            ("Всего часов", "white"), ("Рабочих дней", "white"),
            ("Среднее ч/день", "#ffd93d"), ("Создано тикетов", "#ff6b6b"),
            ("Протестировано", "#4ecdc4"), ("Тикетов/день", "#00ff88"),
        ]
        for key, color in stats:
            lbl = ttk.Label(stats_frame, text=f"{key}: 0", font=(FONT, 10, "bold"), foreground=color)
            lbl.pack(side="left", padx=12)
            self.stat_labels[key] = lbl
        
        self.fig, self.axes = plt.subplots(2, 3, figsize=(18, 11))
        self.fig.patch.set_facecolor('#1e1e1e')
        self.fig.suptitle("Аналитика работы", color='white', fontsize=16, fontweight='bold', y=0.98)
        
        for ax in self.axes.flat:
            ax.set_facecolor('#2d2d2d')
            ax.tick_params(colors='white', labelsize=9)
            ax.xaxis.label.set_color('white')
            ax.yaxis.label.set_color('white')
            ax.title.set_color('white')
            for spine in ax.spines.values():
                spine.set_color('#555555')
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.top)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=15, pady=10)
        self.top.after(200, self.draw)
    
    def count_tickets(self, tickets_str):
        if not tickets_str: return 0
        return len([t.strip() for t in tickets_str.replace(" ", "").split(",") if t.strip().isdigit()])
    
    def classify_block(self, template):
        if not template: return "other"
        t = template.lower()
        if any(w in t for w in ["заведен", "создан", "найден критический баг"]): return "created"
        if any(w in t for w in ["протестирован", "тестирован", "проверк", "тестирование", "прошел", "пройден", "закрыла тестирование", "завершено тестирование"]): return "tested"
        return "other"
    
    def get_filtered_reports(self):
        period = self.combo_period.get()
        now = datetime.now()
        
        if period == "Последние 7 дней":
            cutoff = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0)
        elif period == "Последние 30 дней":
            cutoff = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0)
        elif period == "Текущий месяц":
            cutoff = now.replace(day=1, hour=0, minute=0, second=0)
        else:
            cutoff = datetime(2000, 1, 1)
        
        filtered = []
        for r in self.reports:
            try:
                d = datetime.strptime(r["date"], "%d.%m.%Y")
                if d >= cutoff: filtered.append(r)
            except: pass
        return sorted(filtered, key=lambda x: datetime.strptime(x["date"], "%d.%m.%Y"))
    
    def draw(self):
        if not hasattr(self, 'axes'): return
        filtered = self.get_filtered_reports()
        
        total_hours = sum(r.get("hours", 0) for r in filtered)
        work_days = len(filtered)
        avg_hours = round(total_hours / work_days, 1) if work_days else 0
        
        created_tickets, tested_tickets = 0, 0
        for r in filtered:
            for template, tickets in r.get("blocks", []):
                cnt = self.count_tickets(tickets)
                cls = self.classify_block(template)
                if cls == "created": created_tickets += cnt
                elif cls == "tested": tested_tickets += cnt
        
        productivity_index = round((created_tickets + tested_tickets) / max(work_days, 1), 1)
        
        self.stat_labels["Всего часов"].config(text=f"Всего часов: {total_hours}")
        self.stat_labels["Рабочих дней"].config(text=f"Рабочих дней: {work_days}")
        self.stat_labels["Среднее ч/день"].config(text=f"Среднее: {avg_hours}ч")
        self.stat_labels["Создано тикетов"].config(text=f"Создано: {created_tickets}")
        self.stat_labels["Протестировано"].config(text=f"Протестировано: {tested_tickets}")
        self.stat_labels["Тикетов/день"].config(text=f"Тикетов/день: {productivity_index}")
        
        for ax in self.axes.flat: ax.clear()
        
        if not filtered:
            self.fig.suptitle("Нет данных", color='white', fontsize=14)
            for ax in self.axes.flat:
                ax.text(0.5, 0.5, "Нет данных", ha='center', va='center', color='white', fontsize=12, transform=ax.transAxes)
                ax.set_xticks([]); ax.set_yticks([])
            self.canvas.draw()
            return
        
        dates_short = [r["date"][:5] for r in filtered]
        x_range = range(len(dates_short))
        
        try:
            ax1 = self.axes[0, 0]
            hours_list = [r.get("hours", 0) for r in filtered]
            colors = ['#00ff88' if h >= 8 else '#ffd93d' if h >= 6 else '#ff6b6b' for h in hours_list]
            ax1.bar(x_range, hours_list, color=colors, edgecolor='#555555', alpha=0.8)
            ax1.set_xticks(x_range)
            ax1.set_xticklabels(dates_short, rotation=45, ha='right', color='white', fontsize=8)
            ax1.set_title("Часы по дням", fontsize=11, pad=10, color='white')
            ax1.set_ylabel("Часы", color='white')
            ax1.axhline(y=8, color='#00ff88', linestyle='--', alpha=0.7, linewidth=2, label='Норма 8ч')
            ax1.legend(loc='upper right', facecolor='#2d2d2d', edgecolor='#555555', labelcolor='white', fontsize=8)
            ax1.set_ylim(0, max(hours_list) * 1.3 if hours_list else 10)
        except Exception as e: print(f"Ошибка графика 1: {e}")
        
        try:
            ax2 = self.axes[0, 1]
            created_list, tested_list = [], []
            for r in filtered:
                c, t = 0, 0
                for template, tickets in r.get("blocks", []):
                    cnt = self.count_tickets(tickets)
                    cls = self.classify_block(template)
                    if cls == "created": c += cnt
                    elif cls == "tested": t += cnt
                created_list.append(c)
                tested_list.append(t)
            
            width = 0.35
            ax2.bar([i - width/2 for i in x_range], created_list, width, label='Создано', color='#ff6b6b', alpha=0.8)
            ax2.bar([i + width/2 for i in x_range], tested_list, width, label='Протестировано', color='#4ecdc4', alpha=0.8)
            ax2.set_xticks(x_range)
            ax2.set_xticklabels(dates_short, rotation=45, ha='right', color='white', fontsize=8)
            ax2.set_title("Тикеты по дням", fontsize=11, pad=10, color='white')
            ax2.legend(facecolor='#2d2d2d', edgecolor='#555555', labelcolor='white', fontsize=8)
        except Exception as e: print(f"Ошибка графика 2: {e}")
        
        try:
            ax3 = self.axes[0, 2]
            cum_hours, cum_tickets = [], []
            total_h, total_t = 0, 0
            for r in filtered:
                total_h += r.get("hours", 0)
                total_t += sum(self.count_tickets(t) for _, t in r.get("blocks", []))
                cum_hours.append(total_h)
                cum_tickets.append(total_t)
            
            ax3.plot(x_range, cum_hours, 'o-', color='#ffd93d', linewidth=2, markersize=5, label='Часы')
            ax3.set_xticks(x_range)
            ax3.set_xticklabels(dates_short, rotation=45, ha='right', color='white', fontsize=8)
            ax3.set_title("Кумулятивная динамика", fontsize=11, pad=10, color='white')
            ax3.set_ylabel("Часы", color='#ffd93d', fontsize=10)
            ax3.legend(loc='upper left', facecolor='#2d2d2d', edgecolor='#555555', labelcolor='white', fontsize=8)
            
            ax3_twin = ax3.twinx()
            ax3_twin.plot(x_range, cum_tickets, 's-', color='#ff6b6b', linewidth=2, markersize=5, label='Тикеты')
            ax3_twin.set_ylabel("Тикеты", color='#ff6b6b', fontsize=10)
            ax3_twin.tick_params(colors='#ff6b6b')
            ax3_twin.legend(loc='upper right', facecolor='#2d2d2d', edgecolor='#555555', labelcolor='white', fontsize=8)
        except Exception as e: print(f"Ошибка графика 3: {e}")
        
        try:
            ax4 = self.axes[1, 0]
            type_counts = {"Тестирование": 0, "Создание тикетов": 0, "Другое": 0}
            for r in filtered:
                for template, _ in r.get("blocks", []):
                    cls = self.classify_block(template)
                    if cls == "tested": type_counts["Тестирование"] += 1
                    elif cls == "created": type_counts["Создание тикетов"] += 1
                    else: type_counts["Другое"] += 1
            
            labels_pie = [k for k, v in type_counts.items() if v > 0]
            values_pie = [v for v in type_counts.values() if v > 0]
            colors_pie = ['#4ecdc4', '#ff6b6b', '#95a5a6'][:len(values_pie)]
            
            if values_pie:
                wedges, texts, autotexts = ax4.pie(values_pie, colors=colors_pie, autopct='%1.1f%%', startangle=90, pctdistance=0.75, wedgeprops={'edgecolor': '#1e1e1e', 'linewidth': 2})
                for autotext in autotexts:
                    autotext.set_color('white'); autotext.set_fontweight('bold'); autotext.set_fontsize(10)
                ax4.legend(labels_pie, loc='center left', bbox_to_anchor=(1, 0.5), facecolor='#2d2d2d', edgecolor='#555555', labelcolor='white', fontsize=9)
            else:
                ax4.text(0.5, 0.5, "Нет данных", ha='center', va='center', color='white', fontsize=11, transform=ax4.transAxes)
                ax4.set_xticks([]); ax4.set_yticks([])
            ax4.set_title("Распределение задач", fontsize=11, pad=10, color='white')
        except Exception as e: print(f"Ошибка графика 4: {e}")
        
        try:
            ax5 = self.axes[1, 1]
            day_productivity = []
            for r in filtered:
                ticket_count = sum(self.count_tickets(t) for _, t in r.get("blocks", []))
                score = r.get("hours", 0) * max(ticket_count, 1)
                day_productivity.append((r["date"][:5], score, r["date"]))
            
            day_productivity.sort(key=lambda x: x[1], reverse=True)
            top5 = day_productivity[:5] if len(day_productivity) >= 5 else day_productivity
            
            if top5:
                labels_top = [d[0] for d in top5]
                values_top = [d[1] for d in top5]
                ax5.barh(range(len(labels_top)), values_top, color='#ffd93d', alpha=0.8, edgecolor='#555555')
                ax5.set_yticks(range(len(labels_top)))
                ax5.set_yticklabels(labels_top, color='white', fontsize=9)
                ax5.invert_yaxis()
                ax5.set_title("Топ продуктивных дней", fontsize=11, pad=10, color='white')
                ax5.set_xlabel("Индекс (часы × тикеты)", color='white')
                for i, v in enumerate(values_top):
                    ax5.text(v + 0.5, i, str(int(v)), color='white', va='center', fontsize=8)
            else:
                ax5.text(0.5, 0.5, "Нет данных", ha='center', va='center', color='white', fontsize=11, transform=ax5.transAxes)
                ax5.set_xticks([]); ax5.set_yticks([])
        except Exception as e: print(f"Ошибка графика 5: {e}")
        
        try:
            ax6 = self.axes[1, 2]
            day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
            day_hours = {i: [] for i in range(7)}
            for r in filtered:
                try:
                    d = datetime.strptime(r["date"], "%d.%m.%Y")
                    day_hours[d.weekday()].append(r.get("hours", 0))
                except: pass
            
            avg_by_day = [sum(day_hours[i]) / len(day_hours[i]) if day_hours[i] else 0 for i in range(7)]
            max_avg = max(avg_by_day) if avg_by_day else 1
            colors_heat = ['#00ff88' if h >= 8 else '#ffd93d' if h >= 6 else '#ff6b6b' for h in avg_by_day]
            
            ax6.bar(range(7), avg_by_day, color=colors_heat, alpha=0.8, edgecolor='#555555')
            ax6.set_xticks(range(7))
            ax6.set_xticklabels(day_names, color='white', fontsize=10)
            ax6.set_title("По дням недели", fontsize=11, pad=10, color='white')
            ax6.set_ylabel("Среднее часов", color='white')
            ax6.axhline(y=8, color='#00ff88', linestyle='--', alpha=0.5)
            ax6.set_ylim(0, max_avg * 1.3 if max_avg > 0 else 10)
            for i, v in enumerate(avg_by_day):
                if v > 0: ax6.text(i, v + max_avg * 0.05, f"{v:.1f}", ha='center', color='white', fontsize=8)
        except Exception as e: print(f"Ошибка графика 6: {e}")
        
        self.fig.subplots_adjust(left=0.08, right=0.95, top=0.92, bottom=0.15, hspace=0.4, wspace=0.3)
        self.canvas.draw()

# ─── Калькулятор зарплаты ───
class SalaryCalculator:
    def __init__(self, parent, reports):
        self.reports = reports
        self.top = tk.Toplevel(parent)
        self.top.title("💰 Калькулятор зарплаты")
        self.top.geometry("500x700")
        self.top.resizable(False, False)
        if IS_MAC:
            self.top.update_idletasks(); self.top.lift(); self.top.focus_force()
        self.top.transient(parent)
        
        frame = ttk.LabelFrame(self.top, text="Расчёт зарплаты", padding=20)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ttk.Label(frame, text="Оклад за месяц (руб):", font=(FONT, 11)).pack(anchor="w", pady=(0, 5))
        self.entry_salary = ttk.Entry(frame, font=(FONT, 11), width=20)
        self.entry_salary.pack(fill="x", pady=(0, 15))
        self.entry_salary.insert(0, "100000")
        
        ttk.Label(frame, text="Норма часов в месяце:", font=(FONT, 11)).pack(anchor="w", pady=(0, 5))
        self.entry_norm = ttk.Entry(frame, font=(FONT, 11), width=20)
        self.entry_norm.pack(fill="x", pady=(0, 15))
        self.entry_norm.insert(0, "160")
        
        ttk.Label(frame, text="Период расчёта:", font=(FONT, 11)).pack(anchor="w", pady=(0, 5))
        self.combo_period = ttk.Combobox(frame, values=["Текущий месяц", "Последние 30 дней", "Всё время", "Произвольный диапазон"], state="readonly", font=(FONT, 11))
        self.combo_period.pack(fill="x", pady=(0, 15))
        self.combo_period.set("Текущий месяц")
        self.combo_period.bind("<<ComboboxSelected>>", lambda e: self.toggle_date_range())
        
        self.date_range_frame = ttk.Frame(frame)
        self.date_range_frame.pack(fill="x", pady=(0, 15))
        self.date_range_frame.pack_forget()
        
        ttk.Label(self.date_range_frame, text="С:").pack(side="left", padx=(0, 5))
        self.entry_date_from = ttk.Entry(self.date_range_frame, width=12)
        self.entry_date_from.pack(side="left", padx=(0, 10))
        ttk.Label(self.date_range_frame, text="По:").pack(side="left", padx=(0, 5))
        self.entry_date_to = ttk.Entry(self.date_range_frame, width=12)
        self.entry_date_to.pack(side="left")
        
        result_frame = ttk.LabelFrame(frame, text="Результат", padding=15)
        result_frame.pack(fill="x", pady=15)
        
        self.result_labels = {}
        results = [("Стоимость часа:", "white"), ("Отработано часов:", "white"), ("Норма часов:", "white"), ("Переработка:", "#ffd93d"), ("Начислено:", "#00ff88"), ("НДФЛ (13%):", "#ff6b6b"), ("На руки:", "#00ff88")]
        for label, color in results:
            row = ttk.Frame(result_frame)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=label, font=(FONT, 10)).pack(side="left")
            lbl = ttk.Label(row, text="0", font=(FONT, 10, "bold"), foreground=color)
            lbl.pack(side="right")
            self.result_labels[label] = lbl
        
        ttk.Button(frame, text="🧮 Рассчитать", command=self.calculate).pack(fill="x", pady=15)
    
    def toggle_date_range(self):
        if self.combo_period.get() == "Произвольный диапазон": self.date_range_frame.pack(fill="x", pady=(0, 15))
        else: self.date_range_frame.pack_forget()
    
    def get_filtered_hours(self):
        period = self.combo_period.get()
        now = datetime.now()
        
        if period == "Текущий месяц": cutoff = now.replace(day=1, hour=0, minute=0, second=0)
        elif period == "Последние 30 дней": cutoff = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0)
        elif period == "Всё время": cutoff = datetime(2000, 1, 1)
        else:
            try:
                d_from = datetime.strptime(self.entry_date_from.get(), "%d.%m.%Y")
                d_to = datetime.strptime(self.entry_date_to.get(), "%d.%m.%Y")
                cutoff = d_from; self.date_to = d_to
            except: return 0
        
        total_hours = 0
        for r in self.reports:
            try:
                d = datetime.strptime(r["date"], "%d.%m.%Y")
                if period == "Произвольный диапазон":
                    if d_from <= d <= d_to: total_hours += r.get("hours", 0)
                elif d >= cutoff: total_hours += r.get("hours", 0)
            except: pass
        return total_hours
    
    def calculate(self):
        try:
            salary = float(self.entry_salary.get()); norm_hours = float(self.entry_norm.get())
        except:
            messagebox.showwarning("Внимание", "Введите корректные числа!"); return
        
        worked_hours = self.get_filtered_hours()
        hour_rate = salary / norm_hours if norm_hours > 0 else 0
        overtime = max(0, worked_hours - norm_hours)
        accrued = worked_hours * hour_rate
        ndfl = accrued * 0.13
        net_salary = accrued - ndfl
        
        self.result_labels["Стоимость часа:"].config(text=f"{hour_rate:.2f} руб")
        self.result_labels["Отработано часов:"].config(text=f"{worked_hours:.1f} ч")
        self.result_labels["Норма часов:"].config(text=f"{norm_hours:.0f} ч")
        self.result_labels["Переработка:"].config(text=f"{overtime:.1f} ч")
        self.result_labels["Начислено:"].config(text=f"{accrued:,.2f} руб")
        self.result_labels["НДФЛ (13%):"].config(text=f"{ndfl:,.2f} руб")
        self.result_labels["На руки:"].config(text=f"{net_salary:,.2f} руб")

# ─── Калькулятор отпуска ───
class VacationCalculator:
    def __init__(self, parent):
        self.top = tk.Toplevel(parent)
        self.top.title("🏖️ Калькулятор отпуска")
        self.top.geometry("500x650")
        self.top.resizable(False, False)
        if IS_MAC:
            self.top.update_idletasks(); self.top.lift(); self.top.focus_force()
        self.top.transient(parent)
        
        frame = ttk.LabelFrame(self.top, text="Расчёт отпускных", padding=20)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ttk.Label(frame, text="Оклад за месяц (руб):", font=(FONT, 11)).pack(anchor="w", pady=(0, 5))
        self.entry_salary = ttk.Entry(frame, font=(FONT, 11), width=20)
        self.entry_salary.pack(fill="x", pady=(0, 15))
        self.entry_salary.insert(0, "100000")
        
        ttk.Label(frame, text="Количество дней отпуска:", font=(FONT, 11)).pack(anchor="w", pady=(0, 5))
        self.entry_days = ttk.Entry(frame, font=(FONT, 11), width=20)
        self.entry_days.pack(fill="x", pady=(0, 15))
        self.entry_days.insert(0, "14")
        
        ttk.Label(frame, text="Расчётный период (месяцев):", font=(FONT, 11)).pack(anchor="w", pady=(0, 5))
        self.entry_months = ttk.Entry(frame, font=(FONT, 11), width=20)
        self.entry_months.pack(fill="x", pady=(0, 15))
        self.entry_months.insert(0, "12")
        
        ttk.Label(frame, text="Среднее кол-во дней в месяце:", font=(FONT, 11)).pack(anchor="w", pady=(0, 5))
        self.entry_avg_days = ttk.Entry(frame, font=(FONT, 11), width=20)
        self.entry_avg_days.pack(fill="x", pady=(0, 15))
        self.entry_avg_days.insert(0, "29.3")
        
        result_frame = ttk.LabelFrame(frame, text="Результат", padding=15)
        result_frame.pack(fill="x", pady=15)
        
        self.result_labels = {}
        results = [("Средний дневной заработок:", "white"), ("Сумма отпускных:", "#00ff88"), ("НДФЛ (13%):", "#ff6b6b"), ("На руки:", "#00ff88"), ("Остаток дней отпуска:", "#ffd93d")]
        for label, color in results:
            row = ttk.Frame(result_frame)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=label, font=(FONT, 10)).pack(side="left")
            lbl = ttk.Label(row, text="0", font=(FONT, 10, "bold"), foreground=color)
            lbl.pack(side="right")
            self.result_labels[label] = lbl
        
        ttk.Button(frame, text="🏖️ Рассчитать", command=self.calculate).pack(fill="x", pady=15)
        
        info_frame = ttk.LabelFrame(frame, text="Справка", padding=10)
        info_frame.pack(fill="x", pady=10)
        info_text = ("📋 По ТК РФ:\n• Стандартный отпуск — 28 дней в год\n• Средний дневной заработок = Оклад / 29.3\n• Отпускные = Средний дневной × Дни отпуска\n• НДФЛ удерживается 13%\n\n💡 Отпускные выплачиваются за 3 дня до начала отпуска")
        ttk.Label(info_frame, text=info_text, font=(FONT, 9), foreground="#aaaaaa", justify="left").pack(anchor="w")
    
    def calculate(self):
        try:
            salary = float(self.entry_salary.get()); vacation_days = float(self.entry_days.get())
            months = float(self.entry_months.get()); avg_days = float(self.entry_avg_days.get())
        except:
            messagebox.showwarning("Внимание", "Введите корректные числа!"); return
        
        avg_daily = salary / avg_days if avg_days > 0 else 0
        vacation_pay = avg_daily * vacation_days
        ndfl = vacation_pay * 0.13
        net_vacation = vacation_pay - ndfl
        remaining_days = max(0, 28 - vacation_days)
        
        self.result_labels["Средний дневной заработок:"].config(text=f"{avg_daily:.2f} руб")
        self.result_labels["Сумма отпускных:"].config(text=f"{vacation_pay:,.2f} руб")
        self.result_labels["НДФЛ (13%):"].config(text=f"{ndfl:,.2f} руб")
        self.result_labels["На руки:"].config(text=f"{net_vacation:,.2f} руб")
        self.result_labels["Остаток дней отпуска:"].config(text=f"{remaining_days:.0f} дней")

# ─── Помодоро и Напоминания ───
class PomodoroWindow:
    def __init__(self, parent):
        self.top = tk.Toplevel(parent)
        self.top.title("⏱ Помодоро")
        self.top.geometry("300x250")
        self.top.resizable(False, False)
        if IS_MAC: self.top.update_idletasks(); self.top.lift(); self.top.focus_force()
        self.top.transient(parent)
        self.time_left = 25 * 60
        self.running = False
        self.timer_id = None
        self.lbl_time = tk.Label(self.top, text="25:00", font=(FONT, 48, "bold"), fg="#ff6b6b")
        self.lbl_time.pack(pady=20)
        btn_frame = tk.Frame(self.top)
        btn_frame.pack(pady=10)
        self.btn_start = ttk.Button(btn_frame, text="▶ Старт", command=self.toggle_timer)
        self.btn_start.pack(side="left", padx=10)
        ttk.Button(btn_frame, text="🔄 Сброс", command=self.reset_timer).pack(side="left", padx=10)
    
    def toggle_timer(self):
        if self.running:
            self.running = False; self.btn_start.config(text="▶ Старт")
            if self.timer_id: self.top.after_cancel(self.timer_id)
        else:
            self.running = True; self.btn_start.config(text="⏸ Пауза"); self.update_timer()
    
    def update_timer(self):
        if not self.running: return
        if self.time_left > 0:
            self.time_left -= 1
            mins, secs = divmod(self.time_left, 60)
            self.lbl_time.config(text=f"{mins:02d}:{secs:02d}")
            self.timer_id = self.top.after(1000, self.update_timer)
        else:
            self.running = False; self.btn_start.config(text="▶ Старт")
            self.lbl_time.config(text="00:00"); self.top.bell()
            messagebox.showinfo("Помодоро", "Время вышло! Пора сделать перерыв.", parent=self.top)
            self.reset_timer()
    
    def reset_timer(self):
        if self.timer_id: self.top.after_cancel(self.timer_id)
        self.running = False; self.time_left = 25 * 60
        self.lbl_time.config(text="25:00"); self.btn_start.config(text="▶ Старт")

class ReminderWindow:
    def __init__(self, parent):
        self.top = tk.Toplevel(parent)
        self.top.title("🔔 Напоминание")
        self.top.geometry("350x220")
        self.top.resizable(False, False)
        if IS_MAC: self.top.update_idletasks(); self.top.lift(); self.top.focus_force()
        self.top.transient(parent); self.top.grab_set()
        ttk.Label(self.top, text="Текст напоминания:").pack(pady=(15, 5))
        self.entry_text = ttk.Entry(self.top, width=40)
        self.entry_text.pack(pady=5)
        self.entry_text.insert(0, "Сделать перерыв"); self.entry_text.focus()
        ttk.Label(self.top, text="Через сколько минут напомнить?").pack(pady=(10, 5))
        self.entry_mins = ttk.Entry(self.top, width=10)
        self.entry_mins.pack(pady=5)
        self.entry_mins.insert(0, "25")
        
        def set_reminder():
            try:
                mins = int(self.entry_mins.get()); text = self.entry_text.get().strip()
                if not text: raise ValueError
            except ValueError:
                messagebox.showwarning("Ошибка", "Введите корректное число минут и текст!", parent=self.top); return
            self.top.destroy()
            messagebox.showinfo("Напоминание", f"Таймер установлен на {mins} минут.\nНе закрывайте главное окно!")
            def show_notification():
                top = tk.Toplevel(parent)
                top.title("⏰ Напоминание!"); top.geometry("300x150")
                if IS_MAC: top.update_idletasks(); top.lift(); top.focus_force()
                ttk.Label(top, text="🔔 НАПОМИНАНИЕ", font=(FONT, 14, "bold")).pack(pady=15)
                ttk.Label(top, text=text, font=(FONT, 11)).pack(pady=10)
                ttk.Button(top, text="Ок", command=top.destroy).pack(pady=10)
                top.bell()
            parent.after(mins * 60 * 1000, show_notification)
        ttk.Button(self.top, text="Установить", command=set_reminder).pack(pady=15)

# ─── Окно редактирования ───
class EditWindow:
    def __init__(self, parent, reports, record, on_save, original_date=None):
        self.reports = reports
        self.top = tk.Toplevel(parent)
        self.top.title("Редактировать запись")
        self.top.geometry("600x600")
        self.top.resizable(False, False)
        if IS_MAC: self.top.update_idletasks(); self.top.lift(); self.top.focus_force()
        self.top.transient(parent)
        self.on_save = on_save
        self.original_date = original_date or record["date"]
        
        frame = ttk.LabelFrame(self.top, text="Редактирование", padding=15)
        frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        date_frame = ttk.Frame(frame)
        date_frame.pack(fill="x", pady=5)
        ttk.Label(date_frame, text="Дата:").pack(side="left", padx=(0, 10))
        self.entry_date = ttk.Entry(date_frame, width=12)
        self.entry_date.pack(side="left")
        self.entry_date.insert(0, record["date"])
        ttk.Button(date_frame, text="📅", width=3, command=lambda: CalendarPopup(self.top, lambda d: self.entry_date.delete(0, tk.END) or self.entry_date.insert(0, d), self.entry_date.get())).pack(side="left", padx=10)
        
        time_frame = ttk.Frame(frame)
        time_frame.pack(fill="x", pady=10)
        ttk.Label(time_frame, text="Начало:").pack(side="left", padx=(0, 5))
        self.entry_start = ttk.Entry(time_frame, width=8)
        self.entry_start.pack(side="left"); self.entry_start.insert(0, record["start"])
        ttk.Label(time_frame, text="Конец:").pack(side="left", padx=(20, 5))
        self.entry_end = ttk.Entry(time_frame, width=8)
        self.entry_end.pack(side="left"); self.entry_end.insert(0, record["end"])
        self.var_lunch = tk.BooleanVar(value=record.get("lunch", True))
        ttk.Checkbutton(time_frame, text="Вычесть 1 час обеда", variable=self.var_lunch).pack(side="left", padx=(30, 0))
        
        ttk.Label(frame, text="Блоки задач:").pack(anchor="w", pady=(10, 2))
        self.task_blocks = TaskBlocksFrame(frame)
        
        blocks = record.get("blocks", [])
        if blocks: self.task_blocks.set_blocks(blocks)
        else:
            parsed_blocks, extra_parsed = parse_comment_to_blocks(record["comment"], TEMPLATES)
            if parsed_blocks: self.task_blocks.set_blocks(parsed_blocks)
            else: self.task_blocks.add_block("", record["comment"])
        
        ttk.Label(frame, text="Доп. комментарий:").pack(anchor="w", pady=(10, 2))
        self.text_extra = tk.Text(frame, height=4, font=(FONT, 10), bg="#2d2d2d", fg="white", insertbackground="white", relief="flat", borderwidth=1)
        self.text_extra.pack(fill="x", pady=5)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=10)
        
        def save():
            date = self.entry_date.get().strip(); start = self.entry_start.get().strip(); end = self.entry_end.get().strip()
            lunch = self.var_lunch.get(); blocks = self.task_blocks.get_blocks(); extra = self.text_extra.get("1.0", tk.END).strip()
            if not date or not start or not end:
                messagebox.showwarning("Внимание", "Заполните дату и время!", parent=self.top); return
            comment = build_comment_from_blocks(blocks, extra)
            if not comment:
                messagebox.showwarning("Внимание", "Добавьте хотя бы один блок задач!", parent=self.top); return
            all_tickets = []
            for _, tickets in blocks:
                if tickets: all_tickets.extend([t.strip() for t in tickets.split(",") if t.strip()])
            tickets_str = ", ".join(all_tickets)
            hours = calc_hours(start, end, lunch)
            updated = {"date": date, "start": start, "end": end, "hours": hours, "lunch": lunch, "comment": comment, "tickets": tickets_str, "blocks": blocks}
            
            if date != self.original_date:
                idx, existing = find_record_by_date(self.reports, date)
                if existing is not None:
                    total = round(existing["hours"] + hours, 1)
                    action = show_merge_dialog(self.top, date, existing["hours"], hours, total)
                    if action == "cancel": return
                    elif action == "merge":
                        merged = {"date": date, "start": existing["start"], "end": end, "hours": total, "lunch": existing.get("lunch", True) or lunch, "comment": existing["comment"] + ", " + comment, "tickets": (existing.get("tickets", "") + ", " + tickets_str).strip(", "), "blocks": existing.get("blocks", []) + blocks}
                        self.on_save(merged, merge_idx=idx); self.top.destroy(); return
            self.on_save(updated); self.top.destroy()
        
        ttk.Button(btn_frame, text="💾 Сохранить", command=save).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="❌ Отмена", command=self.top.destroy).pack(side="left", padx=5)