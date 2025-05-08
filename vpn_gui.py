import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import psutil  # Make sure to run: pip install psutil

# List of apps and their default DSCP values
priority_apps = {
    "zoom.exe": 46,
    "discord.exe": 46,
    "valorant.exe": 46,
    "steam.exe": 10
}

# Find full path of a running process by name
def find_exe_path_by_name(app_name):
    for proc in psutil.process_iter(['name', 'exe']):
        if proc.info['name'] and proc.info['name'].lower() == app_name.lower():
            return proc.info['exe']
    return None

# Apply QoS policy
def apply_qos(app):
    dscp = priority_apps[app]
    try:
        exe_path = find_exe_path_by_name(app)
        if not exe_path:
            messagebox.showerror("Error", f"Could not find a running process for {app}.\nPlease make sure it's open.")
            return

        subprocess.run([
            "powershell",
            f"New-NetQosPolicy -Name Auto_{app} "
            f"-AppPathNameMatchCondition '{exe_path}' "
            f"-IPProtocolMatchCondition Both "
            f"-DSCPAction {dscp} "
            f"-NetworkProfile All"
        ], shell=True)

        messagebox.showinfo("Success", f"QoS policy applied to {app} at:\n{exe_path}")
    except Exception as e:
        messagebox.showerror("Error", str(e))

# Remove QoS policy
def remove_qos(app):
    try:
        subprocess.run([
            "powershell",
            f"Remove-NetQosPolicy -Name Auto_{app} -Confirm:$false"
        ], shell=True)
        messagebox.showinfo("Success", f"QoS policy removed from {app}")
    except Exception as e:
        messagebox.showerror("Error", str(e))

# Build the GUI
root = tk.Tk()
root.title("VPN Traffic Prioritization")

tk.Label(root, text="Select an app to manage QoS:", font=("Arial", 14)).pack(pady=10)

for app in priority_apps:
    frame = tk.Frame(root)
    frame.pack(pady=5)

    label = tk.Label(frame, text=app, width=15, anchor="w")
    label.pack(side="left")

    apply_btn = tk.Button(frame, text="Apply Priority", command=lambda a=app: apply_qos(a))
    apply_btn.pack(side="left", padx=5)

    remove_btn = tk.Button(frame, text="Remove Policy", command=lambda a=app: remove_qos(a))
    remove_btn.pack(side="left")

root.mainloop()
