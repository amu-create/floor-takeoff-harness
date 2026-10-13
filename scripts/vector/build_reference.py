"""Assemble vector_reference.json + overlays from measure_rooms flood-fill results.
Regions that contain >1 room name / finish tag are 'open_group'; their area is additionally
apportioned to codes by a marker watershed on the distance transform (splits at necks/doorways)."""
import sys, os, re, json, math, collections
import numpy as np, cv2, fitz
from scipy import ndimage as ndi
sys.path.insert(0, os.path.dirname(__file__))
from vecutil import *
import measure_rooms as MR

UNCODED = re.compile(r"TOILET|화장실|계단|CAR LIFT|세면실|탕비실|서버실|P\.S|ELE'V\(")
STAIR = re.compile(r"계단")
GENERIC = re.compile(r"^(CORRIDOR|OFFICE|\)|名|名\)|\(.*\))$")


NECK_MM = float(os.environ.get("NECK_MM", "800"))


def geo_grow(seeds, region):
    """Geodesic nearest-seed growth of labelled seeds inside a boolean region."""
    ws = seeds.copy()
    ws[~region] = 0
    free = region & (ws == 0)
    k3 = np.ones((3, 3), bool)
    for _ in range(20000):
        if not free.any():
            break
        grown = ndi.grey_dilation(ws, footprint=k3)
        upd = free & (grown > 0)
        if not upd.any():
            break
        ws[upd] = grown[upd]
        free &= ~upd
    return ws


def clean(n):
    n = n.replace("舮", "名").strip()
    n = re.sub(r"\s*\(\s*", " (", n)
    return n


