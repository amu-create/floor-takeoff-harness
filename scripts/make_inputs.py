"""도면 PDF -> 실험 입력 이미지 묶음 생성 (overview / 2x2 타일)"""
import sys, os, fitz
src, out = sys.argv[1], sys.argv[2]
doc = fitz.open(src)
PAGES = {  # page: (name, plan region x0,y0,x1,y1 fractions)
    9:  ("B1_material", (0.10, 0.10, 0.85, 0.75)),
    21: ("2F_material", (0.13, 0.10, 0.79, 0.78)),
    41: ("3F_material", (0.13, 0.10, 0.79, 0.78)),
    10: ("B1_dimension", (0.10, 0.10, 0.85, 0.75)),
    22: ("2F_dimension", (0.13, 0.10, 0.79, 0.78)),
    42: ("3F_dimension", (0.13, 0.10, 0.79, 0.78)),
}
os.makedirs(os.path.join(out, "overview"), exist_ok=True)
os.makedirs(os.path.join(out, "tiles"), exist_ok=True)

def save(p, clip, dpi, path):
    pix = p.get_pixmap(dpi=dpi, clip=clip, alpha=False)
    pix.save(path, jpg_quality=88)
    return pix.width, pix.height

def frac(p, x0, y0, x1, y1):
    r = p.rect
    return fitz.Rect(r.width * x0, r.height * y0, r.width * x1, r.height * y1)

# material list (left half)
p = doc[4]
print("material_list", save(p, frac(p, 0.06, 0.11, 0.46, 0.88), 130, os.path.join(out, "overview", "material_list.jpg")))
for pg, (name, (x0, y0, x1, y1)) in PAGES.items():
    p = doc[pg - 1]
    print(name, "overview", save(p, p.rect, 72, os.path.join(out, "overview", f"{name}.jpg")))
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    ov = 0.02
    tiles = {"NW": (x0, y0, mx + ov, my + ov), "NE": (mx - ov, y0, x1, my + ov),
             "SW": (x0, my - ov, mx + ov, y1), "SE": (mx - ov, my - ov, x1, y1)}
    for t, (a, b, c, d) in tiles.items():
        print(name, t, save(p, frac(p, a, b, c, d), 165, os.path.join(out, "tiles", f"{name}_{t}.jpg")))
