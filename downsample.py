import sys

def downsample(text, factor_x, factor_y):
    lines = [l.rstrip('\n') for l in text.split('\n') if l.strip()]
    if not lines: return []
    
    # Pad lines to max width
    max_w = max(len(l) for l in lines)
    lines = [l.ljust(max_w) for l in lines]
    
    new_h = len(lines) // factor_y
    new_w = max_w // factor_x
    
    out = []
    # Simplified character map for cleaner look
    char_weight = {' ':0, '.':1, ',':2, '-':3, '+':4, ':':5, ';':6, '=':7, '*':8, '%':9, '#':10, '@':11}
    weight_char = sorted(char_weight.items(), key=lambda x: x[1])
    
    for y in range(new_h):
        row = ""
        for x in range(new_w):
            total = 0
            count = 0
            for dy in range(factor_y):
                for dx in range(factor_x):
                    orig_y = y * factor_y + dy
                    orig_x = x * factor_x + dx
                    if orig_y < len(lines) and orig_x < len(lines[orig_y]):
                        # Map original chars to weights
                        c = lines[orig_y][orig_x]
                        w = 0
                        if c in '@S#%?*': w = 11
                        elif c in '+:;': w = 6
                        elif c in '.,': w = 2
                        else: w = 0
                        total += w
                        count += 1
            avg = total / count if count else 0
            
            # Map back
            best_char = ' '
            best_diff = 999
            for char, weight in weight_char:
                if abs(weight - avg) < best_diff:
                    best_diff = abs(weight - avg)
                    best_char = char
            row += best_char
        out.append(row.rstrip()) # strip trailing spaces
    return out

with open('user_logo.txt') as f:
    text = f.read()

# Try factor x=4, y=3
out = downsample(text, 4, 3)
for l in out:
    print(l)
