import json
import os
import re
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from config import DATA_FILE, TEMPLATES_FILE, DEFAULT_TEMPLATES, IS_MAC, FONT

# ─── Шаблоны ───
def load_templates():
    if os.path.exists(TEMPLATES_FILE):
        with open(TEMPLATES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return list(DEFAULT_TEMPLATES)

def save_templates(templates):
    with open(TEMPLATES_FILE, "w", encoding="utf-8") as f:
        json.dump(templates, f, ensure_ascii=False, indent=2)

# ─── Отчёты ───
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ─── Логика времени и строк ───
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

def sort_reports(reports):
    reports.sort(key=lambda r: datetime.strptime(r["date"], "%d.%m.%Y"))
    return reports

def find_record_by_date(reports, date_str):
    for i, r in enumerate(reports):
        if r["date"] == date_str:
            return i, r
    return None, None

def build_comment_from_blocks(blocks, extra_text):
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

def parse_comment_to_blocks(comment, templates):
    blocks = []
    extra_parts = []
    sentences = re.split(r'\.\s*', comment.strip())
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        tickets_found = re.findall(r'\b(\d{3,})\b', sentence)
        tickets_str = ", ".join(tickets_found) if tickets_found else ""
        sentence_clean = re.sub(r'\b\d{3,}\b', '', sentence).strip(" ,.-")
        sentence_lower = sentence_clean.lower()
        
        if not sentence_clean:
            if tickets_str:
                blocks.append(("", tickets_str))
            continue
        
        best_template = None
        best_score = 0.0
        MATCH_THRESHOLD = 0.4
        
        for template in templates:
            template_words = set(template.lower().split())
            sentence_words = set(sentence_lower.split())
            
            if not template_words:
                continue
            
            common = template_words & sentence_words
            score = len(common) / len(template_words)
            
            template_list = template.lower().split()
            for i in range(len(template_list)):
                for length in range(min(4, len(template_list) - i), 1, -1):
                    phrase = " ".join(template_list[i:i+length])
                    if phrase in sentence_lower:
                        score = max(score, length / len(template_list) + 0.15)
            
            if score > best_score:
                best_score = score
                best_template = template
        
        if best_score >= MATCH_THRESHOLD and best_template:
            blocks.append((best_template, tickets_str))
        else:
            extra_parts.append(sentence)
    
    merged_blocks = []
    for template, tickets in blocks:
        found = False
        for i, (t, tk_tickets) in enumerate(merged_blocks):
            if t == template:
                existing_tickets = [x.strip() for x in tk_tickets.split(",") if x.strip()] if tk_tickets else []
                new_tickets = [x.strip() for x in tickets.split(",") if x.strip()] if tickets else []
                all_tickets = list(dict.fromkeys(existing_tickets + new_tickets))
                merged_blocks[i] = (t, ", ".join(all_tickets))
                found = True
                break
        if not found:
            merged_blocks.append((template, tickets))
    
    extra = ". ".join(extra_parts)
    if extra and not extra.endswith("."):
        extra += "."
    
    return merged_blocks, extra

def normalize_time(t):
    t = t.strip()
    if ":" not in t:
        t = t + ":00"
    parts = t.split(":")
    return f"{int(parts[0]):02d}:{int(parts[1]):02d}"

def parse_txt_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    records = []
    blocks = re.split(r'-{3,}', content)
    
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        
        lines = block.split("\n")
        date_line = None
        time_line = None
        comment_lines = []
        in_comment = False
        
        for line in lines:
            line_stripped = line.strip()
            if re.match(r'^\d{2}\.\d{2}\.\d{4}$', line_stripped):
                date_line = line_stripped
                in_comment = False
            elif re.match(r'^отработано\s+с\s+', line_stripped, re.IGNORECASE):
                time_line = line_stripped
                in_comment = False
            elif line_stripped.lower().startswith("комментарий"):
                in_comment = True
                text = line_stripped[len("комментарий"):].strip()
                if text:
                    comment_lines.append(text)
            elif in_comment:
                comment_lines.append(line_stripped)
        
        if date_line and time_line:
            time_match = re.search(r'с\s+(\d{1,2}(?::\d{2})?)\s+до\s+(\d{1,2}(?::\d{2})?)', time_line)
            if time_match:
                start = normalize_time(time_match.group(1))
                end = normalize_time(time_match.group(2))
                comment = " ".join(comment_lines).strip()
                if comment:
                    records.append({
                        "date": date_line,
                        "start": start,
                        "end": end,
                        "comment": comment
                    })
    
    return records

def show_merge_dialog(parent, date_str, existing_hours, new_hours, total_hours):
    dialog = tk.Toplevel(parent)
    dialog.title("Запись уже существует")
    dialog.geometry("420x220")
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()
    if IS_MAC:
        dialog.lift()
        dialog.focus_force()
    
    result = {"action": "cancel"}
    
    ttk.Label(dialog, text=f"⚠ За {date_str} уже есть запись ({format_hours(existing_hours)})",
              font=(FONT, 11, "bold")).pack(pady=15)
    ttk.Label(dialog, text=f"Новая запись: {format_hours(new_hours)}").pack()
    ttk.Label(dialog, text=f"Суммарно будет: {format_hours(total_hours)} часов").pack(pady=5)
    
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

# ─── Настройки приложения ───
SETTINGS_FILE = "settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"daily_reminder_enabled": False, "daily_reminder_time": "18:30"}

def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)