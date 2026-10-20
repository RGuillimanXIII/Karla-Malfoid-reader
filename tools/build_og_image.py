"""Build assets/og-image.png, the 1200x630 link-preview card. Run: python3 tools/build_og_image.py"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = '/usr/share/fonts/truetype/sand-box/google/'
W, H = 1200, 630
BG, ACCENT, SILVER, MUTED = (15, 21, 18), (95, 191, 138), (201, 209, 214), (159, 177, 165)

def font(path, size, wght=None):
    f = ImageFont.truetype(G + path, size)
    if wght is not None:
        try:
            f.set_variation_by_axes([wght] if 'Cormorant' in path else [14 if size < 40 else 32, wght])
        except Exception:
            pass
    return f

img = Image.new('RGB', (W, H), BG)
# soft green glow
glow = Image.new('RGB', (W, H), BG)
gd = ImageDraw.Draw(glow)
gd.ellipse((250, 40, 950, 590), fill=(30, 58, 44))
glow = glow.filter(ImageFilter.GaussianBlur(140))
img = Image.blend(img, glow, 0.9)
d = ImageDraw.Draw(img)

# double frame
d.rectangle((36, 36, W - 37, H - 37), outline=(43, 58, 49), width=2)
d.rectangle((48, 48, W - 49, H - 49), outline=(38, 51, 43), width=1)

def center(text, y, f, fill):
    w = d.textlength(text, font=f)
    d.text(((W - w) / 2, y), text, font=f, fill=fill)

kicker = font('Inter/Inter-VariableFont_opsz,wght.ttf', 26, 500)
title = font('Cormorant Garamond/CormorantGaramond-VariableFont_wght.ttf', 190, 600)
sub = font('Cormorant Garamond/CormorantGaramond-Italic-VariableFont_wght.ttf', 50, 500)
small = font('Inter/Inter-VariableFont_opsz,wght.ttf', 24, 400)

center('A N   U N O F F I C I A L   R E A D E R', 120, kicker, ACCENT)
center('Malfoid', 165, title, SILVER)
# ornament
cy = 400
d.line((W / 2 - 170, cy, W / 2 - 22, cy), fill=ACCENT, width=2)
d.line((W / 2 + 22, cy, W / 2 + 170, cy), fill=ACCENT, width=2)
d.polygon([(W / 2, cy - 9), (W / 2 + 9, cy), (W / 2, cy + 9), (W / 2 - 9, cy)], fill=ACCENT)
center('Short stories by @KarlaBoban97, in story order', 425, sub, (233, 239, 233))
center('rguillimanxiii.github.io/Karla-Malfoid-reader', 528, small, MUTED)

out = os.path.join(ROOT, 'assets', 'og-image.png')
img.save(out, optimize=True)
print(out, os.path.getsize(out))
