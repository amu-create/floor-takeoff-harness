"""render.py SRC OUT PAGE DPI [x0 y0 x1 y1 as fractions of page]"""
import sys, fitz
src, out, page, dpi = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
doc = fitz.open(src)
p = doc[page - 1]
r = p.rect
clip = None
if len(sys.argv) >= 9:
    fx0, fy0, fx1, fy1 = map(float, sys.argv[5:9])
    clip = fitz.Rect(r.x0 + fx0 * r.width, r.y0 + fy0 * r.height, r.x0 + fx1 * r.width, r.y0 + fy1 * r.height)
pix = p.get_pixmap(dpi=dpi, clip=clip, alpha=False)
if out.lower().endswith(".jpg"):
    pix.save(out, jpg_quality=85)
else:
    pix.save(out)
print(out, pix.width, pix.height)
