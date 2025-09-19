import time
from ping3 import ping
import tkinter as tk
from tkinter import messagebox, Entry, Button, Frame, Label, Scrollbar, Canvas, Text, OptionMenu
from threading import Thread, Lock
import queue
import os
import platform
import subprocess
import re
import sys

# Constants
PING_INTERVAL = 5  # Seconds between pings
TIMEOUT_THRESHOLD = 60  # Seconds to consider IP unresponsive
SOUND_FILE = "notification.wav"  # Path to your sound file (for macOS/Linux)
IP_FILE = "ip_list.txt"  # File to store IPs and names
CONFIG_FILE = "config.txt"  # File to store theme preference

# Theme definitions
THEMES = {
    "Light": {
        "window_bg": "#FFFFFF",
        "frame_bg": "#FFFFFF",
        "label_bg": "#FFFFFF",
        "label_fg": "#000000",
        "button_bg": "#E0E0E0",
        "button_fg": "#000000",
        "canvas_bg": "#FFFFFF",
        "text_bg": "#FFFFFF",
        "text_fg": "#000000",
        "highlight_bg": "#FFFF00",  # Yellow for selected IP
        "status_online": "#00FF00",
        "status_offline": "#FF0000",
        "status_unknown": "#CCCCCC"
    },
    "Dark": {
        "window_bg": "#2E2E2E",
        "frame_bg": "#2E2E2E",
        "label_bg": "#2E2E2E",
        "label_fg": "#FFFFFF",
        "button_bg": "#4A4A4A",
        "button_fg": "#FFFFFF",
        "canvas_bg": "#2E2E2E",
        "text_bg": "#1E1E1E",
        "text_fg": "#FFFFFF",
        "highlight_bg": "#FFFF00",  # Yellow for selected IP
        "status_online": "#00FF00",
        "status_offline": "#FF0000",
        "status_unknown": "#555555"
    }
}

# Thread-safe queues
popup_queue = queue.Queue()
status_queue = queue.Queue()
log_queue = queue.Queue()
lock = Lock()
# Global flag for popup activation (disabled on startup)
popups_enabled = False
# Dictionaries to store status, response time, and names
status_labels = {}
response_time_labels = {}
names = {}
# Global variables for GUI
scrollable_frame = None
canvas = None
log_text = None
selected_ip = None  # Track selected IP
ip_labels = {}  # Map IPs to their labels
current_theme = "Light"  # Default theme
# Flag to stop threads
running = True


def load_config():
    """Load theme from config file, return default if file doesn't exist."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                theme = f.read().strip()
                return theme if theme in THEMES else "Light"
        except Exception as e:
            print(f"Error loading config: {e}")
    return "Light"


def save_config(theme):
    """Save theme to config file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            f.write(theme)
    except Exception as e:
        print(f"Error saving config: {e}")


def apply_theme(theme_name):
    """Apply the specified theme to all widgets."""
    global current_theme
    current_theme = theme_name
    theme = THEMES[theme_name]

    try:
        # Update root window
        root.configure(bg=theme["window_bg"])

        # Update frames
        ip_frame.configure(bg=theme["frame_bg"])
        button_frame.configure(bg=theme["frame_bg"])
        log_frame.configure(bg=theme["frame_bg"])
        scrollable_frame.configure(bg=theme["frame_bg"])

        # Update canvas
        canvas.configure(bg=theme["canvas_bg"])

        # Update labels
        for child in root.winfo_children():
            if isinstance(child, Label):
                child.configure(bg=theme["label_bg"], fg=theme["label_fg"])
        for ip in ip_labels:
            row_frame = ip_labels[ip].master
            row_frame.configure(bg=theme["frame_bg"])
            ip_labels[ip].configure(bg=theme["label_bg"], fg=theme["label_fg"])
            row_frame.winfo_children()[1].configure(bg=theme["label_bg"], fg=theme["label_fg"])  # Name
            status_labels[ip].configure(fg=theme["label_fg"])
            response_time_labels[ip].configure(bg=theme["label_bg"], fg=theme["label_fg"])

        # Update buttons and theme menu
        for child in button_frame.winfo_children():
            if isinstance(child, (Button, OptionMenu)):
                child.configure(bg=theme["button_bg"], fg=theme["button_fg"])

        # Update log text
        log_text.configure(bg=theme["text_bg"], fg=theme["text_fg"])

        # Save theme
        save_config(theme_name)

        print(f"Applied theme: {theme_name}")
    except Exception as e:
        print(f"Error applying theme {theme_name}: {e}")


