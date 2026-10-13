"""Render each layer of a page in its own color to inspect what it is.
usage: layer_view.py PAGE x0 y0 x1 y1 ppt LAYER1,LAYER2,... out.png"""
import sys, numpy as np, cv2, os
sys.path.insert(0, os.path.dirname(__file__))
from vecutil import *

pno = int(sys.argv[1]); clip = tuple(map(float, sys.argv[2:6])); ppt = float(sys.argv[6])
layers = sys.argv[7].split("|")
outp = os.path.join(OUT, sys.argv[8])
d = get_drawings(pno)
x0, y0, x1, y1 = clip
W, H = int((x1 - x0) * ppt) + 1, int((y1 - y0) * ppt) + 1
img = np.full((H, W, 3), 255, np.uint8)
pal = [(0, 0, 255), (0, 160, 0), (255, 0, 0), (0, 140, 255), (200, 0, 200), (160, 160, 0), (0, 0, 0), (128, 64, 0), (0, 200, 200), (90, 90, 90)]
for i, L in enumerate(layers):
    m = raster(d, {L}, clip, ppt)
    img[m > 0] = pal[i % len(pal)]
    cv2.putText(img, L, (10, 30 + 30 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.9, pal[i % len(pal)], 2)
imwrite(outp, img)
