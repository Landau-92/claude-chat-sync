# Draws the app icon (1024x1024 PNG): a blue-to-violet rounded square with two opposite arrows.
# Usage: python3 make_icon.py out.png   (needs Pillow)
import sys

from PIL import Image, ImageDraw

S = 1024
TOP, BOTTOM = (0x3B, 0x82, 0xF6), (0x8B, 0x5C, 0xF6)

grad = Image.new("RGB", (S, S))
px = grad.load()
for y in range(S):
    for x in range(S):
        t = (x + y) / (2 * (S - 1))
        px[x, y] = tuple(round(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3))

# Rounded square with the standard macOS icon margin
mask = Image.new("L", (S, S), 0)
m = 100
ImageDraw.Draw(mask).rounded_rectangle([m, m, S - m, S - m], radius=185, fill=255)
icon = Image.new("RGBA", (S, S), (0, 0, 0, 0))
icon.paste(grad, (0, 0), mask)

d = ImageDraw.Draw(icon)
W = (255, 255, 255, 255)


def arrow(y, right):
    x0, x1, h, head = 300, 724, 44, 120
    if right:
        d.rounded_rectangle([x0, y - h // 2, x1 - head + 20, y + h // 2], radius=h // 2, fill=W)
        d.polygon([(x1, y), (x1 - head, y - head * 0.8), (x1 - head, y + head * 0.8)], fill=W)
    else:
        d.rounded_rectangle([x0 + head - 20, y - h // 2, x1, y + h // 2], radius=h // 2, fill=W)
        d.polygon([(x0, y), (x0 + head, y - head * 0.8), (x0 + head, y + head * 0.8)], fill=W)


arrow(420, right=True)
arrow(604, right=False)
icon.save(sys.argv[1])
