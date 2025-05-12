import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import json
import psutil
from PIL import Image, ImageTk
import platform

class VPNQoSManager:
    def __init__(self, root):
        self.root = root
        self.root.title("VPN QoS Manager")
        self.root.geometry("600x600")
        
        # Detect platform
        self.is_windows = platform.system() == "Windows"
        
        # Priority apps and their default priority levels
        self.priority_apps = {
            "zoom.exe": "Ultra High",
            "discord.exe": "Ultra High",
            "teams.exe": "Ultra High",
            "valorant.exe": "High",
            "steam.exe": "High",
            "leagueoflegends.exe": "High",
            "csgo.exe": "High",
            "roblox.exe": "High",
            "obs.exe": "Medium",
            "twitch.exe": "Medium",
            "netflix.exe": "Medium",
            "spotify.exe": "Medium"  # Added Spotify
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
        
        # Configure ttk style for light theme
        style = ttk.Style()
        style.theme_use("clam")
        
        # Define custom styles
        style.configure("Light.TNotebook", background="#F5F5F5")
        style.configure("Light.TFrame", background="#F5F5F5")
        style.configure("Light.TLabel", background="#F5F5F5", foreground="#333333", font=("Arial", 12))
        style.configure("Light.TButton", background="#E0E0E0", foreground="#333333", borderwidth=1, font=("Arial", 10))
        style.map("Light.TButton", background=[("active", "#D0D0D0")])
        style.configure("Light.TCombobox", fieldbackground="#FFFFFF", foreground="#333333", font=("Arial", 10))
        style.map("Light.TCombobox", fieldbackground=[("readonly", "#FFFFFF")])
        
        # Load icons
        self.icons = {}
        self.load_icons()
        
        # Create tabbed interface
        self.notebook = ttk.Notebook(root, style="Light.TNotebook")
        self.notebook.pack(fill="both", expand=True, padx=15, pady=15)
        
        self.qos_tab = ttk.Frame(self.notebook, style="Light.TFrame")
        self.settings_tab = ttk.Frame(self.notebook, style="Light.TFrame")
        
        self.notebook.add(self.qos_tab, text="QoS Management")
        self.notebook.add(self.settings_tab, text="Settings")
        
        # Set root background
        self.root.configure(bg="#F5F5F5")
        
        # Initialize tabs
        self.setup_qos_tab()
        self.setup_settings_tab()
        
    def load_icons(self):
        # Icon directory
        icon_dir = "icons"
        os.makedirs(icon_dir, exist_ok=True)
        
        # Default fallback image
        self.icons["default"] = ImageTk.PhotoImage(Image.new("RGB", (16, 16), color="gray"))
        
        # Load app-specific icons
        for app in self.priority_apps:
            app_name = app.split(".")[0]
            icon_path = os.path.join(icon_dir, f"{app_name}.png")
            try:
                img = Image.open(icon_path).resize((16, 16), Image.Resampling.LANCZOS)
                self.icons[app_name] = ImageTk.PhotoImage(img)
            except Exception as e:
                print(f"Error loading icon for {app_name}: {e}")
                self.icons[app_name] = self.icons["default"]
        
        # Load button icons
        button_icons = {
            "checkmark": "checkmark.png",  # Green checkmark
            "trash": "trash.png",         # Red trash can
            "refresh": "refresh.png"      # Blue refresh arrow
        }
        for name, filename in button_icons.items():
            icon_path = os.path.join(icon_dir, filename)
            try:
                img = Image.open(icon_path).resize((16, 16), Image.Resampling.LANCZOS)
                self.icons[name] = ImageTk.PhotoImage(img)
            except Exception as e:
                print(f"Error loading button icon {name}: {e}")
                self.icons[name] = self.icons["default"]
        
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
        ttk.Label(self.qos_tab, text="Manage QoS Policies", style="Light.TLabel", font=("Arial", 18, "bold")).pack(pady=(10, 20))
        
        # Frame for app list with border
        app_container = ttk.Frame(self.qos_tab, style="Light.TFrame", relief="solid", borderwidth=1, padding=10)
        app_container.pack(fill="both", expand=True, padx=10)
        
        # Canvas for scrollable app list
        canvas = tk.Canvas(app_container, bg="#F5F5F5", highlightthickness=0)
        scrollbar = ttk.Scrollbar(app_container, orient="vertical", command=canvas.yview)
        app_frame = ttk.Frame(canvas, style="Light.TFrame")
        
        app_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.create_window((0, 0), window=app_frame, anchor="nw")
        
        # Priority options
        priority_options = ["Ultra High", "High", "Medium", "Low"]
        
        for app in self.priority_apps:
            frame = ttk.Frame(app_frame, style="Light.TFrame")
            frame.pack(fill="x", pady=5, padx=5)
            
            # App icon
            app_name = app.split(".")[0]
            ttk.Label(frame, image=self.icons[app_name], style="Light.TLabel").pack(side="left", padx=(0, 10))
            
            # App name
            ttk.Label(frame, text=app, width=20, style="Light.TLabel").pack(side="left")
            
            # Priority dropdown
            priority_var = tk.StringVar(value=self.priority_apps[app])
            priority_combo = ttk.Combobox(frame, textvariable=priority_var, values=priority_options, width=12, state="readonly", style="Light.TCombobox")
            priority_combo.pack(side="left", padx=10)
            
            # Buttons with icons
            ttk.Button(frame, text="Apply", image=self.icons["checkmark"], compound="left",
                       command=lambda a=app, v=priority_var: self.apply_qos(a, v), style="Light.TButton").pack(side="left", padx=5)
            ttk.Button(frame, text="Remove", image=self.icons["trash"], compound="left",
                       command=lambda a=app: self.remove_qos(a), style="Light.TButton").pack(side="left", padx=5)
        
        ttk.Button(self.qos_tab, text="Clear All Policies", image=self.icons["trash"], compound="left",
                   command=self.clear_all_policies, style="Light.TButton").pack(pady=15)
        
        self.qos_status = ttk.Label(self.qos_tab, text="", style="Light.TLabel", font=("Arial", 11))
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
        ttk.Label(self.settings_tab, text="Settings", style="Light.TLabel", font=("Arial", 18, "bold")).pack(pady=(10, 20))
        
        # Interface selection frame with border
        interface_frame = ttk.Frame(self.settings_tab, style="Light.TFrame", relief="solid", borderwidth=1, padding=10)
        interface_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(interface_frame, text="Network Interface:", style="Light.TLabel").pack(side="left")
        self.interface_var = tk.StringVar(value=self.settings["interface"])
        self.interface_combo = ttk.Combobox(interface_frame, textvariable=self.interface_var, width=30, state="readonly", style="Light.TCombobox")
        self.interface_combo.pack(side="left", padx=15)
        ttk.Button(interface_frame, text="Refresh", image=self.icons["refresh"], compound="left",
                   command=self.refresh_interfaces, style="Light.TButton").pack(side="left", padx=5)
        
        ttk.Button(self.settings_tab, text="Save Settings", command=self.save_settings_action, style="Light.TButton").pack(pady=15)
        
        self.settings_status = ttk.Label(self.settings_tab, text="", style="Light.TLabel", font=("Arial", 11))
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