import tkinter as tk
from tkinter import messagebox
import subprocess
import psutil

# Tier-to-DSCP mapping
tier_to_dscp = {
    "Ultra High": 46,
    "High": 34,
    "Medium": 28,
    "Low": 10
}

# List of apps you want to support
apps = ["zoom.exe", "discord.exe", "valorant.exe", "steam.exe"]

# Track selected tiers for each app
app_tier_selection = {}

# Find full path of a running process by name
def find_exe_path_by_name(app_name):
    for proc in psutil.process_iter(['name', 'exe']):
        if proc.info['name'] and proc.info['name'].lower() == app_name.lower():
            return proc.info['exe']
    return None

# Apply QoS policy
def apply_qos(app):
    selected_tier = app_tier_selection[app].get()
    dscp = tier_to_dscp[selected_tier]

    exe_path = find_exe_path_by_name(app)
    if not exe_path:
        messagebox.showerror("Error", f"Could not find a running process for {app}. Please make sure it's open.")
        return

    try:
        subprocess.run([
            "powershell",
            f"New-NetQosPolicy -Name Auto_{app} "
            f"-AppPathNameMatchCondition '{exe_path}' "
            f"-IPProtocolMatchCondition Both "
            f"-DSCPAction {dscp} "
            f"-NetworkProfile All"
        ], shell=True)

        messagebox.showinfo("Success", f"QoS policy applied to {app}\nTier: {selected_tier} (DSCP {dscp})")
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

tk.Label(root, text="Assign a priority tier to each app:", font=("Arial", 14)).pack(pady=10)

tiers = list(tier_to_dscp.keys())

for app in apps:
    frame = tk.Frame(root)
    frame.pack(pady=5)

    label = tk.Label(frame, text=app, width=15, anchor="w")
    label.pack(side="left")

    selected = tk.StringVar(value="High")
    app_tier_selection[app] = selected

    dropdown = tk.OptionMenu(frame, selected, *tiers)
    dropdown.pack(side="left", padx=5)

    apply_btn = tk.Button(frame, text="Apply Priority", command=lambda a=app: apply_qos(a))
    apply_btn.pack(side="left", padx=5)

    remove_btn = tk.Button(frame, text="Remove Policy", command=lambda a=app: remove_qos(a))
    remove_btn.pack(side="left")

root.mainloop()
