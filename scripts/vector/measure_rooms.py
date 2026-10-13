"""Vector-based room area measurement.
Boundary layers -> high-res raster -> flood fill from room-name / finish-tag seeds.
Writes out/measure_<floor>.json and debug PNGs. Independent of any BOQ data."""
import sys, os, re, json, math, collections
import numpy as np, cv2, fitz
sys.path.insert(0, os.path.dirname(__file__))
from vecutil import *

FLOORS = {
    "B1": dict(page=9, clip=(240, 240, 1320, 830), bbox=(250, 255, 1300, 815), ppt=2.0),
    "2F": dict(page=21, clip=(240, 240, 1320, 1020), bbox=(265, 250, 1290, 900), ppt=1.5),
    "3F": dict(page=41, clip=(240, 240, 1320, 1020), bbox=(265, 250, 1290, 900), ppt=1.5),
}
# scale evidence: (label, mm, pt0, pt1) measured on CEN / 015-치수선 extension-line coordinates
SCALE_EVID = {
    "B1": [("overall 1~ grid (39200, decoded 'Z`YWW')", 39200, 262.64, 1260.32),
           ("bay '^_WW'=7800", 7800, 262.64, 461.12), ("bay ']1WW'=6100", 6100, 461.12, 616.4),
           ("vertical '^ZWW'=7300 (CEN y)", 7300, 271.04, 456.92)],
    "2F": [("overall 31400", 31400, 276.44, 1275.32), ("1200 end bay", 1200, 276.44, 314.6),
           ("vertical 19900", 19900, 260.0, 893.0), ("vertical 6600", 6600, 673.52, 883.4)],
}
SCALE_EVID["3F"] = SCALE_EVID["2F"]

STROKE_LAYERS = {"wall", "wal", "WID", "COR", "CONW", "door", "FL-DOOR", "I-Door Frame", "I-DOOR",
                 "AR-창호", "FL-FRAME", "ELEV", "E3"}
EXTRA = set(os.environ.get("EXTRA_LAYERS", "").split("|")) - {""}
STROKE_LAYERS |= EXTRA


def boundary_items(d):
    sel = []
    for it in d:
        L = it.get("layer")
        col = tuple(round(v, 2) for v in (it.get("color") or (0, 0, 0)))
        w = it.get("width") or 0
        if L == "FL-DOOR" and col != (0, 0, 0):
            continue  # grey dashed swing traces
        if L in STROKE_LAYERS:
            sel.append(it)
        elif L == "COL":
            # columns (0.72) + long thin black finish/wall lines (furniture lines in COL are short)
            if w > 0.5:
                sel.append(it)
            elif col == (0, 0, 0):
                ln = [x for x in it["items"] if x[0] == "l" and abs(x[1] - x[2]) >= 40]
                if ln:
                    sel.append(dict(it, items=ln))
        elif L == "." and it.get("fill") is not None:
            sel.append(it)
        elif L == "CEN" and len(it["items"]) >= 5 and max(it["rect"].width, it["rect"].height) < 60:
            sel.append(it)  # door swings drawn as polylines on CEN layer
        elif L == "0" and it.get("fill") is not None and max(it["rect"].width, it["rect"].height) < 40:
            sel.append(it)  # dash-dot partition lines (3F) drawn as filled dash rectangles
    return sel


DOOR_LAYERS = {"door", "FL-DOOR", "CEN", "I-Door Frame", "I-DOOR", "ELEV"}


def chains(pls, tol=0.08):
    out = []
    for pl in pls:
        if out and np.hypot(*(out[-1][-1] - pl[0])) < tol:
            out[-1] = np.vstack([out[-1], pl[1:]])
        else:
            out.append(pl.copy())
    return out


def circle3(a, b, c):
    A = np.array([[b[0] - a[0], b[1] - a[1]], [c[0] - a[0], c[1] - a[1]]]) * 2
    B = np.array([b @ b - a @ a, c @ c - a @ a])
    if abs(np.linalg.det(A)) < 1e-6:
        return None
    return np.linalg.solve(A, B)


