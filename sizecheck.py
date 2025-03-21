import os
import tkinter as tk
from tkinter import filedialog, ttk,messagebox
from threading import Thread
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil
""""""
def get_folder_size(path):
    total_size = 0
    def handle_error(error):
        print(f"Error accessing directory: {error.filename}")
    
    for dirpath, _, filenames in os.walk(path, onerror=lambda error: handle_error(error)):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total_size += os.path.getsize(fp)
            except OSError as e:
                print(f"Error accessing file {fp}: {e}")
    return total_size

def find_largest_folders(base_path, top_n=10):
    try:
        with os.scandir(base_path) as entries:
            folders = [entry.path for entry in entries if entry.is_dir()]
    except OSError as e:
        return [], f"Error accessing directory: {e}"

    folder_sizes = []
    with ThreadPoolExecutor() as executor:
        future_to_folder = {executor.submit(get_folder_size, folder): folder for folder in folders}
        for future in as_completed(future_to_folder):
            folder = future_to_folder[future]
            try:
                size = future.result()
                folder_sizes.append((folder, size))
            except Exception as e:
                print(f"Error processing {folder}: {e}")

    folder_sizes.sort(key=lambda x: x[1], reverse=True)
    return folder_sizes[:top_n], ""

def format_size(size_bytes):
    for unit in ['bytes', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def sort_treeview(tree, col, reverse):
    data = [(tree.set(child, col), child) for child in tree.get_children('')]
    data.sort(reverse=reverse, key=lambda x: float(x[0]) if col == "#3" else x[0])
    for index, (val, child) in enumerate(data):
        tree.move(child, '', index)
    tree.heading(col, command=lambda: sort_treeview(tree, col, not reverse))

def delete_folder(folder_path):
    try:
        shutil.rmtree(folder_path)
        return True, ""
    except Exception as e:
        return False, str(e)

def on_treeview_click(event):
    # Identify clicked region
    region = tree.identify("region", event.x, event.y)
    if region == "cell":
        column = tree.identify_column(event.x)
        item = tree.identify_row(event.y)
        
        # Only handle clicks on Delete column (column 4)
        if column == "#4":
            folder_path = tree.item(item)['values'][0]
            
            # Confirmation dialog
            confirm = messagebox.askyesno(
                "Confirm Delete",
                f"Permanently delete this folder?\n{folder_path}",
                icon='warning'
            )
            
            if confirm:
                success, error = delete_folder(folder_path)
                if success:
                    tree.delete(item)
                    status_bar.config(text=f"Successfully deleted: {folder_path}")
                else:
                    messagebox.showerror(
                        "Deletion Error",
                        f"Could not delete folder:\n{error}"
                    )


def scan_folders():
    folder_path = filedialog.askdirectory()
    if not folder_path:
        return

    select_button.config(state=tk.DISABLED)
    status_bar.config(text="Scanning... Please wait...")
    progress_bar.config(mode='indeterminate')
    progress_bar.start()

    def scan():  # Properly nested inside scan_folders
        try:
            results, error = find_largest_folders(folder_path)
            if error:
                root.after(0, lambda: status_bar.config(text=error))
                return

            root.after(0, lambda: tree.delete(*tree.get_children()))
            
            for folder, size in results:
                root.after(0, lambda f=folder, s=size: tree.insert(
                    "", "end", values=(f, format_size(s), s, "🗑️ Delete")
                ))
            
            root.after(0, lambda: status_bar.config(text=f"Found {len(results)} results"))
        except Exception as e:
            root.after(0, lambda: status_bar.config(text=f"Error: {str(e)}"))
        finally:
            root.after(0, progress_bar.stop)
            root.after(0, lambda: select_button.config(state=tk.NORMAL))

    # Start the thread AFTER defining the scan function
    Thread(target=scan, daemon=True).start()

def delete_folder(folder_path):
    try:
        if not os.path.exists(folder_path):
            return False, "Folder does not exist"
            
        if not os.path.isdir(folder_path):
            return False, "Path is not a directory"
            
        if os.path.samefile(folder_path, os.path.expanduser("~")):
            return False, "Cannot delete home directory"
            
        shutil.rmtree(folder_path)
        return True, ""
    except Exception as e:
        return False, str(e)
# GUI Setup
# GUI Setup with improved visual elements
root = tk.Tk()
root.title("Disk Space Analyzer Pro")
root.geometry("1024x768")
root.configure(bg='#f0f0f0')

# Custom style configuration
style = ttk.Style()
style.theme_use('vista')
style.configure('TFrame', background='#f0f0f0')
style.configure('TButton', font=('Segoe UI', 10), padding=6)
style.configure('Header.TLabel', font=('Segoe UI', 11, 'bold'), background='#3a7ff0', foreground='white')
style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'))
style.configure('Treeview', rowheight=28, font=('Segoe UI', 10))
style.map('Treeview.Heading', background=[('active', '#4a90e2')])

main_frame = ttk.Frame(root)
main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

# Header Section
header_frame = ttk.Frame(main_frame)
header_frame.pack(fill=tk.X, pady=(0, 10))

ttk.Label(header_frame, text="Disk Space Analyzer", style='Header.TLabel').pack(side=tk.LEFT, padx=10)
ttk.Separator(header_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)

# Control Panel
control_frame = ttk.Frame(main_frame)
control_frame.pack(fill=tk.X, pady=10)

select_button = ttk.Button(control_frame, text="📁 Select Folder to Scan", command=scan_folders, style='TButton')
select_button.pack(side=tk.LEFT, padx=5)

progress_bar = ttk.Progressbar(control_frame, mode='indeterminate')
progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

# Results Section
results_frame = ttk.Frame(main_frame)
results_frame.pack(fill=tk.BOTH, expand=True)

columns = ("Folder", "Size", "RawSize", "Delete")
tree = ttk.Treeview(results_frame, columns=columns, show="headings", selectmode='browse')

# Column Configuration
tree.column("Folder", width=500, anchor=tk.W)
tree.column("Size", width=150, anchor=tk.W)
tree.column("RawSize", width=0, stretch=tk.NO)
tree.column("Delete", width=80, anchor=tk.CENTER)  # Delete column

tree.heading("Folder", text="Folder Path", anchor=tk.W)
tree.heading("Size", text="Size", anchor=tk.W)
tree.heading("RawSize", text="")
tree.heading("Delete", text="Action")  # Delete column header

tree.bind('<Button-1>', on_treeview_click)
# Scrollbars
vsb = ttk.Scrollbar(results_frame, orient="vertical", command=tree.yview)
hsb = ttk.Scrollbar(results_frame, orient="horizontal", command=tree.xview)
tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

tree.grid(column=0, row=0, sticky='nsew')
vsb.grid(column=1, row=0, sticky='ns')
hsb.grid(column=0, row=1, sticky='ew')
results_frame.grid_columnconfigure(0, weight=1)
results_frame.grid_rowconfigure(0, weight=1)

# Status indication label
status_bar = ttk.Label(main_frame, text="Ready to scan", font=('Segoe UI', 10))
status_bar.pack(fill=tk.X, pady=(0, 5))

def show_context_menu(event):
    item = tree.identify_row(event.y)
    if item:
        tree.selection_set(item)
        context_menu.tk_popup(event.x_root, event.y_root)

tree.bind("<Button-3>", show_context_menu)

root.mainloop()