import tkinter as tk
from tkinter import ttk
from datetime import datetime
import calendar
from config import FONT, IS_MAC, TEMPLATES

# ─── Календарь (popup) ───
class CalendarPopup:
    def __init__(self, parent, callback, initial_date=None):
        self.top = tk.Toplevel(parent)
        self.top.title("Выберите дату")
        self.top.geometry("300x340")
        self.top.resizable(False, False)
        if IS_MAC:
            self.top.update_idletasks()
            self.top.lift()
            self.top.focus_force()
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
        
        header = ttk.Frame(self.top)
        header.pack(fill="x", pady=10, padx=10)
        
        btn_prev = tk.Button(header, text="◀", width=3, bg="#2d2d2d", fg="#aaaaaa",
                            activebackground="#2d2d2d", activeforeground="#aaaaaa",
                            relief="flat", font=(FONT, 10),
                            command=lambda: self._change_month(-1))
        btn_prev.pack(side="left")
        
        month_name = calendar.month_name[month]
        lbl_month = ttk.Label(header, text=f"{month_name} {year}")
        lbl_month.pack(side="left", expand=True)
        
        btn_next = tk.Button(header, text="▶", width=3, bg="#2d2d2d", fg="#aaaaaa",
                            activebackground="#2d2d2d", activeforeground="#aaaaaa",
                            relief="flat", font=(FONT, 10),
                            command=lambda: self._change_month(1))
        btn_next.pack(side="right")
        
        days_header = ttk.Frame(self.top)
        days_header.pack(fill="x", padx=10)
        
        for i, day_name in enumerate(["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]):
            lbl = tk.Label(days_header, text=day_name, width=4,
                          bg="#2d2d2d", fg="#aaaaaa",
                          font=(FONT, 10, "bold"))
            lbl.grid(row=0, column=i, padx=2, pady=5)
        
        days_frame = ttk.Frame(self.top)
        days_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        cal = calendar.monthcalendar(year, month)
        for row_idx, week in enumerate(cal):
            for col_idx, day in enumerate(week):
                if day == 0:
                    continue
                btn = tk.Button(days_frame, text=str(day), width=3,
                               bg="#2d2d2d", fg="#aaaaaa",
                               activebackground="#2d2d2d", activeforeground="#aaaaaa",
                               relief="flat", font=(FONT, 12),
                               command=lambda d=day: self._select_date(d))
                btn.grid(row=row_idx+1, column=col_idx, padx=2, pady=2, sticky="nsew")
        
        for i in range(7):
            days_frame.columnconfigure(i, weight=1)
        
        btn_today = tk.Button(self.top, text="Сегодня", width=10,
                             bg="#2d2d2d", fg="#aaaaaa",
                             activebackground="#2d2d2d", activeforeground="#aaaaaa",
                             relief="flat", font=(FONT, 10),
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

# ─── Контейнер блоков задач ───
class TaskBlocksFrame:
    def __init__(self, parent):
        self.parent = parent
        self.blocks = []
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
        self.clear()
        for template, tickets in blocks:
            self.add_block(template, tickets)