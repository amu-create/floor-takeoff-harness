"""Inspect COL-layer thin black lines by length; render long ones to see if they're finish boundaries."""
import sys, os, numpy as np, cv2, collections
sys.path.insert(0, os.path.dirname(__file__))
from vecutil import *
pno = int(sys.argv[1]); thr = float(sys.argv[2]); L = sys.argv[3] if len(sys.argv) > 3 else "COL"
d = get_drawings(pno)
clip = (240, 240, 1320, 1020); ppt = 1.5
x0, y0, x1, y1 = clip
img = np.full((int((y1 - y0) * ppt) + 1, int((x1 - x0) * ppt) + 1, 3), 255, np.uint8)
# faint background: all walls
bg = raster(d, {"wall", "COR", "CONW", "WID", "wal"}, clip, ppt)
img[bg > 0] = (190, 190, 190)
hist = collections.Counter()
f = open(os.path.join(OUT, f"col_long_{pno}_{L}.txt"), "w", encoding="utf-8")
for it in d:
    if it.get("layer") != L:
        continue
    w = round(it.get("width") or 0, 2); c = tuple(round(v, 2) for v in (it.get("color") or ()))
    for x in it["items"]:
        if x[0] != "l":
            continue
        ln = abs(x[1] - x[2])
        hist[(w, c, int(ln // 10) * 10)] += 1
        if ln >= thr and c == (0.0, 0.0, 0.0):
            p = np.round((np.array([[x[1].x, x[1].y], [x[2].x, x[2].y]]) - [x0, y0]) * ppt).astype(int)
            cv2.line(img, tuple(p[0]), tuple(p[1]), (0, 0, 255), 2)
            f.write(f"{w} {c} len={ln:.1f} ({x[1].x:.1f},{x[1].y:.1f})-({x[2].x:.1f},{x[2].y:.1f}) nitems={len(it['items'])} seq={it.get('seqno')}\n")
for k, v in sorted(hist.items()):
    f.write(f"H {k} {v}\n")
f.close()
imwrite(os.path.join(OUT, f"col_long_{pno}_{L}.png"), img)
