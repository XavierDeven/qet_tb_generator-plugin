#!/usr/bin/env python3
# encoding: utf-8

import logging as log
import os
import re
import shutil
import sys
import json
import time
from PIL import Image
from functools import cmp_to_key
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox
from tksheet import Sheet

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from qetproject import QETProject
from terminalblock import TerminalBlock

# --- CONSTANTS ---
VERSION = '2.1.2'
TITLE = 'QET Terminal Block Generator - v{} (CustomTkinter)'.format(VERSION)
CONFIG_FILE = 'qet_tb_generator.json'
DEBUG_MODE = True  # Enable for diagnostics

TABLE = [
    {'col':0, 'text':'ORDER', 'size':80, 'edit': False, 'key': 'order'},
    {'col':1, 'text':'POS.', 'size':50, 'edit': False, 'key': 'terminal_pos'},
    {'col':2 , 'text':'BLOCK', 'size':80, 'edit': False, 'key': 'block_name'},
    {'col':3 , 'text':'ID', 'size':70, 'edit': False, 'key': 'terminal_name'},
    {'col':4 , 'text':'ETAGE', 'size':60, 'edit': False, 'key': 'etage'},
    {'col':5 , 'text':'XREF', 'size':80, 'edit': False, 'key': 'terminal_xref'},
    {'col':6 , 'text':'CABLE', 'size':90, 'edit': False, 'key': 'cable'},
    {'col':7 , 'text':'B1', 'size':30, 'edit': False, 'key': 'bridge1'},
    {'col':8 , 'text':'B2', 'size':30, 'edit': False, 'key': 'bridge2'},
    {'col':9 , 'text':'B3', 'size':30, 'edit': False, 'key': 'bridge3'},
    {'col':10, 'text':'B4', 'size':30, 'edit': False, 'key': 'bridge4'},
    {'col':11, 'text':'TYPE', 'size':100, 'edit': False, 'key': 'terminal_type'},
    {'col':12, 'text':'HOSE', 'size':120, 'edit': True, 'key': 'hose'},
    {'col':13, 'text':'CONDUCTOR', 'size':100, 'edit': True, 'key': 'conductor'},
    {'col':14, 'text':'COLOR', 'size':120, 'edit': False, 'key': 'terminal_color'}
]

HELP = """
Terminal Block generator plug-in for QElectrotech
https://qelectrotech.org/

Steps:
  - In QET, optional: Choose Project> Clean Project.
  - In QET: Close and reopen the project.
  - In this plug-in: Edit the terminals info.
  - In this plug-in: Press the 'CREATE TERMINAL BLOCKS' button.
  - In QET: Reopen the project.
  - In QET: Under the 'COLLECTIONS' tree of the project, all the terminal blocks appear.

Considerations:
  - This addon searches all elements of type 'Terminal'.
  - Terminals must have a tag like X1:1.
  - All terminals with same <terminal_block_name> are grouped.

Refactored to CustomTkinter with tksheet by Antigravity
"""

# Natural sort for IDs
def natural_sort_key(s):
    if not s: return []
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', str(s))]

