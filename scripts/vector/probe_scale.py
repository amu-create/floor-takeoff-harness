import sys, os, collections, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from vecutil import *
f = open(os.path.join(OUT, "probe_scale.txt"), "w", encoding="utf-8")
for pno in [9, 10, 21, 22, 41, 42]:
    d = get_drawings(pno)
    f.write(f"\n=== page {pno}\n")
    vx = collections.Counter(); hy = collections.Counter()
    for it in d:
        if it.get("layer") != "CEN":
            continue
        for x in it["items"]:
            if x[0] != "l":
                continue
            a, b = x[1], x[2]
            if abs(a.x - b.x) < 0.05 and abs(a.y - b.y) > 3:
                vx[round(a.x, 2)] += abs(a.y - b.y)
            if abs(a.y - b.y) < 0.05 and abs(a.x - b.x) > 3:
                hy[round(a.y, 2)] += abs(a.x - b.x)
    f.write("CEN vertical x (len>100): " + str(sorted((k, round(v)) for k, v in vx.items() if v > 100)) + "\n")
    f.write("CEN horizontal y (len>100): " + str(sorted((k, round(v)) for k, v in hy.items() if v > 100)) + "\n")
    # short vertical/horizontal ticks / extension lines outside the plan (dimension rows)
    lay = collections.Counter()
    ticks = []
    for it in d:
        r = it["rect"]
        if r.y1 < 250 and r.y0 > 140 and r.x0 > 200 and r.x1 < 1400:
            lay[it.get("layer")] += 1
            for x in it["items"]:
                if x[0] == "l":
                    ticks.append((it.get("layer"), round(x[1].x, 2), round(x[1].y, 2), round(x[2].x, 2), round(x[2].y, 2)))
    f.write(f"top dim zone layers: {dict(lay)}\n")
    for t in ticks[:80]:
        f.write(f"  {t}\n")
    sp = [s for s in spans(pno) if s['bbox'][1] < 240 and s['bbox'][1] > 140 and s['bbox'][0] < 1400]
    f.write("top texts: " + str([(s['text'], round((s['bbox'][0] + s['bbox'][2]) / 2, 1), round(s['bbox'][1], 1)) for s in sp]) + "\n")
    sp = [s for s in spans(pno) if s['bbox'][0] < 240 and s['bbox'][0] > 140]
    f.write("left texts: " + str([(s['text'], round(s['bbox'][0], 1), round((s['bbox'][1] + s['bbox'][3]) / 2, 1)) for s in sp]) + "\n")
f.close()
