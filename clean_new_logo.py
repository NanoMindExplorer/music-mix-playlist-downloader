with open('new_logo.txt') as f:
    text = f.read()

# Replace noise with spaces
text = text.replace('.', ' ').replace(',', ' ').replace('+', ' ').replace(':', ' ').replace(';', ' ')

def downsample(text, factor_x, factor_y):
    lines = [l.rstrip('\n') for l in text.split('\n') if l.strip()]
    if not lines: return []
    
    max_w = max(len(l) for l in lines)
    lines = [l.ljust(max_w) for l in lines]
    
    new_h = len(lines) // factor_y
    new_w = max_w // factor_x
    
    out = []
    
    for y in range(new_h):
        row = ""
        for x in range(new_w):
            total = 0
            for dy in range(factor_y):
                for dx in range(factor_x):
                    orig_y = y * factor_y + dy
                    orig_x = x * factor_x + dx
                    if orig_y < len(lines) and orig_x < len(lines[orig_y]):
                        c = lines[orig_y][orig_x]
                        if c in '@S#%?*':
                            total += 1
            if total > (factor_x * factor_y) * 0.1:
                row += '@'
            else:
                row += ' '
        out.append(row.rstrip())
    return out

print("=== 6x4 ===")
for l in downsample(text, 6, 4): print(l)

print("=== 5x4 ===")
for l in downsample(text, 5, 4): print(l)