def door_polys(it, stats):
    """Replace door-swing arcs by their two radii (leaf + closed-door chord): the opening is closed
    on the wall line and the swing wedge stays in the room the door opens into."""
    res = []
    for ch in chains(polylines(it)):
        if len(ch) >= 5:
            a, b, c = ch[0], ch[len(ch) // 2], ch[-1]
            C = circle3(a, b, c)
            if C is not None:
                r = np.hypot(*(a - C))
                dev = np.abs(np.hypot(ch[:, 0] - C[0], ch[:, 1] - C[1]) - r).max()
                ang = abs(math.degrees(math.atan2(*(a - C)[::-1]) - math.atan2(*(c - C)[::-1]))) % 360
                ang = min(ang, 360 - ang)
                if 6 <= r <= 50 and dev < 0.05 * r and 45 <= ang <= 135:
                    res.append(np.array([C, a]))
                    res.append(np.array([C, c]))
                    stats["arcs"] += 1
                    continue
        res.append(ch)
    return res


def build_mask(d, clip, ppt):
    sel = boundary_items(d)
    x0, y0 = clip[:2]
    stats = collections.Counter()
    plain = []
    W, H = int((clip[2] - x0) * ppt) + 1, int((clip[3] - y0) * ppt) + 1
    m = np.zeros((H, W), np.uint8)
    for it in sel:
        if it.get("layer") in DOOR_LAYERS:
            for pl in door_polys(it, stats):
                pts = np.round((pl - [x0, y0]) * ppt * 8).astype(np.int32)
                cv2.polylines(m, [pts], False, 255, 1, cv2.LINE_8, shift=3)
        else:
            plain.append(it)
    m = raster(plain, None, clip, ppt, thick=1, img=m)
    build_mask.stats = stats
    for it in sel:
        if it.get("fill") is not None:
            for pl in polylines(it):
                pts = np.round((pl - [x0, y0]) * ppt * 8).astype(np.int32)
                if len(pts) >= 3:
                    cv2.fillPoly(m, [pts], 255, cv2.LINE_8, shift=3)
    # morphological close: seals hairline gaps (<~150mm) between wall ends / dashed partitions
    k = int(os.environ.get("CLOSE_PX", "7"))
    if k > 1:
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    return m


TAGNUM = re.compile(r"^0[1-9]$")
TAGLET = {"DE", "DT", "CT", "PT", "WD", "ST"}
SKIP = re.compile(r"^([A-Z]'?\d|[A-Z]-\d+|F-\d|\d+|[A-E]|D\.A|DN|UP|P\.S|NO\.|SYMBOL|EXPLANATION|EA|■.*)$")


def labels_and_tags(pno, bbox):
    sp = spans(pno)
    bx0, by0, bx1, by1 = bbox
    inside = lambda s: bx0 <= (s["bbox"][0] + s["bbox"][2]) / 2 <= bx1 and by0 <= (s["bbox"][1] + s["bbox"][3]) / 2 <= by1
    sp = [s for s in sp if inside(s)]
    # finish tags: number span with a letter span right below
    nums = [s for s in sp if TAGNUM.match(s["text"]) and 8 <= s["size"] <= 9]
    lets = [s for s in sp if s["text"] in TAGLET and 8 <= s["size"] <= 9]
    tags = []
    for n in nums:
        cx = (n["bbox"][0] + n["bbox"][2]) / 2
        best = None
        for l in lets:
            lx = (l["bbox"][0] + l["bbox"][2]) / 2
            dy = l["bbox"][1] - n["bbox"][1]
            if abs(lx - cx) < 4 and 7 < dy < 15:
                best = l
        if best:
            tags.append(dict(code=f"{best['text']}-{n['text']}", x=cx, y=(n["bbox"][3] + best["bbox"][1]) / 2))
    # room names: big-ish text, merge spans on same baseline
    cand = [s for s in sp if 9.9 <= s["size"] <= 11.6 and not SKIP.match(s["text"])]
    cand.sort(key=lambda s: (round(s["bbox"][1]), s["bbox"][0]))
    merged = []
    for s in cand:
        if merged and abs(merged[-1]["bbox"][1] - s["bbox"][1]) < 2.5 and 0 <= s["bbox"][0] - merged[-1]["bbox"][2] < 8:
            m = merged[-1]
            m["text"] += s["text"]
            m["bbox"] = (m["bbox"][0], min(m["bbox"][1], s["bbox"][1]), s["bbox"][2], max(m["bbox"][3], s["bbox"][3]))
        else:
            merged.append(dict(text=s["text"], bbox=tuple(s["bbox"])))
    names = []
    for m in merged:
        t = m["text"].replace("舮", "名").strip()
        names.append(dict(name=t, x=(m["bbox"][0] + m["bbox"][2]) / 2, y=(m["bbox"][1] + m["bbox"][3]) / 2, bbox=m["bbox"]))
    return names, tags


def seed_px(mask, x, y, clip, ppt, r=12):
    px, py = int((x - clip[0]) * ppt), int((y - clip[1]) * ppt)
    H, W = mask.shape
    for rad in range(0, r):
        for dx in range(-rad, rad + 1):
            for dy in (-rad, rad) if abs(dx) != rad else range(-rad, rad + 1):
                qx, qy = px + dx, py + dy
                if 0 <= qx < W and 0 <= qy < H and mask[qy, qx] == 0:
                    return qx, qy
    return None


def measure(floor):
    cfg = FLOORS[floor]
    pno, clip, ppt, bbox = cfg["page"], cfg["clip"], cfg["ppt"], cfg["bbox"]
    ev = SCALE_EVID[floor]
    ratios = [mm / abs(p1 - p0) for _, mm, p0, p1 in ev]
    mmpt = ratios[0]
    mmpx = mmpt / ppt
    d = get_drawings(pno)
    mask = build_mask(d, clip, ppt)
    H, W = mask.shape
    names, tags = labels_and_tags(pno, bbox)
    lab = np.zeros((H, W), np.int32)  # region id per pixel
    regions = []
    seeds = [("name", n) for n in names] + [("tag", t) for t in tags]
    for kind, s in seeds:
        sp = seed_px(mask, s["x"], s["y"] + (0 if kind == "name" else 0), clip, ppt)
        if sp is None:
            s["rid"] = None
            continue
        rid = lab[sp[1], sp[0]]
        if rid == 0:
            ff = np.zeros((H + 2, W + 2), np.uint8)
            ff[1:-1, 1:-1] = (mask > 0)
            cv2.floodFill(mask.copy(), ff, sp, 128, flags=4 | (255 << 8) | cv2.FLOODFILL_MASK_ONLY)
            reg = ff[1:-1, 1:-1] == 255
            rid = len(regions) + 1
            lab[reg] = rid
            regions.append(dict(rid=rid, px=int(reg.sum()), names=[], tags=[]))
        s["rid"] = int(rid)
        regions[rid - 1]["names" if kind == "name" else "tags"].append(s)
    out = []
    for r in regions:
        reg = (lab == r["rid"]).astype(np.uint8)
        ys, xs = np.nonzero(reg)
        touches = xs.min() == 0 or ys.min() == 0 or xs.max() == W - 1 or ys.max() == H - 1
        cnts, _ = cv2.findContours(reg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        c = max(cnts, key=cv2.contourArea)
        per_px = cv2.arcLength(cv2.approxPolyDP(c, 1.0, True), True)
        area_px = r["px"] + per_px * 0.5  # half-pixel boundary correction (line pixels are on the wall line)
        codes = sorted(set(t["code"] for t in r["tags"]))
        out.append(dict(rid=r["rid"], names=[n["name"] for n in r["names"]], codes=codes,
                        tag_list=[t["code"] for t in r["tags"]],
                        area_m2=area_px * (mmpx / 1000) ** 2, raw_m2=r["px"] * (mmpx / 1000) ** 2,
                        perimeter_m=per_px * mmpx / 1000, touches_border=bool(touches),
                        bbox_pt=[round(clip[0] + xs.min() / ppt, 1), round(clip[1] + ys.min() / ppt, 1),
                                 round(clip[0] + xs.max() / ppt, 1), round(clip[1] + ys.max() / ppt, 1)]))
    res = dict(floor=floor, page=pno, mm_per_pt=mmpt, scale_checks=[(e[0], round(r_, 3)) for e, r_ in zip(ev, ratios)],
               ppt=ppt, mm_per_px=mmpx, clip=clip, regions=out,
               unseeded=[s.get("name", s.get("code")) for _, s in seeds if s.get("rid") is None])
    json.dump(res, open(os.path.join(OUT, f"measure_{floor}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    np.save(os.path.join(OUT, f"lab_{floor}.npy"), lab)
    # debug image
    dbg = np.full((H, W, 3), 255, np.uint8)
    rng = np.random.default_rng(1)
    colors = rng.integers(60, 230, (len(regions) + 1, 3))
    for r in regions:
        dbg[lab == r["rid"]] = colors[r["rid"]]
    dbg[mask > 0] = (0, 0, 0)
    for r in out:
        x0b, y0b = r["bbox_pt"][:2]
    for kind, s in seeds:
        px, py = int((s["x"] - clip[0]) * ppt), int((s["y"] - clip[1]) * ppt)
        cv2.circle(dbg, (px, py), 4, (0, 0, 255) if kind == "name" else (255, 0, 0), -1)
        if s.get("rid"):
            cv2.putText(dbg, str(s["rid"]), (px + 5, py), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    imwrite(os.path.join(OUT, f"dbg_{floor}.png"), dbg)
    return res


if __name__ == "__main__":
    fl = sys.argv[1:] or list(FLOORS)
    with open(os.path.join(OUT, "measure_log.txt"), "w", encoding="utf-8") as f:
        for F in fl:
            r = measure(F)
            f.write(f"\n=== {F} mm/pt={r['mm_per_pt']:.4f} checks={r['scale_checks']} mm/px={r['mm_per_px']:.2f}\n")
            for g in r["regions"]:
                f.write(f"r{g['rid']:3d} {g['area_m2']:9.2f}m2 per={g['perimeter_m']:7.2f} border={g['touches_border']} names={g['names']} codes={g['codes']} tags={g['tag_list']} bbox={g['bbox_pt']}\n")
            f.write(f"unseeded: {r['unseeded']}\n")