def run(floor):
    res = MR.measure(floor)
    cfg = MR.FLOORS[floor]
    clip, ppt = cfg["clip"], cfg["ppt"]
    mmpx = res["mm_per_px"]
    px2m2 = (mmpx / 1000) ** 2
    lab = np.load(os.path.join(OUT, f"lab_{floor}.npy"))
    d = get_drawings(cfg["page"])
    wall = MR.build_mask(d, clip, ppt)
    names, tags = MR.labels_and_tags(cfg["page"], cfg["bbox"])
    # merge label fragments like '사업팀 (3' + '名' + ')' that lie on one line
    regions_out, cells_img = [], np.zeros(lab.shape, np.int32)
    cell_codes = {}
    for r in res["regions"]:
        rid = r["rid"]
        reg = lab == rid
        nm = []
        for n in names:
            px, py = int((n["x"] - clip[0]) * ppt), int((n["y"] - clip[1]) * ppt)
            if 0 <= py < lab.shape[0] and 0 <= px < lab.shape[1]:
                sp = MR.seed_px(MR.build_mask.__wrapped__(d, clip, ppt) if False else wall, n["x"], n["y"], clip, ppt)
                if sp and lab[sp[1], sp[0]] == rid:
                    nm.append(dict(n, px=sp))
        tg = []
        for t in tags:
            sp = MR.seed_px(wall, t["x"], t["y"], clip, ppt)
            if sp and lab[sp[1], sp[0]] == rid:
                tg.append(dict(t, px=sp))
        # compose display names: join fragments on same baseline within 60pt
        nm.sort(key=lambda n: (round(n["y"] / 4), n["x"]))
        merged = []
        for n in nm:
            if merged and abs(merged[-1]["y"] - n["y"]) < 3 and n["bbox"][0] - merged[-1]["bbox"][2] < 6:
                merged[-1]["name"] += n["name"]; merged[-1]["bbox"] = (merged[-1]["bbox"][0], 0, n["bbox"][2], 0)
            else:
                merged.append(dict(n))
        for m in merged:
            m["name"] = clean(m["name"])
        merged = [m for m in merged if not re.fullmatch(r"[\)名\s]*", m["name"])]
        stairs = [m for m in merged if STAIR.search(m["name"])]
        if stairs and len(merged) == len(stairs) and not tg:
            regions_out.append(dict(floor=floor, name="/".join(m["name"] for m in stairs), code=None,
                                    area_m2=None, perimeter_m=None, kind="excluded", members=[], leak=False,
                                    note="stair seed lands between treads; stair area not measured"))
            continue
        # markers: finish tags (code) + uncoded-type room names (null)
        markers = [(t["code"], t["px"], t["code"]) for t in tg]
        markers += [(None, m["px"], m["name"]) for m in merged if UNCODED.search(m["name"])]
        distinct = sorted(set(m["name"] for m in merged if not GENERIC.match(m["name"])))
        codes = sorted(set(t["code"] for t in tg))
        is_group = len(distinct) > 1 or len(codes) > 1 or (codes and any(m[0] is None for m in markers))
        ys, xs = np.nonzero(reg)
        area = (reg.sum() + r["perimeter_m"] * 1000 / mmpx * 0.5) * px2m2
        entry = dict(floor=floor, rid=rid, area_m2=round(area, 2), perimeter_m=round(r["perimeter_m"], 2),
                     bbox_pt=r["bbox_pt"])
        # watershed split
        split = collections.OrderedDict()
        if len(markers) >= 2:
            sub = reg[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
            # 1) neck cut: erode free space by NECK_MM so doorways / narrow passages separate
            rad = max(3, int(NECK_MM / mmpx))
            er = cv2.erode(sub.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * rad + 1, 2 * rad + 1))) > 0
            comps, nc = ndi.label(er)
            P = geo_grow(comps, sub)
            # names inside region become secondary markers (code None unless tag in same component)
            name_mk = [(None, m["px"], m["name"]) for m in merged if not UNCODED.search(m["name"])]
            bycomp = collections.defaultdict(list)
            for mk_ in markers + name_mk:
                (px, py) = mk_[1]
                bycomp[P[py - ys.min(), px - xs.min()]].append(mk_)
            seeds = np.zeros(sub.shape, np.int32)
            final_markers = []
            for cidx in range(1, nc + 1):
                mks = bycomp.get(cidx, [])
                tagm = [m_ for m_ in mks if m_[0] is not None]
                unc = [m_ for m_ in mks if m_[0] is None and UNCODED.search(m_[2])]
                use = tagm + unc  # name-only components inherit from the geodesically nearest tagged part
                if not use:
                    continue  # unmarked component: absorbed by neighbours below
                if len(use) == 1:
                    final_markers.append(use[0]); seeds[(comps == cidx)] = len(final_markers)
                else:
                    sub_seed = np.zeros(sub.shape, np.int32)
                    base_i = len(final_markers)
                    for m_ in use:
                        final_markers.append(m_)
                        sub_seed[m_[1][1] - ys.min(), m_[1][0] - xs.min()] = len(final_markers)
                    part = geo_grow(sub_seed, comps == cidx)
                    seeds[comps == cidx] = part[comps == cidx]
            markers = final_markers if final_markers else markers
            ws = geo_grow(seeds, sub)
            agg = collections.defaultdict(lambda: [0, []])
            for i, (code, _, lbl) in enumerate(markers):
                c = ws == (i + 1)
                agg[code][0] += int(c.sum())
                agg[code][1].append(lbl)
                full = np.zeros(lab.shape, bool)
                full[ys.min():ys.max() + 1, xs.min():xs.max() + 1] = c
                cid = len(cell_codes) + 1
                cells_img[full] = cid
                cell_codes[cid] = code
            tot = sum(v[0] for v in agg.values())
            for code, (n, lbls) in agg.items():
                split[str(code)] = round(area * n / tot, 2)
        else:
            cid = len(cell_codes) + 1
            cells_img[reg] = cid
            code = markers[0][0] if markers else None
            cell_codes[cid] = code
            split[str(code)] = round(area, 2)
        mem = []
        for m in merged:
            # nearest tag (pt) inside same region within 45pt
            best = None
            for t in tg:
                dd = math.hypot(t["x"] - m["x"], t["y"] - m["y"])
                if dd < 45 and (best is None or dd < best[0]):
                    best = (dd, t["code"])
            mem.append(dict(name=m["name"], code=None if UNCODED.search(m["name"]) else (best[1] if best else None)))
        if not is_group:
            nm0 = merged[0]["name"] if merged else (f"(unnamed, tag {codes[0]})" if codes else "(unnamed)")
            entry.update(name=nm0, code=codes[0] if codes else None, kind="closed", members=[], leak=False,
                         note="" if codes else "no finish tag found in this enclosed region")
            if UNCODED.search(nm0):
                entry["code"] = None
                entry["note"] = "uncoded space type"
        else:
            entry.update(name=f"OPEN-{floor}-{rid}", code=codes[0] if len(codes) == 1 and not any(m[0] is None for m in markers) else None,
                         kind="open_group", members=mem, member_codes=codes, leak=True,
                         code_split_m2=split,
                         note="flood fill crossed doorless openings; per-code split = geodesic nearest-marker apportionment (markers: finish tags + uncoded room names) - approximate")
        entry["code_split_m2"] = split
        regions_out.append(entry)
    return res, regions_out, cells_img, cell_codes


