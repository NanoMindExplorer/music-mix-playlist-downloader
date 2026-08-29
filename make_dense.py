from PIL import Image

img_path = 'png-clipart-logo-headphones-graphic-design-product-design-business-logo-design-ideas-text-logo.png'
img = Image.open(img_path)

if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
    alpha = img.convert('RGBA').split()[-1]
    bg = Image.new("RGBA", img.size, (255,255,255,255))
    bg.paste(img, mask=alpha)
    img = bg.convert('L')
else:
    img = img.convert('L')

width = 44
w, h = img.size
new_h = int((h / w) * width)
if new_h % 2 != 0:
    new_h += 1

img = img.resize((width, new_h), Image.Resampling.LANCZOS)
pixels = img.load()

# Threshold
threshold = 200

lines = []
for y in range(0, new_h, 2):
    row_str = ""
    for x in range(width):
        top_dark = pixels[x, y] < threshold
        bottom_dark = pixels[x, y+1] < threshold if y+1 < new_h else False
        
        if top_dark and bottom_dark:
            row_str += "█"
        elif top_dark and not bottom_dark:
            row_str += "▀"
        elif not top_dark and bottom_dark:
            row_str += "▄"
        else:
            row_str += " "
    if row_str.strip(): # only append non-empty lines to trim height
        lines.append(row_str)

for line in lines:
    print(line)

with open("dense_logo.txt", "w") as f:
    f.write("\n".join(lines))
