#!/usr/bin/env python3
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from collections import defaultdict
import psycopg2
import psycopg2.extras

# Directories to always exclude from file tree traversal.
EXCLUDE_DIRS = {'node_modules', '.next', 'prompts'}

# Name of the file to store Supabase connection details locally.
SUPABASE_CONFIG_FILENAME = "supabase_config.local"

# --------------------------
# Helper functions for supabase config
# --------------------------
def load_supabase_config(base_path):
    config_file = os.path.join(base_path, SUPABASE_CONFIG_FILENAME)
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding="utf-8") as f:
                config = json.load(f)
            return config
        except Exception as e:
            print("Failed to load supabase_config.local:", e)
            return {}
    return {}

def save_supabase_config(base_path, config):
    config_file = os.path.join(base_path, SUPABASE_CONFIG_FILENAME)
    try:
        with open(config_file, 'w', encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print("Failed to save supabase_config.local:", e)

# --------------------------
# Function to generate a directory tree string
# --------------------------
def get_directory_tree(base_path, excluded_paths):
    tree_str = ""
    # Normalize excluded paths.
    excluded_paths = {os.path.normpath(p) for p in excluded_paths}
    
    for root, dirs, files in os.walk(base_path, topdown=True):
        # Skip excluded directories.
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and os.path.normpath(os.path.join(root, d)) not in excluded_paths]
        files = [f for f in files if os.path.normpath(os.path.join(root, f)) not in excluded_paths]
        
        root_norm = os.path.normpath(root)
        if root_norm in excluded_paths:
            dirs[:] = []
            continue

        level = root.replace(base_path, '').count(os.sep)
        indent = ' ' * (4 * level)
        tree_str += f"{indent}{os.path.basename(root)}/\n"
        
        subindent = ' ' * (4 * (level + 1))
        for f in files:
            tree_str += f"{subindent}{f}\n"
            
    return tree_str

