import psutil
import subprocess

# List of apps to prioritize and their DSCP values (46 = high priority)
priority_apps = {
    "zoom.exe": 46,
    "discord.exe": 46,
    "valorant.exe": 46,
    "steam.exe": 10  # lower priority
}

already_applied = set()

for proc in psutil.process_iter(['name', 'exe']):
    try:
        name = proc.info['name'].lower()
        path = proc.info['exe']

        if name in priority_apps and name not in already_applied:
            dscp = priority_apps[name]
            print(f"Applying QoS to: {name} with DSCP {dscp}")

            subprocess.run([
                "powershell",
                f"New-NetQosPolicy -Name Auto_{name} "
                f"-AppPathNameMatchCondition '{path}' "
                f"-IPProtocolMatchCondition Both "
                f"-DSCPAction {dscp}"
            ], shell=True)

            already_applied.add(name)

    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        continue
