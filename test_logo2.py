from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()

def print_banner() -> None:
    """Cetak banner Antigravity-style dengan logo headphone."""
    console.clear()
    
    # ASCII Headphone
    headphone_art = [
        "      .--------.      ",
        "    /`          `\\    ",
        "   /   .------.   \\   ",
        "  |   /        \\   |  ",
        "  |  |          |  |  ",
        " [___]          [___] "
    ]
    
    # Antigravity/Gemini gradient colors
    gradient = ["#4285F4", "#5C6BC0", "#7E57C2", "#AB47BC", "#D81B60", "#EC407A"]
    
    banner = Text()
    banner.append("\n")
    
    for i, line in enumerate(headphone_art):
        color = gradient[i % len(gradient)]
        banner.append(line + "\n", style=f"bold {color}")
        
    banner.append("\n")
    banner.append("Music Mix Playlist Downloader\n", style="bold white")
    banner.append("High-Fidelity Audio Engine", style="dim white")
    
    banner.justify = "center"
    
    # Antigravity style usually has a clean border
    console.print(
        Panel(
            banner,
            box=box.ROUNDED,
            border_style="#5C6BC0",
            padding=(1, 4),
            title="[bold white]MMPD CLI[/bold white]",
            title_align="center",
            subtitle="[dim]Powered by NanoMindExplorer[/dim]",
            subtitle_align="center",
        )
    )
    console.print()

print_banner()
