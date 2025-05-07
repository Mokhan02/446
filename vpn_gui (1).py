import tkinter as tk
from tkinter import messagebox
import subprocess
import os

# List of apps and their default DSCP values
priority_apps = {
    "zoom.exe": 46,
    "discord.exe": 46,
    "valorant.exe": 46,
    "steam.exe": 10
}

# Apply QoS policy
def apply_qos(app):
    dscp = priority_apps[app]
    try:
        # This gets the full path of the running process (if needed, can be improved)
        exe_path = f"C:\\Program Files\\{app.split('.')[0].capitalize()}\\{app}"  # change as needed
        subprocess.run([
            "powershell",
            f"New-NetQosPolicy -Name Auto_{app} "
            f"-AppPathNameMatchCondition '{exe_path}' "
            f"-IPProtocolMatchCondition Both "
            f"-DSCPAction {dscp}"
        ], shell=True)
        messagebox.showinfo("Success", f"QoS policy applied to {app} (DSCP {dscp})")
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