def load_ip_list():
    """Load IPs and names from file, return default list if file doesn't exist."""
    default_ips = [("8.8.8.8", "Google DNS"), ("1.1.1.1", "Cloudflare DNS"), ("192.168.1.1", "Router")]
    if os.path.exists(IP_FILE):
        try:
            with open(IP_FILE, 'r') as f:
                pairs = []
                for line in f:
                    parts = line.strip().split(',', 1)
                    if len(parts) >= 1 and validate_ip(parts[0]):
                        ip = parts[0]
                        name = parts[1] if len(parts) > 1 and parts[1].strip() else "N/A"
                        pairs.append((ip, name))
                return pairs if pairs else default_ips
        except Exception as e:
            print(f"Error loading IP list: {e}")
    return default_ips


def save_ip_list(ip_name_pairs):
    """Save IPs and names to file."""
    try:
        with open(IP_FILE, 'w') as f:
            for ip, name in ip_name_pairs:
                f.write(f"{ip},{name}\n")
    except Exception as e:
        print(f"Error saving IP list: {e}")


def validate_ip(ip):
    """Validate IP address format."""
    pattern = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    return bool(re.match(pattern, ip))


def play_sound():
    """Play a notification sound based on the operating system."""
    if not popups_enabled:
        return
    system = platform.system()
    try:
        if system == "Windows":
            import winsound
            winsound.Beep(1000, 500)
        elif system == "Darwin":  # macOS
            if os.path.exists(SOUND_FILE):
                subprocess.run(["afplay", SOUND_FILE], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                print(f"Sound file {SOUND_FILE} not found")
        elif system == "Linux":
            if os.path.exists(SOUND_FILE):
                subprocess.run(["aplay", SOUND_FILE], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                print(f"Sound file {SOUND_FILE} not found")
        else:
            print(f"Sound playback not supported on {system}")
    except Exception as e:
        print(f"Error playing sound: {e}")


def show_popup(message):
    """Display a popup with the given message and play a sound."""
    if not popups_enabled:
        return
    Thread(target=play_sound, daemon=True).start()
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("IP Status", message)
    root.destroy()


def process_popup_queue():
    """Process the popup queue in the main thread."""
    try:
        while True:
            message = popup_queue.get_nowait()
            show_popup(message)
    except queue.Empty:
        pass


def process_status_queue():
    """Process the status queue to update GUI indicators."""
    try:
        while True:
            ip, is_responding, response_time = status_queue.get_nowait()
            if ip in status_labels:
                status_labels[ip].config(
                    bg=THEMES[current_theme]["status_online"] if is_responding else THEMES[current_theme][
                        "status_offline"],
                    text="Online" if is_responding else "Offline"
                )
                response_time_labels[ip].config(
                    text=f"{int(response_time * 1000)} ms" if is_responding else "N/A"
                )
    except queue.Empty:
        pass


def process_log_queue():
    """Process the log queue to update the log window."""
    try:
        while True:
            message = log_queue.get_nowait()
            log_text.config(state="normal")
            log_text.insert(tk.END, f"{message}\n")
            log_text.see(tk.END)
            log_text.config(state="disabled")
    except queue.Empty:
        pass


def process_queues():
    """Process all queues."""
    if not running:
        return
    process_popup_queue()
    process_status_queue()
    process_log_queue()
    root.after(100, process_queues)


def monitor_ip(ip):
    """Monitor a single IP address."""
    was_responsive = False
    last_response_time = time.time()

    while running:
        try:
            response_time = ping(ip, timeout=2)
            current_time = time.time()

            with lock:
                is_responding = response_time is not None
                status_queue.put((ip, is_responding, response_time if response_time is not None else 0))

                name = names.get(ip, "N/A")
                display_name = name if name != "N/A" else f"IP {ip}"

                if is_responding and not was_responsive:
                    message = f"{time.strftime('%Y-%m-%d %H:%M:%S')}: {display_name} is responding"
                    popup_queue.put(message)
                    log_queue.put(message)
                    was_responsive = True
                    last_response_time = current_time
                elif not is_responding and was_responsive:
                    if current_time - last_response_time >= TIMEOUT_THRESHOLD:
                        message = f"{time.strftime('%Y-%m-%d %H:%M:%S')}: {display_name} stopped responding"
                        popup_queue.put(message)
                        log_queue.put(message)
                        was_responsive = False
                elif is_responding:
                    last_response_time = current_time
        except Exception as e:
            print(f"Error pinging {ip}: {e}")

        time.sleep(PING_INTERVAL)


def create_gui():
    """Create the main GUI window."""
    global root, ip_frame, button_frame, log_frame, popup_button, scrollable_frame, canvas, log_text
    root = tk.Tk()
    root.title("Hip-no-ping IP Monitor By Richeee")
    root.geometry("500x900")  # Reduced height due to horizontal buttons

    # Handle window close
    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Load and apply theme
    global current_theme
    current_theme = load_config()

    # Frame for IP list and status
    tk.Label(root, text="IP Addresses and Status:").pack(pady=5)
    ip_frame = Frame(root)
    ip_frame.pack(pady=5, padx=5, fill=tk.BOTH, expand=True)

    # Scrollbar and Canvas
    canvas = Canvas(ip_frame)
    scrollbar = Scrollbar(ip_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = Frame(canvas)
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Bind mouse wheel for scrolling
    def on_mouse_wheel(event):
        canvas.yview_scroll(-1 * (event.delta // 120), "units")

    canvas.bind_all("<MouseWheel>", on_mouse_wheel)  # Windows
    canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))  # Linux/macOS
    canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))  # Linux/macOS

    # Load initial IPs and names
    ip_name_pairs = load_ip_list()
    for ip, name in ip_name_pairs:
        names[ip] = name
        add_ip_to_frame(ip)

    # Button frame for horizontal layout
    button_frame = Frame(root)
    button_frame.pack(pady=5, fill=tk.X)
    tk.Button(button_frame, text="Add", command=add_ip).pack(side=tk.LEFT, padx=2)
    tk.Button(button_frame, text="Edit", command=edit_ip).pack(side=tk.LEFT, padx=2)
    tk.Button(button_frame, text="Remove", command=remove_ip).pack(side=tk.LEFT, padx=2)
    tk.Button(button_frame, text="Save", command=save_ips).pack(side=tk.LEFT, padx=2)
    popup_button = tk.Button(button_frame, text="Enable Popups", command=toggle_popups)
    popup_button.pack(side=tk.LEFT, padx=2)

    # Theme selection menu
    theme_var = tk.StringVar(value=current_theme)
    theme_menu = OptionMenu(button_frame, theme_var, *THEMES.keys(), command=lambda theme: apply_theme(theme))
    theme_menu.configure(width=8)
    theme_menu.pack(side=tk.LEFT, padx=2)

    # Log window
    tk.Label(root, text="Event Log:").pack(pady=5)
    log_frame = Frame(root)
    log_frame.pack(pady=5, padx=5, fill=tk.BOTH, expand=False)
    log_text = Text(log_frame, height=10, width=40, state="disabled")
    log_scrollbar = Scrollbar(log_frame, orient="vertical", command=log_text.yview)
    log_text.configure(yscrollcommand=log_scrollbar.set)
    log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Apply initial theme
    apply_theme(current_theme)

    # Start monitoring threads
    for ip, _ in ip_name_pairs:
        Thread(target=monitor_ip, args=(ip,), daemon=True).start()

    root.after(100, process_queues)
    root.mainloop()


def add_ip_to_frame(ip):
    """Add an IP and its status indicator to the GUI."""
    global scrollable_frame, canvas
    row_frame = Frame(scrollable_frame)
    row_frame.pack(fill=tk.X, pady=2)
    ip_label = Label(row_frame, text=ip, width=15, anchor="w")
    ip_label.pack(side=tk.LEFT)
    ip_label.bind("<Button-1>", lambda e: select_ip(ip))
    ip_labels[ip] = ip_label  # Store label reference
    name_label = Label(row_frame, text=names.get(ip, "N/A"), width=15, anchor="w")
    name_label.pack(side=tk.LEFT, padx=5)
    status_label = Label(row_frame, text="Unknown", bg=THEMES[current_theme]["status_unknown"], width=10)
    status_label.pack(side=tk.LEFT, padx=5)
    response_time_label = Label(row_frame, text="N/A", width=10)
    response_time_label.pack(side=tk.LEFT, padx=5)
    status_labels[ip] = status_label
    response_time_labels[ip] = response_time_label
    # Apply theme to new row
    row_frame.configure(bg=THEMES[current_theme]["frame_bg"])
    ip_label.configure(bg=THEMES[current_theme]["label_bg"], fg=THEMES[current_theme]["label_fg"])
    name_label.configure(bg=THEMES[current_theme]["label_bg"], fg=THEMES[current_theme]["label_fg"])
    status_label.configure(fg=THEMES[current_theme]["label_fg"])
    response_time_label.configure(bg=THEMES[current_theme]["label_bg"], fg=THEMES[current_theme]["label_fg"])
    canvas.configure(scrollregion=canvas.bbox("all"))


def select_ip(ip):
    """Highlight the selected IP."""
    global selected_ip
    try:
        # Reset all labels to default background
        for label in ip_labels.values():
            label.config(bg=THEMES[current_theme]["label_bg"])
        # Highlight the selected IP
        if ip in ip_labels:
            ip_labels[ip].config(bg=THEMES[current_theme]["highlight_bg"])
            selected_ip = ip
        else:
            selected_ip = None
        print(f"Selected IP: {selected_ip}")  # Debug
    except Exception as e:
        print(f"Error in select_ip for IP {ip}: {e}")


def add_ip():
    """Open a dialog to add a new IP."""
    dialog = tk.Toplevel(root)
    dialog.title("Add IP")
    dialog.geometry("250x250")
    dialog.configure(bg=THEMES[current_theme]["window_bg"])
    tk.Label(dialog, text="Enter IP:", bg=THEMES[current_theme]["label_bg"], fg=THEMES[current_theme]["label_fg"]).pack(
        pady=5)
    ip_entry = Entry(dialog)
    ip_entry.pack(pady=5)
    tk.Label(dialog, text="Enter Name (optional):", bg=THEMES[current_theme]["label_bg"],
             fg=THEMES[current_theme]["label_fg"]).pack(pady=5)
    name_entry = Entry(dialog)
    name_entry.pack(pady=5)

    def submit():
        print("Add IP submit clicked")  # Debug
        ip = ip_entry.get().strip()
        name = name_entry.get().strip() or "N/A"
        print(f"Adding IP: {ip}, Name: {name}")  # Debug
        if validate_ip(ip):
            print(f"IP {ip} is valid")  # Debug
            if ip not in status_labels:
                print(f"IP {ip} is not in list, adding")  # Debug
                names[ip] = name
                add_ip_to_frame(ip)
                Thread(target=monitor_ip, args=(ip,), daemon=True).start()
                dialog.destroy()
            else:
                print(f"IP {ip} already in list")  # Debug
                messagebox.showerror("Error", "IP already in list")
        else:
            print(f"IP {ip} is invalid")  # Debug
            messagebox.showerror("Error", "Invalid IP address")

    tk.Button(dialog, text="Submit", bg=THEMES[current_theme]["button_bg"], fg=THEMES[current_theme]["button_fg"],
              command=submit).pack(pady=5)


def edit_ip():
    """Open a dialog to edit the selected IP."""
    global selected_ip
    if not selected_ip:
        print("Edit IP: No IP selected")  # Debug
        messagebox.showerror("Error", "Select an IP to edit")
        return
    try:
        print(f"Edit IP: Opening dialog for {selected_ip}")  # Debug
        old_ip = selected_ip
        old_name = names.get(old_ip, "N/A")

        dialog = tk.Toplevel(root)
        dialog.title("Edit IP")
        dialog.geometry("250x250")
        dialog.configure(bg=THEMES[current_theme]["window_bg"])
        tk.Label(dialog, text="Edit IP:", bg=THEMES[current_theme]["label_bg"],
                 fg=THEMES[current_theme]["label_fg"]).pack(pady=5)
        ip_entry = Entry(dialog)
        ip_entry.insert(0, old_ip)
        ip_entry.pack(pady=5)
        tk.Label(dialog, text="Edit Name (optional):", bg=THEMES[current_theme]["label_bg"],
                 fg=THEMES[current_theme]["label_fg"]).pack(pady=5)
        name_entry = Entry(dialog)
        name_entry.insert(0, old_name if old_name != "N/A" else "")
        name_entry.pack(pady=5)

        def submit():
            global selected_ip
            print("Edit IP submit clicked")  # Debug
            new_ip = ip_entry.get().strip()
            new_name = name_entry.get().strip() or "N/A"
            print(f"Editing IP: {old_ip} -> {new_ip}, Name: {old_name} -> {new_name}")  # Debug
            if not validate_ip(new_ip):
                print(f"IP {new_ip} is invalid")  # Debug
                messagebox.showerror("Error", "Invalid IP address")
                return
            print(f"IP {new_ip} is valid")  # Debug
            if new_ip in status_labels and new_ip != old_ip:
                print(f"IP {new_ip} already in list")  # Debug
                messagebox.showerror("Error", "IP already in list")
                return
            print(f"Updating IP {old_ip} to {new_ip}")  # Debug
            # Update dictionaries
            status_labels[new_ip] = status_labels.pop(old_ip)
            response_time_labels[new_ip] = response_time_labels.pop(old_ip)
            names[new_ip] = new_name
            names.pop(old_ip, None)
            # Update label reference
            ip_labels[new_ip] = ip_labels.pop(old_ip)
            ip_labels[new_ip].config(text=new_ip, bg=THEMES[current_theme]["label_bg"])
            # Update name label
            ip_labels[new_ip].master.winfo_children()[1].config(text=new_name)
            # Start new monitoring thread
            Thread(target=monitor_ip, args=(new_ip,), daemon=True).start()
            selected_ip = None
            canvas.configure(scrollregion=canvas.bbox("all"))
            print(f"Edit complete, closing dialog")  # Debug
            dialog.destroy()

        tk.Button(dialog, text="Submit", bg=THEMES[current_theme]["button_bg"], fg=THEMES[current_theme]["button_fg"],
                  command=submit).pack(pady=5)
    except Exception as e:
        print(f"Error editing IP: {e}")


def remove_ip():
    """Remove the selected IP."""
    global selected_ip
    if not selected_ip:
        print("Remove IP: No IP selected")  # Debug
        messagebox.showerror("Error", "Select an IP to remove")
        return
    try:
        print(f"Removing IP: {selected_ip}")  # Debug
        ip = selected_ip
        # Remove from dictionaries
        status_labels.pop(ip, None)
        response_time_labels.pop(ip, None)
        names.pop(ip, None)
        # Destroy the row
        ip_labels[ip].master.destroy()
        ip_labels.pop(ip, None)
        selected_ip = None
        canvas.configure(scrollregion=canvas.bbox("all"))
    except Exception as e:
        print(f"Error removing IP: {e}")


def save_ips():
    """Save the current IP list to file."""
    try:
        ip_name_pairs = [(child.winfo_children()[0]["text"], child.winfo_children()[1]["text"]) for child in
                         scrollable_frame.winfo_children()]
        save_ip_list(ip_name_pairs)
        messagebox.showinfo("Success", "IP list saved")
    except Exception as e:
        print(f"Error saving IPs: {e}")


def toggle_popups():
    """Toggle popups and update button text."""
    global popups_enabled
    popups_enabled = not popups_enabled
    popup_button.config(text="Disable Popups" if popups_enabled else "Enable Popups")


def on_closing():
    """Handle window close event."""
    global running
    running = False
    root.destroy()
    sys.exit()


if __name__ == "__main__":
    create_gui()