class App(ctk.CTk):
    def __init__(self, qet_file):
        super().__init__()
        
        self.qet_file = qet_file
        self.qet_project = QETProject(qet_file)
        self.edited_terminals = []
        self.settings = {}
        self.displayed_terminals = []

        if DEBUG_MODE:
            print(f"DEBUG: App starting with version {VERSION}")

        self.title(TITLE)
        if os.name == 'nt':
            self.after(0, lambda: self.state('zoomed'))
        else:
            try:
                self.after(0, lambda: self.attributes('-zoomed', True))
            except:
                pass
        ctk.set_appearance_mode("dark")
        
        self.setup_ui()
        self.load_settings()
        self.refresh_table()

        self.bind_all("<Control-v>", self.handle_global_paste)
        self.bind_all("<Control-V>", self.handle_global_paste)

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkScrollableFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.logo_label = ctk.CTkLabel(self.sidebar, text="QET Plugin", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.pack(pady=20)

        self.filter_label = ctk.CTkLabel(self.sidebar, text="Filter Terminal Blocks:")
        self.filter_label.pack(pady=(10, 0))

        self.tb_scroll = ctk.CTkScrollableFrame(self.sidebar, height=200)
        self.tb_scroll.pack(fill="x", padx=10, pady=5)
        self.tb_buttons = {}
        self.selected_tbs = set(["-- ALL --"])
        self.update_tb_list()

        self.sort_btn = ctk.CTkButton(self.sidebar, text="Sort by ID", command=self.sort_by_id)
        self.sort_btn.pack(pady=10, padx=20)

        self.create_btn = ctk.CTkButton(self.sidebar, text="Create Terminal Blocks", fg_color="green", hover_color="darkgreen", command=self.on_create)
        self.create_btn.pack(pady=10, padx=20)

        self.settings_btn = ctk.CTkButton(self.sidebar, text="Settings", command=self.open_settings)
        self.settings_btn.pack(pady=10, padx=20)

        self.move_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.move_frame.pack(pady=10, padx=20)
        ctk.CTkButton(self.move_frame, text="▲ Monter", width=90, command=self.move_up).pack(side="left", padx=2)
        ctk.CTkButton(self.move_frame, text="▼ Descendre", width=90, command=self.move_down).pack(side="left", padx=2)

        self.autofill_label = ctk.CTkLabel(self.sidebar, text="Auto-Fill Conductors:", font=ctk.CTkFont(weight="bold"))
        self.autofill_label.pack(pady=(20, 0))

        ctk.CTkButton(self.sidebar, text="24V -> Brown", fg_color="#8B4513", command=lambda: self.apply_auto_fill("24V", "Brown")).pack(pady=5, padx=20)
        ctk.CTkButton(self.sidebar, text="0V -> Blue", fg_color="#0000FF", command=lambda: self.apply_auto_fill("0V", "Blue")).pack(pady=5, padx=20)
        ctk.CTkButton(self.sidebar, text="Others -> Black", fg_color="#333333", command=lambda: self.apply_auto_fill("OTHERS", "Black")).pack(pady=5, padx=20)
        ctk.CTkButton(self.sidebar, text="Réinitialiser Conductor", fg_color="#FF4C4C", command=lambda: self.apply_auto_fill("RESET", "")).pack(pady=5, padx=20)

        self.bridge_label = ctk.CTkLabel(self.sidebar, text="Générer les Ponts:", font=ctk.CTkFont(weight="bold"))
        self.bridge_label.pack(pady=(20, 0))

        self.bridge_btn_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.bridge_btn_frame.pack(pady=5, padx=20)
        for i in range(1, 5):
            ctk.CTkButton(self.bridge_btn_frame, text=f"B{i}", width=40, height=30, command=lambda x=i: self.apply_auto_bridge(x)).pack(side="left", padx=2)

        ctk.CTkButton(self.sidebar, text="Help", command=lambda: messagebox.showinfo("Help", HELP)).pack(pady=20, padx=20)

        self.content = ctk.CTkFrame(self)
        self.content.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        self.sheet = Sheet(self.content, 
                           headers=[col['text'] for col in TABLE],
                           font=("Segoe UI", 10, "normal"),
                           header_font=("Segoe UI", 10, "bold"),
                           theme="dark", 
                           editable=True,
                           show_row_index=False)
        self.sheet.pack(fill="both", expand=True)
        self.sheet.set_column_widths([col_def['size'] for col_def in TABLE])

        self.sheet.enable_bindings(("single_select", "drag_select", "row_select", "column_width_resize", "row_height_resize", "arrowkeys", "copy", "cut", "paste", "delete", "undo", "redo", "edit_cell"))
        self.sheet.extra_bindings([
            ("end_edit_cell", self.on_sheet_edit),
            ("end_paste", self.on_sheet_paste),
            ("end_delete", self.on_sheet_delete),
            ("end_cut", self.on_sheet_delete)
        ])
        
        # Use direct canvas bindings with add="+" to preserve tksheet native logic
        # this ensures toggles and manual editing/selection can coexist
        self.sheet.MT.bind("<Button-1>", self.on_sheet_left_click, add="+")
        self.sheet.CH.bind("<Button-1>", self.on_header_click, add="+")

    def on_sheet_begin_edit(self, event):
        # Identify cell from coordinates (event is a tksheet event in extra_bindings, 
        # but here we use it as a Tkinter event if called from MT.bind? No, this is for extra_bindings)
        # Wait, I removed extra_bindings, so on_sheet_begin_edit won't be called.
        # If I want to block editing for toggle columns, I should re-add it or use readonly_columns.
        pass

    def on_sheet_left_click(self, event):
        # Identify row and column from mouse coordinates on the main table (MT)
        row = self.sheet.identify_row(event)
        col = self.sheet.identify_column(event)
        
        if row is None or col is None or row < 0 or col < 0 or col >= len(TABLE) or row >= len(self.displayed_terminals):
            return
            
        if TABLE[col]['edit']:
            # For editable columns (Hose/Conductor), let tksheet handle selection/editing via its internal handlers.
            return
            
        key = TABLE[col]['key']
        terminal = self.displayed_terminals[row]
        handled = False
        
        # Logic for Bridges
        if key.startswith('bridge'):
            current = terminal.get(key, "").strip().upper()
            mapping = {"": "O", "O": "F", "F": ""}
            new_val = mapping.get(current, "")
            terminal[key] = new_val
            self.sheet.set_cell_data(row, col, new_val)
            handled = True
            
        # Logic for Etage
        elif key == 'etage':
            current = str(terminal.get('etage', '1')).strip()
            mapping = {"1": "2", "2": "3", "3": "4", "4": "1"}
            new_val = mapping.get(current, "1")
            terminal['etage'] = new_val
            self.sheet.set_cell_data(row, col, new_val)
            handled = True
            
        # Logic for Color (sequential cycle)
        elif key == 'terminal_color':
            colors = ["", "orange", "lightblue", "red", "darkblue", "green"]
            current = terminal.get('terminal_color', '')
            try: idx = colors.index(current)
            except: idx = 0
            new_val = colors[(idx + 1) % len(colors)]
            terminal['terminal_color'] = new_val
            self.sheet.set_cell_data(row, col, new_val)
            self.apply_row_colors(row, new_val)
            handled = True
            
        # Logic for Type (toggle STANDARD/FUSE/GROUND)
        elif key == 'terminal_type':
            types = ["STANDARD", "FUSE", "GROUND"]
            current = terminal.get('terminal_type', 'STANDARD').strip().upper()
            try: idx = types.index(current)
            except: idx = 0
            new_val = types[(idx + 1) % len(types)]
            terminal['terminal_type'] = new_val
            self.sheet.set_cell_data(row, col, new_val)
            handled = True
            
        if handled:
            self.mark_as_edited(terminal['block_name'])
            # We don't need deselect here because MT.bind("<Button-1>") fires every time it is clicked

    def on_header_click(self, event):
        # Identify column from mouse coordinates on the column header (CH)
        col = self.sheet.identify_column(event)
        if col is None or col < 0 or col >= len(TABLE): return
        key = TABLE[col]['key']
        if key == 'terminal_type':
            self.auto_ground_type()
        elif key == 'terminal_color':
            self.auto_color_type()

    def on_sheet_edit(self, event):
        row, col, value = event.row, event.column, event.value
        if col >= len(TABLE): return
        key = TABLE[col]['key']
        terminal = self.displayed_terminals[row]
        terminal[key] = value
        self.mark_as_edited(terminal['block_name'])
        if key == 'terminal_color':
            self.apply_row_colors(row, value)

    def on_sheet_paste(self, event=None):
        self.sync_sheet_to_model()

    def on_sheet_delete(self, event=None):
        self.sync_sheet_to_model()

    def sync_sheet_to_model(self):
        sheet_data = self.sheet.get_sheet_data()
        for i, row_vals in enumerate(sheet_data):
            if i < len(self.displayed_terminals):
                term = self.displayed_terminals[i]
                changed = False
                for j, col_def in enumerate(TABLE):
                    if col_def['edit']:
                        val = row_vals[j]
                        if term.get(col_def['key']) != val:
                            term[col_def['key']] = val
                            changed = True
                if changed:
                    self.mark_as_edited(term['block_name'])

    def apply_row_colors(self, row_idx, color_name):
        color_map = {"orange": "#FFA500", "lightblue": "#ADD8E6", "red": "#FF0000", "darkblue": "#00008B", "green": "#008000"}
        hex_color = color_map.get(color_name, None)
        col_idx = next(i for i, c in enumerate(TABLE) if c['key'] == 'terminal_color')
        if hex_color:
            self.sheet.highlight_cells(row=row_idx, column=col_idx, bg=hex_color, fg="white" if "blue" in color_name or color_name == "red" else "black")
        else:
            self.sheet.dehighlight_cells(row=row_idx, column=col_idx)

    def update_tb_list(self):
        names = ["-- ALL --"] + self.qet_project.tb_names
        if set(self.tb_buttons.keys()) != set(names):
            for btn in self.tb_buttons.values(): btn.destroy()
            self.tb_buttons = {}
            for name in names:
                btn = ctk.CTkButton(self.tb_scroll, text=name, height=25, command=lambda n=name: self.toggle_tb_filter(n))
                btn.pack(fill="x", pady=1)
                self.tb_buttons[name] = btn
        for name, btn in self.tb_buttons.items():
            is_sel = name in self.selected_tbs
            btn.configure(fg_color="blue" if is_sel else "transparent")

    def toggle_tb_filter(self, name):
        if name == "-- ALL --": self.selected_tbs = set(["-- ALL --"])
        else:
            if "-- ALL --" in self.selected_tbs: self.selected_tbs.remove("-- ALL --")
            if name in self.selected_tbs: self.selected_tbs.remove(name)
            else: self.selected_tbs.add(name)
            if not self.selected_tbs: self.selected_tbs.add("-- ALL --")
        self.update_tb_list()
        self.refresh_table()

    def refresh_table(self):
        show_all = "-- ALL --" in self.selected_tbs
        self.displayed_terminals = [t for t in self.qet_project.terminals if show_all or t['block_name'] in self.selected_tbs]
        sheet_data = [[term.get(col['key'], "") for col in TABLE] for term in self.displayed_terminals]
        self.sheet.set_sheet_data(sheet_data)
        
        # Explicit state management for all columns
        readonly_indices = [i for i, col in enumerate(TABLE) if not col['edit']]
        self.sheet.readonly_columns(columns=readonly_indices)
        
        editable_indices = [i for i, col in enumerate(TABLE) if col['edit']]
        self.sheet.readonly_columns(columns=editable_indices, readonly=False)
            
        for i, term in enumerate(self.displayed_terminals):
            self.apply_row_colors(i, term.get('terminal_color', ''))
        self.sheet.refresh()

    def mark_as_edited(self, tb_name):
        if tb_name not in self.edited_terminals: self.edited_terminals.append(tb_name)

    def sort_by_id(self):
        blocks = {}
        for t in self.qet_project.terminals:
            bn = t['block_name']
            if bn not in blocks: blocks[bn] = []
            blocks[bn].append(t)
        new_terminals = []
        sorted_block_names = []
        for t in self.qet_project.terminals:
            if t['block_name'] not in sorted_block_names: sorted_block_names.append(t['block_name'])
        for bn in sorted_block_names:
            group = blocks[bn]
            def special_sort_key(t):
                name_key = natural_sort_key(t['terminal_name'])
                cable = str(t.get('cable', '')).upper()
                priority = 0 if "0V" in cable else (1 if "24V" in cable else 2)
                return (name_key, priority)
            group.sort(key=special_sort_key)
            for i, t in enumerate(group): t['terminal_pos'] = i + 1
            new_terminals.extend(group)
        self.qet_project.terminals[:] = new_terminals
        self.refresh_table()

    def move_up(self, row_idx=None):
        if row_idx is None:
            try: row_idx = self.sheet.get_currently_selected()[0]
            except: return
        if row_idx <= 0: return
        t1, t2 = self.displayed_terminals[row_idx], self.displayed_terminals[row_idx - 1]
        all_t = self.qet_project.terminals
        if t1['block_name'] == t2['block_name']:
            keys = [col['key'] for col in TABLE[3:]]
            for k in keys: t1[k], t2[k] = t2[k], t1[k]
            t1['uuid'], t2['uuid'] = t2['uuid'], t1['uuid']
            self.mark_as_edited(t1['block_name'])
            self.refresh_table()
            self.sheet.set_currently_selected(row_idx - 1, 0)
            self.sheet.see(row_idx - 1, 0)

    def move_down(self, row_idx=None):
        if row_idx is None:
            try: row_idx = self.sheet.get_currently_selected()[0]
            except: return
        if row_idx >= len(self.displayed_terminals) - 1: return
        t1, t2 = self.displayed_terminals[row_idx], self.displayed_terminals[row_idx + 1]
        if t1['block_name'] == t2['block_name']:
            keys = [col['key'] for col in TABLE[3:]]
            for k in keys: t1[k], t2[k] = t2[k], t1[k]
            t1['uuid'], t2['uuid'] = t2['uuid'], t1['uuid']
            self.mark_as_edited(t1['block_name'])
            self.refresh_table()
            self.sheet.set_currently_selected(row_idx + 1, 0)
            self.sheet.see(row_idx + 1, 0)

    def handle_global_paste(self, event=None): pass

    def apply_auto_fill(self, target, color):
        for t in self.displayed_terminals:
            current_cond = str(t.get('conductor', '')).strip()
            if target != "RESET" and current_cond.isdigit(): continue
            cable = str(t.get('cable', '')).upper()
            should_fill = (target == "24V" and "24V" in cable) or (target == "0V" and "0V" in cable) or (target == "OTHERS" and "24V" not in cable and "0V" not in cable) or (target == "RESET")
            if should_fill:
                t['conductor'] = color
                self.mark_as_edited(t['block_name'])
        self.refresh_table()

    def auto_ground_type(self, event=None):
        for t in self.displayed_terminals:
            if 'pe' in str(t.get('cable', '')).lower() or 'pe' in str(t.get('conductor', '')).lower():
                t['terminal_type'] = "GROUND"
                self.mark_as_edited(t['block_name'])
        self.refresh_table()

    def auto_color_type(self, event=None):
        for t in self.displayed_terminals:
            cable = str(t.get('cable', '')).lower()
            has_bridge = any(str(t.get(f'bridge{i}', '')).strip().upper() in ['O', 'F'] for i in range(1, 5))
            
            new_color = ""
            if 'pe' in cable:
                new_color = "green"
            elif any(x in cable for x in ['24v', '48v']) and has_bridge:
                new_color = "red"
            elif '0v' in cable and has_bridge:
                new_color = "darkblue"
                
            t['terminal_color'] = new_color
            self.mark_as_edited(t['block_name'])
        self.refresh_table()

    def apply_auto_bridge(self, level):
        level_str, bridge_key = str(level), f"bridge{level}"
        show_all = "-- ALL --" in self.selected_tbs
        target_terminals = [t for t in self.qet_project.terminals if show_all or t['block_name'] in self.selected_tbs]
        for t in target_terminals:
            if str(t.get('etage', '1')).strip() == level_str: t[bridge_key] = ""
        level_terminals = [t for t in target_terminals if str(t.get('etage', '1')).strip() == level_str]
        if len(level_terminals) < 2:
            self.refresh_table()
            return
        i = 0
        while i < len(level_terminals) - 1:
            curr, next_t = level_terminals[i], level_terminals[i+1]
            cond_curr, cond_next = str(curr.get('cable', '')).strip(), str(next_t.get('cable', '')).strip()
            if cond_curr and cond_curr == cond_next:
                curr[bridge_key], next_t[bridge_key] = "O", "F"
                self.mark_as_edited(curr['block_name'])
                j = i + 1
                while j < len(level_terminals) - 1:
                    t_j, t_next_j = level_terminals[j], level_terminals[j+1]
                    if str(t_j.get('cable', '')).strip() == str(t_next_j.get('cable', '')).strip() != "":
                        t_j[bridge_key], t_next_j[bridge_key] = "O", "F"
                        j += 1
                    else: break
                i = j + 1
            else: i += 1
        self.refresh_table()

    def on_create(self):
        try:
            if DEBUG_MODE:
                for log_file in ["debug_drawing.txt", "bridge_debug.txt"]:
                    try: 
                        with open(log_file, "w") as f: f.write("")
                    except: pass
            self.sync_sheet_to_model()
            all_data, tb_names = self.qet_project.terminals, self.qet_project.tb_names
            choosed = [n for n in tb_names if ("-- ALL --" in self.selected_tbs or n in self.selected_tbs)]
            if not choosed: return messagebox.showwarning("Warning", "No terminal blocks selected.")
            self.backup_diagram()
            split_val = int(self.settings.get('-CFG_SPLIT-', 30))
            filtered_data = [d for d in all_data if d['block_name'] in choosed]
            if not filtered_data: return messagebox.showwarning("Warning", "The selected terminal blocks contain no data.")
            tb_done, current_tb, memo_tb_name = [], [], filtered_data[0]['block_name']
            for t in filtered_data:
                if t['block_name'] == memo_tb_name and len(current_tb) < split_val: current_tb.append(t)
                else:
                    self.create_tb_segment(current_tb, tb_done, split_val, filtered_data)
                    current_tb, memo_tb_name = [t], t['block_name']
            self.create_tb_segment(current_tb, tb_done, split_val, filtered_data)
            self.qet_project.update_terminals(filtered_data)
            self.qet_project.save_tb(self.qet_file)
            messagebox.showinfo("Success", "Terminal blocks created successfully!")
        except Exception as e:
            import traceback
            err_msg = f"An error occurred during creation:\n{str(e)}\n\n{traceback.format_exc()}"
            with open("error_log.txt", "w") as f: f.write(err_msg)
            messagebox.showerror("Creation Error", err_msg)

    def create_tb_segment(self, current_tb, tb_done, split_val, filtered_data):
        name = current_tb[0]['block_name']
        tb_done.append(name)
        slice_num = tb_done.count(name)
        head_text = "{}({})".format(name, slice_num) if len([1 for x in filtered_data if x['block_name'] == name]) > split_val else name
        self.qet_project.insert_tb(head_text, TerminalBlock(head_text, current_tb, self.settings).drawTerminalBlock())

    def backup_diagram(self):
        i, base = 1, os.path.splitext(self.qet_file)[0]
        while True:
            backup = f"{base}_{i}.qet"
            if not os.path.exists(backup): return shutil.copyfile(self.qet_file, backup)
            i += 1

    def open_settings(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Settings")
        dialog.geometry("900x700")
        dialog.transient(self)
        dialog.grab_set()

        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=(10, 0))
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)

        scroll_canvas = ctk.CTkScrollableFrame(main_frame)
        scroll_canvas.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # --- Layout for settings and image ---
        top_frame = ctk.CTkFrame(scroll_canvas, fg_color="transparent")
        top_frame.pack(fill="x", padx=10, pady=5)
        
        # Left side: inputs
        inputs_frame = ctk.CTkFrame(top_frame)
        inputs_frame.pack(side="left", fill="y", padx=10, pady=5)

        # Labels mapping
        labels_map = {
            '-CFG_SPLIT-': 'Max Terminals per Block:',
            '-CFG_A-': 'A: Head Height:',
            '-CFG_B-': 'B: Head Width:',
            '-CFG_C-': 'C: Union Height:',
            '-CFG_D-': 'D: Union Width:',
            '-CFG_E-': 'E: Terminal Height:',
            '-CFG_F-': 'F: Terminal Width:',
            '-CFG_G-': 'G: Conductor Length:',
            '-CFG_H-': 'H: Hose Start Length:',
            '-CFG_I-': 'I: Hose Length:',
            '-CFG_J-': 'J: Hose End Length:',
            '-CFG_K-': 'K: Terminal Step:',
            '-CFG_HEAD_FONT-': 'Head Font Size:',
            '-CFG_TERMINAL_FONT-': 'Terminal Font Size:',
            '-CFG_XREF_FONT-': 'XREF Font Size:',
            '-CFG_CONDUCTOR_FONT-': 'Conductor Font Size:'
        }

        self.settings_entries = {}
        for row, (key, label_text) in enumerate(labels_map.items()):
            lbl = ctk.CTkLabel(inputs_frame, text=label_text)
            lbl.grid(row=row, column=0, sticky="w", padx=10, pady=2)
            ent = ctk.CTkEntry(inputs_frame, width=60)
            ent.insert(0, str(self.settings.get(key, "")))
            ent.grid(row=row, column=1, padx=10, pady=2)
            self.settings_entries[key] = ent

        # Right side: reference image
        try:
            img_path = os.path.join(current_dir, "assets", "legend borne.jpg")
            if os.path.exists(img_path):
                img = Image.open(img_path)
                img.thumbnail((450, 600))
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                img_lbl = ctk.CTkLabel(top_frame, image=ctk_img, text="")
                img_lbl.pack(side="right", padx=10, pady=5, anchor="n")
        except Exception as e:
            print("Could not load image:", e)

        def save():
            new_settings = self.settings.copy()
            for key, ent in self.settings_entries.items():
                new_settings[key] = ent.get()
            try:
                for v in new_settings.values():
                    int(v) if v else 0
                self.settings = new_settings
                self.save_settings_to_file()
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Error", "Values must be integers.")

        ctk.CTkButton(scroll_canvas, text="Save Settings", command=save).pack(pady=20)

    def load_settings(self):
        path = os.path.join(os.path.expanduser("~"), CONFIG_FILE)
        if os.path.isfile(path):
            try:
                with open(path, 'r') as f: self.settings = json.load(f)
            except: self.set_defaults()
        else: self.set_defaults()

    def set_defaults(self):
        self.settings = {'-CFG_SPLIT-': '30', **{f'-CFG_{c}-': '120' for c in "ABCDEFGHIJK"}, '-CFG_HEAD_FONT-': '13', '-CFG_TERMINAL_FONT-': '9', '-CFG_XREF_FONT-': '6', '-CFG_CONDUCTOR_FONT-': '6'}

    def save_settings_to_file(self):
        with open(os.path.join(os.path.expanduser("~"), CONFIG_FILE), 'w') as f: json.dump(self.settings, f)

def main():
    path = None
    if len(sys.argv) > 1:
        path = sys.argv[1]
        if not os.path.isfile(path):
            print(f"File not found: {path}")
            path = None
            
    if not path:
        root = tk.Tk(); root.withdraw()
        path = filedialog.askopenfilename(title="Choose a diagram QET file", 
                                           filetypes=[("QET Files", "*.qet"), ("All Files", "*.*")])
        root.destroy()
        
    if path:
        App(path).mainloop()

if __name__ == "__main__":
    main()
