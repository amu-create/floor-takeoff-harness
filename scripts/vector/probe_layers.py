import os, pathlib
import fitz, collections, json, sys, os
ROOT = os.environ.get("CONPA_ROOT", str(pathlib.Path(__file__).resolve().parents[2]))
doc = fitz.open(os.path.join(ROOT, "data", "raw_kba", "plan.pdf"))
out = open(os.path.join(ROOT, "out", "probe_layers.txt"), "w", encoding="utf-8")
for pg in [9, 21, 41, 10, 22, 42]:
    p = doc[pg - 1]
    d = p.get_drawings()
    stat = collections.defaultdict(lambda: [0, 0, fitz.Rect(), collections.Counter(), collections.Counter()])
    for it in d:
        L = it.get("layer")
        s = stat[L]
        s[0] += 1
        s[1] += len(it["items"])
        s[2] |= it["rect"]
        s[3][(tuple(round(x, 2) for x in (it.get("color") or ())), round(it.get("width") or 0, 2), it.get("type"))] += 1
        for x in it["items"]:
            s[4][x[0]] += 1
    out.write(f"\n=== page {pg} rot={p.rotation} rect={p.rect} drawings={len(d)}\n")
    for L, s in sorted(stat.items(), key=lambda kv: -kv[1][0]):
        out.write(f"{str(L):20s} n={s[0]:6d} items={s[1]:7d} bbox={tuple(round(v) for v in s[2])} ops={dict(s[4])} style={s[3].most_common(3)}\n")
    # text
    td = p.get_text("dict")
    spans = []
    for b in td["blocks"]:
        for l in b.get("lines", []):
            for sp in l["spans"]:
                t = sp["text"].strip()
                if t:
                    spans.append((round(sp["bbox"][0], 1), round(sp["bbox"][1], 1), round(sp["size"], 1), t))
    out.write(f"-- spans {len(spans)}\n")
    for s in spans[:400]:
        out.write(f"   {s}\n")
out.close()
