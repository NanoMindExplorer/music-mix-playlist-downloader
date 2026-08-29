from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

art = [
    r"       .-----------------------------------------.       ",
    r"     /                                             \     ",
    r"    /      __  ___   __  ___   ____     ____        \    ",
    r"   |      /  |/  /  /  |/  /  / __ \   / __ \        |   ",
    r"   |     / /|_/ /  / /|_/ /  / /_/ /  / / / /        |   ",
    r"   |    / /  / /  / /  / /  / ____/  / /_/ /         |   ",
    r"  ___  /_/  /_/  /_/  /_/  /_/      /_____/         ___  ",
    r" /   \                                             /   \ ",
    r"|  O  |          |||||||||||||||||||||||          |  O  |",
    r"|     |          || ıllılı.ıllılı.ıllılı ||          |     |",
    r" \___/                                             \___/ "
]

gradient = ["#4285F4", "#5C6BC0", "#7E57C2", "#AB47BC", "#D81B60", "#EC407A"]

console = Console()
banner = Text("\n")
for i, line in enumerate(art):
    banner.append(line + "\n", style=f"bold {gradient[i % len(gradient)]}")
    
banner.justify = "center"
console.print(Panel(banner, box=box.ROUNDED, border_style="#5C6BC0"))
