"""Render one layer split by (color,width) style. usage: style_view.py PAGE LAYER out.png"""
import sys, numpy as np, cv2, os, collections
sys.path.insert(0, os.path.dirname(__file__))
from vecutil import *
pno = int(sys.argv[1]); L = sys.argv[2]; outp = os.path.join(OUT, sys.argv[3])
clip = (260, 250, 1300, 1020); ppt = 1.6
d = [it for it in get_drawings(pno) if it.get("layer") == L]
groups = collections.defaultdict(list)
for it in d:
    groups[(tuple(round(x, 2) for x in (it.get("color") or ())), round(it.get("width") or 0, 2), it.get("fill") is not None)].append(it)
x0, y0, x1, y1 = clip
img = np.full((int((y1 - y0) * ppt) + 1, int((x1 - x0) * ppt) + 1, 3), 255, np.uint8)
pal = [(0, 0, 255), (0, 160, 0), (255, 0, 0), (0, 140, 255), (200, 0, 200), (160, 160, 0)]
for i, (k, its) in enumerate(sorted(groups.items(), key=lambda kv: -len(kv[1]))):
    m = raster(its, None, clip, ppt)
    img[m > 0] = pal[i % 6]
    cv2.putText(img, f"{k} n={len(its)}", (10, 30 + 30 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.8, pal[i % 6], 2)
imwrite(outp, img)