PALETTE = {"DE-01": (66, 135, 245), "DT-01": (240, 160, 40), "DT-02": (60, 180, 75), "DT-03": (230, 90, 60),
           "CT-01": (145, 30, 180), "CT-02": (240, 50, 230), "CT-03": (70, 200, 200), "None": (170, 170, 170)}


def overlay(floor, cells, cell_codes, pno, clip, ppt, summary):
    from PIL import Image, ImageDraw, ImageFont
    zoom = ppt
    pix = doc()[pno - 1].get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=fitz.Rect(*clip))
    base = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)[:, :, :3].astype(np.float32)
    H, W = min(base.shape[0], cells.shape[0]), min(base.shape[1], cells.shape[1])
    base = base[:H, :W]; cells = cells[:H, :W]
    img = 255 - (255 - base) * 0.45
    col = np.zeros((H, W, 3), np.float32); a = np.zeros((H, W), np.float32)
    for cid, code in cell_codes.items():
        m = cells == cid
        col[m] = PALETTE.get(str(code), (120, 120, 120)); a[m] = 0.55 if code else 0.30
    img = img * (1 - a[..., None]) + col * a[..., None]
    # cell outlines
    edges = cv2.morphologyEx((cells > 0).astype(np.uint8) * 0 + cells.astype(np.uint16).astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    img[edges & (cells > 0)] = img[edges & (cells > 0)] * 0.5
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    scale = 1600 / im.width
    im = im.resize((1600, int(im.height * scale)), Image.LANCZOS)
    legend_h = 40 + 26 * ((len(summary) + 3) // 4)
    canvas = Image.new("RGB", (1600, im.height + legend_h + 50), "white")
    canvas.paste(im, (0, 50))
    dr = ImageDraw.Draw(canvas)
    try:
        f1 = ImageFont.truetype("malgun.ttf", 22); f2 = ImageFont.truetype("malgun.ttf", 17)
    except Exception:
        f1 = f2 = ImageFont.load_default()
    dr.text((16, 12), f"{floor} — vector flood-fill floor finish areas (m², net/안목)", fill=(20, 20, 20), font=f1)
    y0 = im.height + 60
    for i, (code, m2) in enumerate(summary):
        x, y = 16 + (i % 4) * 395, y0 + (i // 4) * 26
        dr.rectangle([x, y + 3, x + 20, y + 19], fill=PALETTE.get(code, (120, 120, 120)), outline=(60, 60, 60))
        dr.text((x + 28, y), f"{'no code' if code == 'None' else code}: {m2:.1f} m²", fill=(20, 20, 20), font=f2)
    canvas.save(os.path.join(OUT, f"overlay_{floor}.png"))


if __name__ == "__main__":
    allregions, scale, fsum, bct = [], {}, {}, collections.Counter()
    log = open(os.path.join(OUT, "build_log.txt"), "w", encoding="utf-8")
    for F in ["B1", "2F", "3F"]:
        res, regs, cells, cc = run(F)
        scale[F] = dict(mm_per_pt=round(res["mm_per_pt"], 4), checks=res["scale_checks"],
                        raster_mm_per_px=round(res["mm_per_px"], 2), page=res["page"])
        by = collections.Counter()
        for r in regs:
            for k, v in (r.get("code_split_m2") or {}).items():
                by[k] += v
        coded = sum(v for k, v in by.items() if k != "None")
        fsum[F] = dict(coded_m2=round(coded, 2), uncoded_m2=round(by.get("None", 0), 2),
                       filled_total_m2=round(coded + by.get("None", 0), 2),
                       by_code={k: round(v, 2) for k, v in sorted(by.items()) if k != "None"})
        for k, v in by.items():
            if k != "None":
                bct[k] += v
        cfg = MR.FLOORS[F]
        overlay(F, cells, cc, cfg["page"], cfg["clip"], cfg["ppt"], sorted(((k, v) for k, v in by.items()), key=lambda kv: kv[0]))
        for r in regs:
            log.write(json.dumps(r, ensure_ascii=False) + "\n")
            allregions.append(r)
        log.write(json.dumps(fsum[F], ensure_ascii=False) + "\n")
    json.dump(dict(scale=scale, regions=allregions, floor_summary=fsum,
                   by_code_total={k: round(v, 2) for k, v in sorted(bct.items())}),
              open(os.path.join(OUT, "vector_reference_core.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log.close()
