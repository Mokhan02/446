import subprocess

apps = ["zoom.exe", "discord.exe", "valorant.exe", "steam.exe"]

for app in apps:
    app_base = app.split(".")[0].lower()  # Removes .exe
    name = f"Auto_{app_base}"
    print(f"Removing QoS policy: {name}")
    subprocess.run([
        "powershell",
        "-Command",
        f"try {{ Remove-NetQosPolicy -Name '{name}' -Confirm:$false }} catch {{ }}"
    ], shell=True)
