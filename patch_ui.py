import re

art = [
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

new_art = '    # ASCII Headphone (Generated with Artem)\n    headphone_art = [\n'
for line in art:
    escaped = line.replace('\\', '\\\\')
    new_art += f'        "{escaped}",\n'
new_art = new_art.rstrip(',\n') + '\n    ]'

with open("mmpd/ui.py", "r") as f:
    text = f.read()

text = re.sub(
    r'    # ASCII Headphone.*?headphone_art = \[\n.*?\]',
    new_art,
    text,
    flags=re.DOTALL
)

with open("mmpd/ui.py", "w") as f:
    f.write(text)
print("patched")
