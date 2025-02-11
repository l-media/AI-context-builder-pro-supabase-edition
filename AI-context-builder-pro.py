#!/usr/bin/env python3
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
import psycopg2.extras

EXCLUDE_DIRS = {'node_modules', '.next', 'prompts'}
SUPABASE_CONFIG_FILENAME = "supabase_config.local"

# --------------------------------------------------------------------------
# Supabase config helpers
# --------------------------------------------------------------------------
def load_supabase_config(base_path):
    config_file = os.path.join(base_path, SUPABASE_CONFIG_FILENAME)
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding="utf-8") as f:
                return json.load(f)
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

# --------------------------------------------------------------------------
# Generate a directory tree string with exclusions
# --------------------------------------------------------------------------
def get_directory_tree(base_path, excluded_paths):
    tree_str = ""
    excluded_paths = {os.path.normpath(p) for p in excluded_paths}
    
    for root, dirs, files in os.walk(base_path, topdown=True):
        # Skip excluded directories
        dirs[:] = [
            d for d in dirs
            if d not in EXCLUDE_DIRS and os.path.normpath(os.path.join(root, d)) not in excluded_paths
        ]
        files = [
            f for f in files
            if os.path.normpath(os.path.join(root, f)) not in excluded_paths
        ]
        
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

