"""벡터 실측 결과 -> 웹 3D용 scene.json (mm 좌표)
cells: 마감 코드별 바닥 영역 폴리곤(구멍=기둥 포함), walls: 경계 레이어 선분, glass: 창호 선분"""
import sys, os, json, math
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
from vecutil import *
import measure_rooms as MR
import build_reference as BR

WALL_L = {"wall", "wal", "WID", "COR", "CONW", "CON", "ELEV"}
GLASS_L = {"AR-창호", "FL-FRAME"}

def segs_from(items, clip, mmpt, layers, min_mm=60, width_min=None):
    out = []
    x0c, y0c, x1c, y1c = clip
    for it in items:
        L = it.get("layer")
        if L not in layers:
            continue
        if width_min is not None and (it.get("width") or 0) < width_min:
            continue
        for pl in polylines(it):
            for a, b in zip(pl[:-1], pl[1:]):
                ax, ay = float(a[0]), float(a[1]); bx, by = float(b[0]), float(b[1])
                if not (x0c <= ax <= x1c and y0c <= ay <= y1c and x0c <= bx <= x1c and y0c <= by <= y1c):
                    continue
                X1, Y1 = (ax - x0c) * mmpt, (ay - y0c) * mmpt
                X2, Y2 = (bx - x0c) * mmpt, (by - y0c) * mmpt
                if math.hypot(X2 - X1, Y2 - Y1) < min_mm:
                    continue
                out.append([round(X1), round(Y1), round(X2), round(Y2)])
    # 중복 제거
    seen, uniq = set(), []
    for s in out:
        k = tuple(s) if (s[0], s[1]) <= (s[2], s[3]) else (s[2], s[3], s[0], s[1])
        if k not in seen:
            seen.add(k); uniq.append(s)
    return uniq

scene = {"floors": {}}
for F in ["B1", "2F", "3F"]:
    res, regs, cells, cc = BR.run(F)
    cfg = MR.FLOORS[F]
    clip, ppt = cfg["clip"], cfg["ppt"]
    mmpx = res["mm_per_px"]; mmpt = res["mm_per_pt"]
    lab = np.load(os.path.join(OUT, f"lab_{F}.npy"))
    reg_by_rid = {r.get("rid"): r for r in regs if r.get("rid") is not None}
    cell_list = []
    for cid, code in cc.items():
        m = (cells == cid).astype(np.uint8)
        if m.sum() < 30:
            continue
        ys, xs = np.nonzero(m)
        rid = int(lab[ys[len(ys) // 2], xs[len(xs) // 2]])
        r = reg_by_rid.get(rid, {})
        name = r.get("name", "")
        if r.get("kind") == "open_group":
            mem = [x["name"] for x in r.get("members", []) if x.get("code") == code]
            name = " · ".join(mem[:4]) if mem else f"{code or '코드 없음'} 구역"
        cnts, hier = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        if hier is None:
            continue
        hier = hier[0]
        for i, c in enumerate(cnts):
            if hier[i][3] != -1 or cv2.contourArea(c) < 25:
                continue
            outer = cv2.approxPolyDP(c, 1.6, True)[:, 0, :]
            holes = []
            ch = hier[i][2]
            while ch != -1:
                hc = cnts[ch]
                if cv2.contourArea(hc) > 9:
                    holes.append([[round(float(p[0]) * mmpx), round(float(p[1]) * mmpx)] for p in cv2.approxPolyDP(hc, 1.2, True)[:, 0, :]])
                ch = hier[ch][0]
            cell_list.append({"code": code, "name": name, "kind": r.get("kind"),
                              "region_area_m2": r.get("area_m2"),
                              "cell_area_m2": round(float(cv2.contourArea(c)) * (mmpx / 1000) ** 2, 2),
                              "poly": [[round(float(p[0]) * mmpx), round(float(p[1]) * mmpx)] for p in outer],
                              "holes": holes})
    d = get_drawings(cfg["page"])
    bx0, by0, bx1, by1 = cfg["bbox"]
    walls = segs_from(d, (bx0, by0, bx1, by1), mmpt, WALL_L)
    # 기준점을 clip 원점으로 맞추기 (cells는 clip 원점 기준)
    off = ((bx0 - clip[0]) * mmpt, (by0 - clip[1]) * mmpt)
    walls = [[s[0] + off[0], s[1] + off[1], s[2] + off[0], s[3] + off[1]] for s in walls]
    cols = segs_from(d, (bx0, by0, bx1, by1), mmpt, {"COL"}, min_mm=150, width_min=0.7)
    cols = [[s[0] + off[0], s[1] + off[1], s[2] + off[0], s[3] + off[1]] for s in cols]
    glass = segs_from(d, (bx0, by0, bx1, by1), mmpt, GLASS_L)
    glass = [[s[0] + off[0], s[1] + off[1], s[2] + off[0], s[3] + off[1]] for s in glass]
    scene["floors"][F] = {"mm_per_px": mmpx, "cells": cell_list,
                          "walls": [[round(v) for v in s] for s in walls],
                          "cols": [[round(v) for v in s] for s in cols],
                          "glass": [[round(v) for v in s] for s in glass]}
    print(F, "cells", len(cell_list), "walls", len(walls), "cols", len(cols), "glass", len(glass))
json.dump(scene, open(os.path.join(OUT, "scene.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("saved", os.path.getsize(os.path.join(OUT, "scene.json")))
