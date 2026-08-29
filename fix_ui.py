import re

with open("mmpd/ui.py", "r") as f:
    text = f.read()

new_func = '''def print_banner() -> None:
    """Cetak banner ala Antigravity CLI dengan logo headphone."""
    console.clear()
    
    # ASCII Headphone Typography Logo
    headphone_art = [
        r"       .-----------------------------------------.       ",
        r"     /                                             \     ",
        r"    /      __  ___   __  ___   ____     ____        \    ",
        r"   |      /  |/  /  /  |/  /  / __ \   / __ \        |   ",
        r"   |     / /|_/ /  / /|_/ /  / /_/ /  / / / /        |   ",
        r"   |    / /  / /  / /  / /  / ____/  / /_/ /         |   ",
        r"  ___  /_/  /_/  /_/  /_/  /_/      /_____/         ___  ",
        r" /   \                                             /   \ ",
        r"|  O  |          [==|==|==|==|==|==|==]           |  O  |",
        r"|     |          [  |  |  |  |  |  |  ]           |     |",
        r" \___/                                             \___/ "
    ]
    
    # Antigravity/Gemini gradient colors (Blue to Magenta)
    gradient = ["#4285F4", "#5C6BC0", "#7E57C2", "#AB47BC", "#D81B60", "#EC407A"]
    
    banner = Text()
    banner.append("\\n")
    for i, line in enumerate(headphone_art):
        color = gradient[i % len(gradient)]
        banner.append(line + "\\n", style=f"bold {color}")
        
    banner.append("\\n")
    banner.append("Music Mix Playlist Downloader\\n", style="bold white")
    banner.append("High-Fidelity Audio Engine\\n\\n", style="dim white")
    banner.append("Artfully Crafted by ", style="dim white")
    banner.append("NanoMindExplorer", style="bold #4285F4")
    
    banner.justify = "center"
    
    console.print(
        Panel(
            banner,
            box=box.ROUNDED,
            border_style="#5C6BC0",
        )
    )'''

# Replace the whole function
text = re.sub(
    r'def print_banner\(\) -> None:.*?border_style="#5C6BC0",\n        \)\n    \)',
    new_func,
    text,
    flags=re.DOTALL
)

with open("mmpd/ui.py", "w") as f:
    f.write(text)
print("fixed")
