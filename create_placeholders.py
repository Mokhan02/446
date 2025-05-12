from PIL import Image
import os

# Colors for each app/button
colors = {
    "zoom": "blue",
    "discord": "purple",
    "skype": "cyan",
    "teams": "darkblue",
    "valorant": "red",
    "steam": "black",
    "leagueoflegends": "gold",
    "csgo": "orange",
    "obs": "green",
    "twitch": "purple",
    "checkmark": "green",
    "trash": "red",
    "refresh": "blue"
}

# Create icons directory
os.makedirs("icons", exist_ok=True)

# Generate 16x16 colored squares
for name, color in colors.items():
    img = Image.new("RGB", (16, 16), color=color)
    img.save(f"icons/{name}.png")