# --------------------------
# Supabase Connection and Export Dialog
# --------------------------
class SupabaseDialog(tk.Toplevel):
    def __init__(self, parent, base_path):
        super().__init__(parent)
        self.parent = parent
        self.base_path = base_path
        self.title("Supabase Connection")
        self.geometry("700x500")
        self.resizable(True, True)
        self.conn = None

        # Make this a modal dialog.
        self.grab_set()

        # Try to load stored connection details.
        self.config = load_supabase_config(base_path)

        # Create connection frame.
        conn_frame = ttk.LabelFrame(self, text="Database Connection Details")
        conn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Host
        ttk.Label(conn_frame, text="Host:").grid(row=0, column=0, sticky=tk.E, padx=5, pady=5)
        self.host_entry = ttk.Entry(conn_frame, width=40)
        self.host_entry.grid(row=0, column=1, padx=5, pady=5)
        self.host_entry.insert(0, self.config.get("SUPABASE_HOST", "your-project-ref.supabase.co"))
        
        # Port
        ttk.Label(conn_frame, text="Port:").grid(row=1, column=0, sticky=tk.E, padx=5, pady=5)
        self.port_entry = ttk.Entry(conn_frame, width=10)
        self.port_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        self.port_entry.insert(0, self.config.get("SUPABASE_PORT", "5432"))
        
        # Database name
        ttk.Label(conn_frame, text="Database:").grid(row=2, column=0, sticky=tk.E, padx=5, pady=5)
        self.db_entry = ttk.Entry(conn_frame, width=40)
        self.db_entry.grid(row=2, column=1, padx=5, pady=5)
        self.db_entry.insert(0, self.config.get("SUPABASE_DB", "postgres"))
        
        # User
        ttk.Label(conn_frame, text="User:").grid(row=3, column=0, sticky=tk.E, padx=5, pady=5)
        self.user_entry = ttk.Entry(conn_frame, width=40)
        self.user_entry.grid(row=3, column=1, padx=5, pady=5)
        self.user_entry.insert(0, self.config.get("SUPABASE_USER", "postgres"))
        
        # Password
        ttk.Label(conn_frame, text="Password:").grid(row=4, column=0, sticky=tk.E, padx=5, pady=5)
        self.password_entry = ttk.Entry(conn_frame, show="*", width=40)
        self.password_entry.grid(row=4, column=1, padx=5, pady=5)
        self.password_entry.insert(0, self.config.get("SUPABASE_PASSWORD", ""))
        
        # Connect button.
        self.connect_button = ttk.Button(conn_frame, text="Connect", command=self.connect_db)
        self.connect_button.grid(row=5, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Label for connection status.
        self.status_label = ttk.Label(self, text="Not connected", foreground="red")
        self.status_label.pack(pady=5)
        
        # Frame for listing available tables.
        tables_frame = ttk.LabelFrame(self, text="Available Tables (public schema)")
        tables_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.tables_listbox = tk.Listbox(tables_frame, selectmode=tk.MULTIPLE)
        self.tables_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(tables_frame, orient="vertical", command=self.tables_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tables_listbox.config(yscrollcommand=scrollbar.set)
        
        # Export tables button.
        self.export_button = ttk.Button(self, text="Export Selected Tables", command=self.export_tables, state=tk.DISABLED)
        self.export_button.pack(pady=5)
        
        # A separate proceed button lets you close the dialog even if you don't export.
        self.proceed_button = ttk.Button(self, text="Proceed", command=self.destroy)
        self.proceed_button.pack(pady=5)
        
    def connect_db(self):
        host = self.host_entry.get().strip()
        port = self.port_entry.get().strip()
        db = self.db_entry.get().strip()
        user = self.user_entry.get().strip()
        password = self.password_entry.get().strip()
        
        try:
            self.conn = psycopg2.connect(host=host, port=port, database=db, user=user, password=password)
            self.status_label.config(text="Connected successfully!", foreground="green")
            self.export_button.config(state=tk.NORMAL)
            self.populate_tables()
            # Save connection details locally.
            self.config = {
                "SUPABASE_HOST": host,
                "SUPABASE_PORT": port,
                "SUPABASE_DB": db,
                "SUPABASE_USER": user,
                "SUPABASE_PASSWORD": password
            }
            save_supabase_config(self.base_path, self.config)
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect:\n{str(e)}")
            self.status_label.config(text="Not connected", foreground="red")
    
    def populate_tables(self):
        if not self.conn:
            return
        query = """
            SELECT table_name 
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """
        try:
            cur = self.conn.cursor()
            cur.execute(query)
            tables = cur.fetchall()
            self.tables_listbox.delete(0, tk.END)
            for table in tables:
                self.tables_listbox.insert(tk.END, table[0])
            cur.close()
        except Exception as e:
            messagebox.showerror("Error Retrieving Tables", str(e))
    
    def export_tables(self):
        if not self.conn:
            messagebox.showwarning("Not Connected", "Please connect to Supabase first!")
            return

        selected_indices = self.tables_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Table Selected", "Select at least one table to export.")
            return

        selected_tables = [self.tables_listbox.get(i) for i in selected_indices]
        export_data = {}
        try:
            cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            for table in selected_tables:
                # Get column schema.
                cur.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    ORDER BY ordinal_position;
                """, (table,))
                columns = cur.fetchall()

                # Get all table rows.
                cur.execute(f"SELECT * FROM {table};")
                rows = cur.fetchall()

                export_data[table] = {"schema": columns, "rows": rows}
            cur.close()
            
            json_str = json.dumps(export_data, indent=4, default=str)
            # Save JSON to file in the base path.
            json_file = os.path.join(self.base_path, "supabases_tables.json")
            with open(json_file, "w", encoding="utf-8") as f:
                f.write(json_str)
            
            # Create the prompt text with the desired header.
            prompt_text = (
                "These are all my supabase current tables. Return any SQL commands before your XML output "
                "and after your changes description on every output if you need me to run changes to the supabase database of the app. "
                "This is my databases tables json: supabases_tables.json:\n---\n" +
                json_str +
                "\n---"
            )
            # Add this generated prompt into the available prompts of the main GUI.
            self.parent.add_supabase_prompt("supabases_tables.json", prompt_text)
            messagebox.showinfo("Export Successful", f"Exported data and prompt added.\nJSON saved at:\n{json_file}")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Export Error", str(e))
            self.destroy()

# --------------------------
# Main File Selection / AI Context Builder GUI
# --------------------------
class FileSelectorGUI(tk.Tk):
    def __init__(self, base_path):
        super().__init__()
        self.base_path = base_path
        self.title("AI Context Builder Pro")
        self.geometry("1200x900")
        
        # Dictionaries to keep track of file and directory states.
        self.file_token_counts = {}
        self.dir_to_files = defaultdict(list)
        self.dir_parent_map = {}
        self.file_vars = {}      # file path -> BooleanVar.
        self.dir_vars = {}       # directory path -> BooleanVar.
        self.exclusion_vars = {} # For exclusion toggles.
        self.item_widgets = {}   # Map normalized path -> (checkbox widget, label widget)
        self.prompts_data = {}   # Map for presaved prompts: key -> {path, content, tokens}
        
        self.context_file = os.path.join(self.base_path, 'ai_context.config')
        self.setup_gui()
        self.populate_data()
        self.setup_prompts_frame()
        self.populate_prompts()
        self.populate_gui()
        
        # Open the Supabase connection dialog after the main window is loaded.
        self.after(100, self.open_supabase_dialog)
    
    def setup_gui(self):
        self.style = ttk.Style()
        self.style.configure("Exclusion.TButton", foreground="red", font=('Helvetica', 10, 'bold'))
        
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(self.main_frame)
        self.scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.control_frame = ttk.Frame(self)
        self.control_frame.pack(pady=10, fill=tk.X)
        
        self.token_label = ttk.Label(self.control_frame, text="Estimated Tokens: 0")
        self.token_label.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(self.control_frame, text="Generate Output", command=self.generate_output).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.control_frame, text="Save Configuration", command=self.save_configuration).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.control_frame, text="Load Configuration", command=self.load_configuration).pack(side=tk.LEFT, padx=5)
    
    def populate_data(self):
        all_files = []
        try:
            script_name = os.path.basename(__file__)
        except NameError:
            script_name = ""
        for root, dirs, files in os.walk(self.base_path, topdown=True):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            dirs.sort()
            for d in dirs:
                dir_path = os.path.join(root, d)
                self.dir_parent_map[dir_path] = os.path.dirname(dir_path)
            for file in files:
                if file != script_name:
                    all_files.append(os.path.join(root, file))
        
        for file in all_files:
            try:
                with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # Estimate token count (roughly one token per 4 characters)
                    self.file_token_counts[file] = len(content) // 4
            except Exception:
                self.file_token_counts[file] = 0

        for file in all_files:
            current_dir = os.path.dirname(os.path.abspath(file))
            self.dir_to_files[current_dir].append(file)
    
    def populate_gui(self):
        row = 0
        # Walk through the directory structure.
        for root, dirs, files in os.walk(self.base_path, topdown=True):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            dirs.sort()
            rel_path = os.path.relpath(root, self.base_path)
            depth = rel_path.count(os.sep) if rel_path != '.' else 0
            
            # Directory row.
            dir_frame = ttk.Frame(self.scrollable_frame)
            dir_frame.grid(row=row, column=0, sticky="w", padx=(20 * depth, 0), pady=2)
            
            norm_root = os.path.normpath(root)
            excl_var = tk.BooleanVar()
            self.exclusion_vars[norm_root] = excl_var
            ttk.Checkbutton(
                dir_frame,
                text="×",
                style="Exclusion.TButton",
                variable=excl_var,
                command=lambda r=root, v=excl_var: self.toggle_exclusion(r, v)
            ).pack(side=tk.LEFT)
            
            dir_var = tk.BooleanVar()
            self.dir_vars[norm_root] = dir_var
            ttk.Checkbutton(
                dir_frame,
                variable=dir_var,
                command=lambda r=root: self.on_dir_check(r)
            ).pack(side=tk.LEFT)
            dir_lbl = ttk.Label(dir_frame, text=f"📁 {os.path.basename(root)}")
            dir_lbl.pack(side=tk.LEFT)
            
            self.item_widgets[norm_root] = (None, dir_lbl)
            self.update_item_appearance(root)
            row += 1

            for file in sorted(files):
                try:
                    if file == os.path.basename(__file__):
                        continue
                except NameError:
                    pass
                file_path = os.path.join(root, file)
                norm_file = os.path.normpath(file_path)
                file_frame = ttk.Frame(self.scrollable_frame)
                file_frame.grid(row=row, column=0, sticky="w", padx=(20 * (depth + 1), 0), pady=2)
                
                file_excl_var = tk.BooleanVar()
                self.exclusion_vars[norm_file] = file_excl_var
                ttk.Checkbutton(
                    file_frame,
                    text="×",
                    style="Exclusion.TButton",
                    variable=file_excl_var,
                    command=lambda fp=file_path, v=file_excl_var: self.toggle_exclusion(fp, v)
                ).pack(side=tk.LEFT)
                
                file_var = tk.BooleanVar()
                self.file_vars[norm_file] = file_var
                file_cb = ttk.Checkbutton(file_frame, variable=file_var, command=self.update_token_count)
                file_cb.pack(side=tk.LEFT)
                file_lbl = ttk.Label(file_frame, text=f"📄 {file}")
                file_lbl.pack(side=tk.LEFT)
                
                self.item_widgets[norm_file] = (file_cb, file_lbl)
                self.update_item_appearance(file_path)
                row += 1
                
        self.update_token_count()
    
    def is_excluded(self, path):
        norm_path = os.path.normpath(path)
        base_abs = os.path.abspath(self.base_path)
        current = norm_path
        while True:
            if current in self.excluded_paths:
                return True
            if os.path.abspath(current) == base_abs:
                break
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent
        return False

    @property
    def excluded_paths(self):
        return {path for path, var in self.exclusion_vars.items() if var.get()}

    def update_item_appearance(self, path):
        norm_path = os.path.normpath(path)
        eff_excluded = norm_path in self.excluded_paths
        if norm_path in self.item_widgets:
            cb, lbl = self.item_widgets[norm_path]
            lbl.config(foreground='red' if eff_excluded else 'black')
            if cb is not None:
                cb.config(state='disabled' if eff_excluded else 'normal')

    def refresh_all_appearances(self):
        for path in self.item_widgets:
            self.update_item_appearance(path)

    def toggle_exclusion(self, path, var):
        self.refresh_all_appearances()
        self.update_token_count()
            
    def on_dir_check(self, dir_path):
        norm_dir = os.path.normpath(dir_path)
        state = self.dir_vars[norm_dir].get()
        for root, dirs, files in os.walk(dir_path, topdown=True):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for d in dirs:
                full_path = os.path.normpath(os.path.join(root, d))
                if full_path in self.dir_vars:
                    self.dir_vars[full_path].set(state)
            for f in files:
                full_path = os.path.normpath(os.path.join(root, f))
                if full_path in self.file_vars:
                    self.file_vars[full_path].set(state)
        self.update_token_count()

    def update_token_count(self):
        # Count tokens for selected code files.
        selected_files = self.get_selected_files()
        total_tokens_files = sum(self.file_token_counts.get(fp, 0) for fp in selected_files)
        # Also add tokens from selected prompts.
        total_tokens_prompts = 0
        if hasattr(self, "selected_prompts_box"):
            for fname in self.selected_prompts_box.get(0, tk.END):
                prompt_data = self.prompts_data.get(fname)
                if prompt_data:
                    total_tokens_prompts += prompt_data["tokens"]
        total_tokens = total_tokens_files + total_tokens_prompts
        self.token_label.config(text=f"Estimated Tokens: {total_tokens}")

    def save_configuration(self):
        config = {
            'excluded_paths': list(self.excluded_paths),
            'selected_files': [p for p, var in self.file_vars.items() if var.get()],
            'selected_dirs': [p for p, var in self.dir_vars.items() if var.get()]
        }
        try:
            with open(self.context_file, 'w') as f:
                json.dump(config, f)
            messagebox.showinfo("Success", f"Configuration saved to:\n{self.context_file}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {str(e)}")
            
    def load_configuration(self):
        try:
            with open(self.context_file, 'r') as f:
                config = json.load(f)
            
            for var in self.dir_vars.values():
                var.set(False)
            for var in self.file_vars.values():
                var.set(False)
            
            for path in config.get('excluded_paths', []):
                norm_path = os.path.normpath(path)
                if norm_path in self.exclusion_vars:
                    self.exclusion_vars[norm_path].set(True)
            
            for dir_path in config.get('selected_dirs', []):
                norm_dir = os.path.normpath(dir_path)
                if norm_dir in self.dir_vars:
                    self.dir_vars[norm_dir].set(True)
            
            for file_path in config.get('selected_files', []):
                norm_file = os.path.normpath(file_path)
                if norm_file in self.file_vars:
                    self.file_vars[norm_file].set(True)
            
            self.refresh_all_appearances()
            self.update_token_count()
            messagebox.showinfo("Success", "Configuration loaded successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load configuration: {str(e)}")
    
    def setup_prompts_frame(self):
        # Frame for presaved prompts.
        self.prompts_frame = ttk.LabelFrame(self, text="Presaved Prompts")
        self.prompts_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Left column – available prompts.
        available_frame = ttk.Frame(self.prompts_frame)
        available_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        ttk.Label(available_frame, text="Available Prompts").pack()
        self.available_prompts_box = tk.Listbox(available_frame, selectmode=tk.MULTIPLE, width=40, height=6)
        self.available_prompts_box.pack()
        
        # Middle column – control buttons.
        buttons_frame = ttk.Frame(self.prompts_frame)
        buttons_frame.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(buttons_frame, text="Add >>", command=self.add_prompt).pack(pady=2)
        ttk.Button(buttons_frame, text="<< Remove", command=self.remove_prompt).pack(pady=2)
        ttk.Button(buttons_frame, text="Move Up", command=self.move_prompt_up).pack(pady=2)
        ttk.Button(buttons_frame, text="Move Down", command=self.move_prompt_down).pack(pady=2)
        
        # Right column – selected prompts (ordered).
        selected_frame = ttk.Frame(self.prompts_frame)
        selected_frame.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")
        ttk.Label(selected_frame, text="Selected Prompts (Ordered)").pack()
        self.selected_prompts_box = tk.Listbox(selected_frame, selectmode=tk.SINGLE, width=40, height=6)
        self.selected_prompts_box.pack()
        
    def populate_prompts(self):
        # Load prompt files from a "prompts" folder, if available.
        prompts_dir = os.path.join(self.base_path, "prompts")
        if not os.path.exists(prompts_dir):
            return
        self.prompts_data = {}
        for fname in sorted(os.listdir(prompts_dir)):
            if fname.endswith(".txt"):
                full_path = os.path.join(prompts_dir, fname)
                try:
                    with open(full_path, 'r', encoding="utf-8") as f:
                        content = f.read()
                    token_count = len(content) // 4
                    self.prompts_data[fname] = {"path": full_path, "content": content, "tokens": token_count}
                except Exception:
                    continue
        self.available_prompts_box.delete(0, tk.END)
        for fname in sorted(self.prompts_data.keys()):
            self.available_prompts_box.insert(tk.END, fname)
    
    def add_prompt(self):
        # Move selected item(s) from available to selected listbox.
        selection = self.available_prompts_box.curselection()
        for index in selection[::-1]:
            fname = self.available_prompts_box.get(index)
            if fname not in self.selected_prompts_box.get(0, tk.END):
                self.selected_prompts_box.insert(tk.END, fname)
            self.available_prompts_box.delete(index)
        self.update_token_count()
            
    def remove_prompt(self):
        # Remove selected prompt from the selected list.
        selection = self.selected_prompts_box.curselection()
        for index in selection[::-1]:
            fname = self.selected_prompts_box.get(index)
            self.selected_prompts_box.delete(index)
            self.available_prompts_box.insert(tk.END, fname)
            items = list(self.available_prompts_box.get(0, tk.END))
            items.sort()
            self.available_prompts_box.delete(0, tk.END)
            for item in items:
                self.available_prompts_box.insert(tk.END, item)
        self.update_token_count()
    
    def move_prompt_up(self):
        selection = self.selected_prompts_box.curselection()
        if not selection:
            return
        index = selection[0]
        if index > 0:
            item = self.selected_prompts_box.get(index)
            self.selected_prompts_box.delete(index)
            self.selected_prompts_box.insert(index-1, item)
            self.selected_prompts_box.selection_clear(0, tk.END)
            self.selected_prompts_box.selection_set(index-1)
        self.update_token_count()
    
    def move_prompt_down(self):
        selection = self.selected_prompts_box.curselection()
        if not selection:
            return
        index = selection[0]
        if index < self.selected_prompts_box.size()-1:
            item = self.selected_prompts_box.get(index)
            self.selected_prompts_box.delete(index)
            self.selected_prompts_box.insert(index+1, item)
            self.selected_prompts_box.selection_clear(0, tk.END)
            self.selected_prompts_box.selection_set(index+1)
        self.update_token_count()
    
    def open_supabase_dialog(self):
        # Opens the Supabase connection dialog at startup.
        dialog = SupabaseDialog(self, self.base_path)
        self.wait_window(dialog)
        # Update token count if the supabase prompt was added.
        self.update_token_count()

    def add_supabase_prompt(self, prompt_key, prompt_text):
        # Add the generated supabase prompt to the available prompts.
        token_count = len(prompt_text) // 4
        self.prompts_data[prompt_key] = {"path": None, "content": prompt_text, "tokens": token_count}
        current = self.available_prompts_box.get(0, tk.END)
        if prompt_key not in current:
            self.available_prompts_box.insert(tk.END, prompt_key)
        self.update_token_count()
    
    def generate_output(self):
        output_file = os.path.join(self.base_path, 'output.txt')
        selected_files = self.get_selected_files()
        
        try:
            with open(output_file, 'w', encoding='utf-8') as outfile:
                # Insert selected prompts first.
                if self.selected_prompts_box.size() > 0:
                    outfile.write("Selected Presaved Prompts:\n\n")
                    for fname in self.selected_prompts_box.get(0, tk.END):
                        prompt_data = self.prompts_data.get(fname)
                        if prompt_data:
                            outfile.write(f"Prompt: {fname}\n```\n{prompt_data['content']}\n```\n\n")
                outfile.write("Directory Structure:\n")
                outfile.write(get_directory_tree(self.base_path, self.excluded_paths))
                
                if selected_files:
                    outfile.write("\nImportant Code Files:\n\n")
                    for file in selected_files:
                        relative_path = os.path.relpath(file, self.base_path)
                        outfile.write(f"File: {relative_path}\n```\n")
                        try:
                            with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                                outfile.write(f.read())
                            outfile.write("\n```\n\n")
                        except Exception as e:
                            outfile.write(f"Error reading file: {e}\n```\n\n")
                else:
                    outfile.write("\nNo code files selected for inclusion\n")
                    
            self.save_configuration()
            messagebox.showinfo("Success", f"Output generated at:\n{output_file}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate output: {str(e)}")
        self.destroy()
        
    def get_selected_files(self):
        selected = set()
        for file, var in self.file_vars.items():
            if var.get() and file not in self.excluded_paths:
                selected.add(file)
        return sorted(selected)

if __name__ == "__main__":
    base_path = os.path.dirname(os.path.abspath(__file__))
    app = FileSelectorGUI(base_path)
    app.mainloop()
