import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import json
import psutil
import base64
from io import BytesIO
from PIL import Image, ImageTk
import platform

# Valid base64-encoded 16x16 PNG icons (simple colored squares)
CHECKMARK_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAHklEQVR42mNgGAWjYBSMglEwCkZB"
    "KAiFAgC7vLy8nQA4QAvo6m4QhwAAAABJRU5ErkJggg=="
)  # Green square
TRASH_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAH0lEQVR42mNgGAWjYBSMglEwCkZB"
    "KBgFo2AUjIJRMAoGAYcAc0gbygAAAABJRU5ErkJggg=="
)  # Red square
REFRESH_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAHklEQVR42mNgGAWjYBSMglEwCkZB"
    "KAiFAgC7vLy8nQA4QAvo6m4QhwAAAABJRU5ErkJggg=="
)  # Blue square
APP_PLACEHOLDER_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAIElEQVR42mNgGAWjYBSMglEwCkZB"
    "KBgFo2AUjIJRMAoGAe0Ac0gb8AAAAABJRU5ErkJggg=="
)  # Gray square

class VPNQoSManager:
    def __init__(self, root):
        self.root = root
        self.root.title("VPN QoS Manager")
        self.root.geometry("600x400")
        
        # Detect platform
        self.is_windows = platform.system() == "Windows"
        
        # Priority apps and their default priority levels
        self.priority_apps = {
            "zoom.exe": "Ultra High",
            "discord.exe": "Ultra High",
            "valorant.exe": "Ultra High",
            "steam.exe": "Low"
        }
        
        # DSCP mapping
        self.priority_to_dscp = {
            "Ultra High": 46,
            "High": 34,
            "Medium": 28,
            "Low": 10
        }
        
        # Load settings
        self.settings_file = "settings.json"
        self.settings = self.load_settings()
        
        # Configure ttk style for dark theme
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background="#2e2e2e")
        style.configure("TFrame", background="#2e2e2e")
        style.configure("TLabel", background="#2e2e2e", foreground="#ffffff")
        style.configure("TButton", background="#4a4a4a", foreground="#ffffff")
        style.configure("TCombobox", fieldbackground="#4a4a4a", foreground="#ffffff")
        
        # Load icons
        self.icons = {}
        self.load_icons()
        
        # Create tabbed interface
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.qos_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.qos_tab, text="QoS Management")
        self.notebook.add(self.settings_tab, text="Settings")
        
        # Initialize tabs
        self.setup_qos_tab()
        self.setup_settings_tab()
        
    def load_icons(self):
        # Load base64-encoded icons
        for name, b64_data in [
            ("checkmark", CHECKMARK_BASE64),
            ("trash", TRASH_BASE64),
            ("refresh", REFRESH_BASE64),
            ("app", APP_PLACEHOLDER_BASE64)
        ]:
            try:
                img_data = base64.b64decode(b64_data)
                img = Image.open(BytesIO(img_data))
                self.icons[name] = ImageTk.PhotoImage(img)
            except Exception as e:
                print(f"Error loading icon {name}: {e}")
                # Fallback to empty image
                self.icons[name] = ImageTk.PhotoImage(Image.new("RGB", (16, 16), color="gray"))
        
    def load_settings(self):
        try:
            with open(self.settings_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"interface": "Ethernet"}
        
    def save_settings(self):
        with open(self.settings_file, "w") as f:
            json.dump(self.settings, f, indent=2)
        messagebox.showinfo("Success", "Settings saved.")
        
    def setup_qos_tab(self):
        ttk.Label(self.qos_tab, text="Manage QoS Policies", font=("Arial", 16)).pack(pady=10)
        
        # Frame for app list
        app_frame = ttk.Frame(self.qos_tab)
        app_frame.pack(fill="x", padx=10)
        
        # Priority options
        priority_options = ["Ultra High", "High", "Medium", "Low"]
        
        for app in self.priority_apps:
            frame = ttk.Frame(app_frame)
            frame.pack(fill="x", pady=5)
            
            # App icon
            ttk.Label(frame, image=self.icons["app"]).pack(side="left", padx=5)
            
            # App name
            ttk.Label(frame, text=app, width=20).pack(side="left")
            
            # Priority dropdown
            priority_var = tk.StringVar(value=self.priority_apps[app])
            priority_combo = ttk.Combobox(frame, textvariable=priority_var, values=priority_options, width=12)
            priority_combo.pack(side="left", padx=5)
            
            # Buttons with icons
            ttk.Button(frame, text="Apply", image=self.icons["checkmark"], compound="left",
                       command=lambda a=app, v=priority_var: self.apply_qos(a, v)).pack(side="left", padx=5)
            ttk.Button(frame, text="Remove", image=self.icons["trash"], compound="left",
                       command=lambda a=app: self.remove_qos(a)).pack(side="left", padx=5)
        
        ttk.Button(self.qos_tab, text="Clear All Policies", image=self.icons["trash"], compound="left",
                   command=self.clear_all_policies).pack(pady=10)
        
        self.qos_status = ttk.Label(self.qos_tab, text="")
        self.qos_status.pack(pady=5)
        
    def apply_qos(self, app, priority_var):
        if not self.is_windows:
            self.qos_status.config(text="QoS management not supported on macOS")
            messagebox.showerror("Error", "QoS management requires Windows with PowerShell")
            return
            
        try:
            priority = priority_var.get()
            dscp = self.priority_to_dscp[priority]
            # Find executable path using psutil
            exe_path = None
            for proc in psutil.process_iter(['name', 'exe']):
                if proc.info['name'].lower() == app:
                    exe_path = proc.info['exe']
                    break
            if not exe_path:
                raise Exception(f"{app} not found running")
                
            subprocess.run([
                "powershell",
                f"New-NetQosPolicy -Name Auto_{app} "
                f"-AppPathNameMatchCondition '{exe_path}' "
                f"-IPProtocolMatchCondition Both "
                f"-DSCPAction {dscp}"
            ], shell=True, check=True)
            
            self.priority_apps[app] = priority
            self.qos_status.config(text=f"Policy applied to {app} ({priority})")
        except Exception as e:
            self.qos_status.config(text=f"Error: {str(e)}")
            messagebox.showerror("Error", str(e))
            
    def remove_qos(self, app):
        if not self.is_windows:
            self.qos_status.config(text="QoS management not supported on macOS")
            messagebox.showerror("Error", "QoS management requires Windows with PowerShell")
            return
            
        try:
            subprocess.run([
                "powershell",
                f"Remove-NetQosPolicy -Name Auto_{app} -Confirm:$false"
            ], shell=True, check=True)
            self.qos_status.config(text=f"Policy removed from {app}")
        except Exception as e:
            self.qos_status.config(text=f"Error: {str(e)}")
            messagebox.showerror("Error", str(e))
            
    def clear_all_policies(self):
        if not self.is_windows:
            self.qos_status.config(text="QoS management not supported on macOS")
            messagebox.showerror("Error", "QoS management requires Windows with PowerShell")
            return
            
        try:
            for app in self.priority_apps:
                subprocess.run([
                    "powershell",
                    f"Remove-NetQosPolicy -Name Auto_{app} -Confirm:$false"
                ], shell=True)
            self.qos_status.config(text="All policies cleared")
        except Exception as e:
            self.qos_status.config(text=f"Error: {str(e)}")
            messagebox.showerror("Error", str(e))
            
    def setup_settings_tab(self):
        ttk.Label(self.settings_tab, text="Settings", font=("Arial", 16)).pack(pady=10)
        
        # Interface selection
        interface_frame = ttk.Frame(self.settings_tab)
        interface_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(interface_frame, text="Network Interface:").pack(side="left")
        self.interface_var = tk.StringVar(value=self.settings["interface"])
        self.interface_combo = ttk.Combobox(interface_frame, textvariable=self.interface_var, width=30)
        self.interface_combo.pack(side="left", padx=5)
        ttk.Button(interface_frame, text="Refresh", image=self.icons["refresh"], compound="left",
                   command=self.refresh_interfaces).pack(side="left", padx=5)
        
        # Save button
        ttk.Button(self.settings_tab, text="Save Settings", command=self.save_settings_action).pack(pady=10)
        
        self.settings_status = ttk.Label(self.settings_tab, text="")
        self.settings_status.pack(pady=5)
        
        # Populate interfaces
        self.refresh_interfaces()
        
    def refresh_interfaces(self):
        if not self.is_windows:
            self.interface_combo["values"] = ["Not supported on macOS"]
            self.interface_var.set("Not supported on macOS")
            self.settings_status.config(text="Interface detection not supported on macOS")
            return
            
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Select-Object -ExpandProperty Name"],
                capture_output=True,
                text=True,
                check=True
            )
            interfaces = result.stdout.strip().split("\n")
            self.interface_combo["values"] = interfaces
            if self.interface_var.get() not in interfaces:
                self.interface_var.set(interfaces[0] if interfaces else "Ethernet")
        except Exception as e:
            self.settings_status.config(text=f"Error: {str(e)}")
            messagebox.showerror("Error", str(e))
            
    def save_settings_action(self):
        try:
            self.settings["interface"] = self.interface_var.get()
            self.save_settings()
        except Exception as e:
            self.settings_status.config(text=f"Error: {str(e)}")
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = VPNQoSManager(root)
    root.mainloop()