# --------------------------------------------------------------------------
# Supabase Dialog
# --------------------------------------------------------------------------
class SupabaseDialog(tk.Toplevel):
    def __init__(self, parent, base_path):
        super().__init__(parent)
        self.parent = parent
        self.base_path = base_path
        self.title("Supabase Connection")
        self.geometry("700x500")
        self.resizable(True, True)
        self.conn = None

        # Make this a modal dialog
        self.grab_set()

        # Try to load stored connection details
        self.config = load_supabase_config(base_path)

        # Create connection frame
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
        
        # Database
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
        
        # Connect button
        self.connect_button = ttk.Button(conn_frame, text="Connect", command=self.connect_db)
        self.connect_button.grid(row=5, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Status label
        self.status_label = ttk.Label(self, text="Not connected", foreground="red")
        self.status_label.pack(pady=5)
        
        # Tables frame
        tables_frame = ttk.LabelFrame(self, text="Available Tables (public schema)")
        tables_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.tables_listbox = tk.Listbox(tables_frame, selectmode=tk.MULTIPLE)
        self.tables_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(tables_frame, orient="vertical", command=self.tables_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tables_listbox.config(yscrollcommand=scrollbar.set)
        
        # Frame for Export + Skip
        bottom_buttons_frame = ttk.Frame(self)
        bottom_buttons_frame.pack(pady=5)

        self.export_button = ttk.Button(
            bottom_buttons_frame, text="Export Selected Tables", command=self.export_tables, state=tk.DISABLED
        )
        self.export_button.grid(row=0, column=0, padx=5)

        # "Skip" button
        skip_button = ttk.Button(bottom_buttons_frame, text="Skip", command=self.destroy)
        skip_button.grid(row=0, column=1, padx=5)

        # Proceed button
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
            for (table_name,) in tables:
                self.tables_listbox.insert(tk.END, table_name)
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
            json_file = os.path.join(self.base_path, "supabases_tables.json")
            with open(json_file, "w", encoding="utf-8") as f:
                f.write(json_str)
            
            # Replaced old text with the new instructions
            prompt_text = (
                "## Supabase Database Context**\n"
                "- Don't create SQL migrations in the XML output, only return sql commands for me to run on the supabase sql editor directly.\n"
                "- If schema updates are needed, provide the SQL commands **before** the XML output.\n\n"
                "See the relevant tables below:\n---\n"
                + json_str +
                "\n---"
            )
            self.parent.add_supabase_prompt("supabases_tables.json", prompt_text)
            messagebox.showinfo("Export Successful", f"Exported data and prompt added.\nJSON saved at:\n{json_file}")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Export Error", str(e))
            self.destroy()

# --------------------------------------------------------------------------
# Main File Selection / AI Context Builder GUI
# --------------------------------------------------------------------------
class FileSelectorGUI(tk.Tk):
    def __init__(self, base_path):
        super().__init__()
        self.base_path = base_path
        self.title("AI Context Builder Pro")
        self.geometry("1200x900")
        
        # State dictionaries
        self.file_token_counts = {}
        # is_excluded -> path => BooleanVar
        self.exclusion_vars = {}
        # is_selected -> either file_vars or dir_vars
        self.file_vars = {}
        self.dir_vars = {}

        self.prompts_data = {}
        self.tree_item_map = {}  # item_id -> path

        self.context_file = os.path.join(self.base_path, 'ai_context.config')

        # Optional: style for row lines
        style = ttk.Style(self)
        style.configure("Treeview", rowheight=22, bordercolor="black", relief="solid")
        style.map("Treeview", background=[("selected", "#cceeff")])

        self.setup_gui()
        self.load_all_file_tokens()
        self.setup_prompts_frame()
        self.populate_prompts()

        self.insert_root_node()

        # Open Supabase dialog
        self.after(100, self.open_supabase_dialog)

    # ----------------------------------------------------------------------
    # Setup the Treeview
    # ----------------------------------------------------------------------
    def setup_gui(self):
        # Place the tree in a frame with scrollbars
        tree_frame = ttk.Frame(self)
        tree_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("add_code", "exclude"),
            show="tree headings"
        )

        # Column #0: Name
        self.tree.heading("#0", text="Name", anchor="w")
        self.tree.column("#0", minwidth=180, width=300, stretch=True)

        # Add code column
        self.tree.heading("add_code", text="Add Code", anchor="center")
        self.tree.column("add_code", width=80, anchor="center", stretch=False)

        # Exclude column
        self.tree.heading("exclude", text="Exclude", anchor="center")
        self.tree.column("exclude", width=80, anchor="center", stretch=False)

        # Vertical scrollbar
        yscroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=yscroll.set)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Horizontal scrollbar (optional)
        xscroll = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=xscroll.set)
        xscroll.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Bind events
        self.tree.bind("<<TreeviewOpen>>", self.on_tree_expand)
        self.tree.bind("<Button-1>", self.on_tree_click)

        # Tags for color
        self.tree.tag_configure("excluded", foreground="red")
        self.tree.tag_configure("selected", foreground="green")
        self.tree.tag_configure("normal", foreground="black")

        # Control frame
        self.control_frame = ttk.Frame(self)
        self.control_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)

        self.token_label = ttk.Label(self.control_frame, text="Estimated Tokens: 0")
        self.token_label.pack(side=tk.LEFT, padx=10)

        ttk.Button(self.control_frame, text="Generate Output", command=self.generate_output).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.control_frame, text="Save Configuration", command=self.save_configuration).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.control_frame, text="Load Configuration", command=self.load_configuration).pack(side=tk.LEFT, padx=5)

        ttk.Button(self.control_frame, text="Clear all", command=self.clear_all).pack(side=tk.LEFT, padx=5)

    def load_all_file_tokens(self):
        try:
            script_name = os.path.basename(__file__)
        except NameError:
            script_name = ""

        for root, dirs, files in os.walk(self.base_path, topdown=True):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for f in files:
                if f == script_name:
                    continue
                full_path = os.path.join(root, f)
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as ff:
                        content = ff.read()
                    # Rough estimate: 1 token ~ 4 chars
                    self.file_token_counts[full_path] = len(content) // 4
                except Exception:
                    self.file_token_counts[full_path] = 0

    # ----------------------------------------------------------------------
    # Prompts
    # ----------------------------------------------------------------------
    def setup_prompts_frame(self):
        self.prompts_frame = ttk.LabelFrame(self, text="Presaved Prompts")
        self.prompts_frame.pack(fill=tk.X, padx=10, pady=10, side=tk.TOP)
        
        # Left column – available prompts
        available_frame = ttk.Frame(self.prompts_frame)
        available_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        ttk.Label(available_frame, text="Available Prompts").pack()
        self.available_prompts_box = tk.Listbox(available_frame, selectmode=tk.MULTIPLE, width=40, height=6)
        self.available_prompts_box.pack()
        
        # Middle column – control buttons
        buttons_frame = ttk.Frame(self.prompts_frame)
        buttons_frame.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(buttons_frame, text="Add >>", command=self.add_prompt).pack(pady=2)
        ttk.Button(buttons_frame, text="<< Remove", command=self.remove_prompt).pack(pady=2)
        ttk.Button(buttons_frame, text="Move Up", command=self.move_prompt_up).pack(pady=2)
        ttk.Button(buttons_frame, text="Move Down", command=self.move_prompt_down).pack(pady=2)
        
        # Right column – selected prompts (ordered)
        selected_frame = ttk.Frame(self.prompts_frame)
        selected_frame.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")
        ttk.Label(selected_frame, text="Selected Prompts (Ordered)").pack()
        self.selected_prompts_box = tk.Listbox(selected_frame, selectmode=tk.SINGLE, width=40, height=6)
        self.selected_prompts_box.pack()

    def populate_prompts(self):
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

    # ----------------------------------------------------------------------
    # Build the Tree (with lazy loading)
    # ----------------------------------------------------------------------
    def insert_root_node(self):
        base_abs = os.path.abspath(self.base_path)
        display_name = os.path.basename(base_abs) or base_abs
        item_id = self.tree.insert(
            "",
            "end",
            text=display_name,
            values=("Add", "Exclude"),
            open=False
        )
        self.tree_item_map[item_id] = base_abs
        
        self.exclusion_vars[base_abs] = tk.BooleanVar(value=False)
        self.dir_vars[base_abs] = tk.BooleanVar(value=False)

        # Add a dummy child
        self.tree.insert(item_id, "end", text="...")

    def on_tree_expand(self, event):
        """When the user manually expands a node, we load its children (lazy load)."""
        item_id = self.tree.focus()
        if not item_id:
            return
        path = self.tree_item_map.get(item_id)
        if not path:
            return
        
        children = self.tree.get_children(item_id)
        if len(children) == 1:
            dummy = children[0]
            if self.tree.item(dummy, "text") == "...":
                self.tree.delete(dummy)
                self.insert_children(item_id, path)

        # If parent is excluded or selected, propagate that
        if self.exclusion_vars.get(path, tk.BooleanVar()).get():
            self.propagate_exclusion(path, True)
        else:
            if os.path.isdir(path) and self.dir_vars[path].get():
                self.propagate_selection(path, True)

        self.refresh_subtree(item_id)

    def insert_children(self, parent_item, parent_path):
        """Inserts actual child dirs/files for a given directory, if they aren't excluded."""
        try:
            with os.scandir(parent_path) as entries:
                dirs = []
                files = []
                for e in entries:
                    if e.name in EXCLUDE_DIRS:
                        continue
                    if e.is_dir():
                        dirs.append(e.name)
                    else:
                        files.append(e.name)

            dirs.sort()
            files.sort()

            for d in dirs:
                full_path = os.path.join(parent_path, d)
                iid = self.tree.insert(
                    parent_item,
                    "end",
                    text=d,
                    values=("Add", "Exclude"),
                    open=False
                )
                self.tree_item_map[iid] = full_path

                self.exclusion_vars.setdefault(full_path, tk.BooleanVar(value=False))
                self.dir_vars.setdefault(full_path, tk.BooleanVar(value=False))

                # Add a dummy child so we can lazy-load its children
                self.tree.insert(iid, "end", text="...")

                self.update_item_appearance(iid, full_path)

            for f in files:
                full_path = os.path.join(parent_path, f)
                iid = self.tree.insert(
                    parent_item,
                    "end",
                    text=f,
                    values=("Add", "Exclude"),
                    open=False
                )
                self.tree_item_map[iid] = full_path

                self.exclusion_vars.setdefault(full_path, tk.BooleanVar(value=False))
                self.file_vars.setdefault(full_path, tk.BooleanVar(value=False))

                self.update_item_appearance(iid, full_path)

        except PermissionError:
            pass

    # ----------------------------------------------------------------------
    # Expand only one level: the root directory and its immediate children
    # ----------------------------------------------------------------------
    def expand_root_one_level(self):
        """
        Expand the root folder node and load its children,
        then for each direct child folder, load their children
        but do not expand the grandchildren further.
        """
        root_items = self.tree.get_children("")
        for item_id in root_items:
            # Expand the root item itself
            self.tree.item(item_id, open=True)
            path = self.tree_item_map.get(item_id)
            if path:
                # If the root has a dummy child, remove it and insert real children
                kids = self.tree.get_children(item_id)
                if len(kids) == 1:
                    dummy_id = kids[0]
                    if self.tree.item(dummy_id, "text") == "...":
                        self.tree.delete(dummy_id)
                        self.insert_children(item_id, path)
                # Now open each immediate child folder (just enough to see one level deeper)
                child_items = self.tree.get_children(item_id)
                for cid in child_items:
                    cpath = self.tree_item_map.get(cid)
                    if not cpath:
                        continue
                    if os.path.isdir(cpath):
                        # Expand this child folder to load its sub-children (one more level).
                        self.tree.item(cid, open=True)
                        # If that child folder has a dummy child, remove it
                        cc = self.tree.get_children(cid)
                        if len(cc) == 1 and self.tree.item(cc[0], "text") == "...":
                            self.tree.delete(cc[0])
                            self.insert_children(cid, cpath)

    # ----------------------------------------------------------------------
    # Single-click toggles
    # ----------------------------------------------------------------------
    def on_tree_click(self, event):
        col_str = self.tree.identify_column(event.x)  # "#0", "#1", "#2", ...
        item_id = self.tree.identify_row(event.y)
        if not item_id or item_id == "":
            return

        path = self.tree_item_map.get(item_id)
        if not path:
            return

        # #1 => add_code, #2 => exclude, #0 => Name
        if col_str == "#1":
            self.handle_add_code(path)
            self.refresh_subtree(item_id)
        elif col_str == "#2":
            self.handle_exclude(path)
            self.refresh_subtree(item_id)

        self.update_token_count()

    def handle_add_code(self, path):
        """Toggle between selected/unselected (also clears exclusion)."""
        if os.path.isdir(path):
            currently_selected = self.dir_vars[path].get()
            if currently_selected:
                self.dir_vars[path].set(False)
                self.propagate_selection(path, False)
            else:
                self.exclusion_vars[path].set(False)
                self.dir_vars[path].set(True)
                self.propagate_selection(path, True)
        else:
            currently_selected = self.file_vars[path].get()
            if currently_selected:
                self.file_vars[path].set(False)
            else:
                self.exclusion_vars[path].set(False)
                self.file_vars[path].set(True)

    def handle_exclude(self, path):
        """Toggle between excluded/not-excluded (also unselect if excluded)."""
        currently_excluded = self.exclusion_vars[path].get()
        self.propagate_exclusion(path, not currently_excluded)

    # ----------------------------------------------------------------------
    # Propagation & Refresh
    # ----------------------------------------------------------------------
    def propagate_exclusion(self, path, new_state):
        self.exclusion_vars[path].set(new_state)
        if os.path.isdir(path):
            if new_state:
                self.dir_vars[path].set(False)
            for root, dirs, files in os.walk(path, topdown=True):
                dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
                for d in dirs:
                    fp = os.path.join(root, d)
                    self.exclusion_vars.setdefault(fp, tk.BooleanVar(value=False)).set(new_state)
                    self.dir_vars.setdefault(fp, tk.BooleanVar(value=False)).set(False)
                for f in files:
                    fp = os.path.join(root, f)
                    self.exclusion_vars.setdefault(fp, tk.BooleanVar(value=False)).set(new_state)
                    self.file_vars.setdefault(fp, tk.BooleanVar(value=False)).set(False)
        else:
            self.file_vars[path].set(False)

    def propagate_selection(self, path, new_state):
        if os.path.isdir(path):
            self.dir_vars[path].set(new_state)
            self.exclusion_vars[path].set(False)
            for root, dirs, files in os.walk(path, topdown=True):
                dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
                for d in dirs:
                    fp = os.path.join(root, d)
                    self.dir_vars.setdefault(fp, tk.BooleanVar(value=False)).set(new_state)
                    self.exclusion_vars.setdefault(fp, tk.BooleanVar(value=False)).set(False)
                for f in files:
                    fp = os.path.join(root, f)
                    self.file_vars.setdefault(fp, tk.BooleanVar(value=False)).set(new_state)
                    self.exclusion_vars.setdefault(fp, tk.BooleanVar(value=False)).set(False)
        else:
            self.file_vars[path].set(new_state)
            self.exclusion_vars[path].set(False)

    def refresh_subtree(self, item_id):
        path = self.tree_item_map.get(item_id)
        if path:
            self.update_item_appearance(item_id, path)
        for child_id in self.tree.get_children(item_id):
            self.refresh_subtree(child_id)

    def update_item_appearance(self, item_id, path):
        excluded = self.exclusion_vars.get(path, tk.BooleanVar()).get()
        if os.path.isdir(path):
            selected = self.dir_vars[path].get()
        else:
            selected = self.file_vars[path].get()

        if excluded:
            color_tag = "excluded"
            add_code_text = "Add"
            exclude_text = "X"
        else:
            if selected:
                color_tag = "selected"
                add_code_text = "Yes"
                exclude_text = "Exclude"
            else:
                color_tag = "normal"
                add_code_text = "Add"
                exclude_text = "Exclude"

        self.tree.item(item_id, tags=(color_tag,))
        self.tree.set(item_id, "add_code", add_code_text)
        self.tree.set(item_id, "exclude", exclude_text)

    # ----------------------------------------------------------------------
    # Query states
    # ----------------------------------------------------------------------
    @property
    def excluded_paths(self):
        return {p for p, var in self.exclusion_vars.items() if var.get()}

    def get_selected_files(self):
        return sorted(
            p
            for p, var in self.file_vars.items()
            if var.get() and not self.exclusion_vars[p].get()
        )

    # ----------------------------------------------------------------------
    # Clear all
    # ----------------------------------------------------------------------
    def clear_all(self):
        """Resets all selections, exclusions, and prompts."""
        for p in self.exclusion_vars:
            self.exclusion_vars[p].set(False)
        for p in self.dir_vars:
            self.dir_vars[p].set(False)
        for p in self.file_vars:
            self.file_vars[p].set(False)

        self.selected_prompts_box.delete(0, tk.END)
        self.available_prompts_box.delete(0, tk.END)

        # Repopulate "available" from self.prompts_data
        for fname in sorted(self.prompts_data.keys()):
            self.available_prompts_box.insert(tk.END, fname)

        # Refresh the visible portion
        for item_id in self.tree.get_children():
            self.refresh_subtree(item_id)

        self.update_token_count()

    # ----------------------------------------------------------------------
    # Supabase integration
    # ----------------------------------------------------------------------
    def open_supabase_dialog(self):
        dialog = SupabaseDialog(self, self.base_path)
        self.wait_window(dialog)
        self.update_token_count()

    def add_supabase_prompt(self, prompt_key, prompt_text):
        token_count = len(prompt_text) // 4
        self.prompts_data[prompt_key] = {"path": None, "content": prompt_text, "tokens": token_count}
        # If not in either list, add to "available" 
        if prompt_key not in self.available_prompts_box.get(0, tk.END) \
           and prompt_key not in self.selected_prompts_box.get(0, tk.END):
            self.available_prompts_box.insert(tk.END, prompt_key)
        self.update_token_count()

    # ----------------------------------------------------------------------
    # Prompts logic
    # ----------------------------------------------------------------------
    def add_prompt(self):
        selection = self.available_prompts_box.curselection()
        for index in selection[::-1]:
            fname = self.available_prompts_box.get(index)
            if fname not in self.selected_prompts_box.get(0, tk.END):
                self.selected_prompts_box.insert(tk.END, fname)
            self.available_prompts_box.delete(index)
        self.update_token_count()
            
    def remove_prompt(self):
        selection = self.selected_prompts_box.curselection()
        for index in selection[::-1]:
            fname = self.selected_prompts_box.get(index)
            self.selected_prompts_box.delete(index)
            # Insert back into available, keep it sorted
            items = list(self.available_prompts_box.get(0, tk.END))
            items.append(fname)
            items.sort()
            self.available_prompts_box.delete(0, tk.END)
            for it in items:
                self.available_prompts_box.insert(tk.END, it)
        self.update_token_count()
    
    def move_prompt_up(self):
        selection = self.selected_prompts_box.curselection()
        if not selection:
            return
        idx = selection[0]
        if idx > 0:
            item = self.selected_prompts_box.get(idx)
            self.selected_prompts_box.delete(idx)
            self.selected_prompts_box.insert(idx-1, item)
            self.selected_prompts_box.selection_clear(0, tk.END)
            self.selected_prompts_box.selection_set(idx-1)
        self.update_token_count()
    
    def move_prompt_down(self):
        selection = self.selected_prompts_box.curselection()
        if not selection:
            return
        idx = selection[0]
        if idx < self.selected_prompts_box.size() - 1:
            item = self.selected_prompts_box.get(idx)
            self.selected_prompts_box.delete(idx)
            self.selected_prompts_box.insert(idx+1, item)
            self.selected_prompts_box.selection_clear(0, tk.END)
            self.selected_prompts_box.selection_set(idx+1)
        self.update_token_count()

    def update_token_count(self):
        selected_files = self.get_selected_files()
        total_file_tokens = sum(self.file_token_counts.get(fp, 0) for fp in selected_files)

        total_prompt_tokens = 0
        if hasattr(self, "selected_prompts_box"):
            for fname in self.selected_prompts_box.get(0, tk.END):
                pd = self.prompts_data.get(fname)
                if pd:
                    total_prompt_tokens += pd["tokens"]

        total = total_file_tokens + total_prompt_tokens
        self.token_label.config(text=f"Estimated Tokens: {total}")

    # ----------------------------------------------------------------------
    # Save / Load configuration
    # ----------------------------------------------------------------------
    def save_configuration(self):
        config = {
            'excluded_paths': list(self.excluded_paths),
            'selected_files': [p for p, var in self.file_vars.items() if var.get()],
            'selected_dirs': [p for p, var in self.dir_vars.items() if var.get()],
            'selected_prompts': list(self.selected_prompts_box.get(0, tk.END)),
        }
        try:
            with open(self.context_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            messagebox.showinfo("Success", f"Configuration saved to:\n{self.context_file}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {str(e)}")
            
    def load_configuration(self):
        """Load the config, reset everything, expand root + children, apply states."""
        try:
            with open(self.context_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 1) Clear everything
            self.clear_all()
            # 2) Expand one level so we can see root + immediate children
            self.expand_root_one_level()

            # 3) Now set states from the config
            for p in config.get('excluded_paths', []):
                if p in self.exclusion_vars:
                    self.exclusion_vars[p].set(True)

            for d in config.get('selected_dirs', []):
                if d in self.dir_vars:
                    self.dir_vars[d].set(True)

            for fpath in config.get('selected_files', []):
                if fpath in self.file_vars:
                    self.file_vars[fpath].set(True)

            # 4) Restore selected prompts
            for sp in config.get('selected_prompts', []):
                if sp in self.prompts_data:  # Must exist in known prompts
                    if sp in self.available_prompts_box.get(0, tk.END):
                        idx = list(self.available_prompts_box.get(0, tk.END)).index(sp)
                        self.available_prompts_box.delete(idx)
                    if sp not in self.selected_prompts_box.get(0, tk.END):
                        self.selected_prompts_box.insert(tk.END, sp)

            # 5) Refresh so appearance matches
            for item_id in self.tree.get_children():
                self.refresh_subtree(item_id)

            # 6) Update token count
            self.update_token_count()
            messagebox.showinfo("Success", "Configuration loaded successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load configuration: {str(e)}")

    # ----------------------------------------------------------------------
    # Generate Output
    # ----------------------------------------------------------------------
    def generate_output(self):
        output_file = os.path.join(self.base_path, 'output.txt')
        selected_files = self.get_selected_files()
        
        try:
            with open(output_file, 'w', encoding='utf-8') as outfile:
                # Presaved prompts
                if self.selected_prompts_box.size() > 0:
                    for fname in self.selected_prompts_box.get(0, tk.END):
                        prompt_data = self.prompts_data.get(fname)
                        if prompt_data:
                            outfile.write(f"```\n{prompt_data['content']}\n```\n\n")
                
                # Directory structure
                outfile.write("Directory Structure:\n")
                outfile.write(get_directory_tree(self.base_path, self.excluded_paths))
                
                # Selected files
                if selected_files:
                    outfile.write("\nImportant Code Files:\n\n")
                    for fp in selected_files:
                        relative_path = os.path.relpath(fp, self.base_path)
                        outfile.write(f"File: {relative_path}\n```\n")
                        try:
                            with open(fp, 'r', encoding='utf-8', errors='ignore') as ff:
                                outfile.write(ff.read())
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

# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
if __name__ == "__main__":
    base_path = os.path.dirname(os.path.abspath(__file__))
    app = FileSelectorGUI(base_path)
    app.mainloop()
