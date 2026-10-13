import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from vecutil import *
pno = int(sys.argv[1]); X0, Y0, X1, Y1 = map(float, sys.argv[2:6])
f = open(os.path.join(OUT, "probe_rect.txt"), "w", encoding="utf-8")
for it in get_drawings(pno):
    r = it["rect"]
    if r.x0 <= X1 and r.x1 >= X0 and r.y0 <= Y1 and r.y1 >= Y0 and it.get("layer") != "SHEET":
        f.write(f"{it.get('layer')} col={tuple(round(c,2) for c in (it.get('color') or ()))} w={round(it.get('width') or 0,2)} fill={it.get('fill')} dashes={it.get('dashes')} rect={tuple(round(v,1) for v in r)} n={len(it['items'])}\n")
f.close()
