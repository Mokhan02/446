import subprocess

apps = ["zoom.exe", "discord.exe", "valorant.exe", "steam.exe"]

for app in apps:
    name = f"Auto_{app}"
    print(f"Removing QoS policy: {name}")
    subprocess.run([
        "powershell",
        f"Remove-NetQosPolicy -Name {name} -Confirm:$false"
    ], shell=True)