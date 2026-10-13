import os, pathlib
import json, os
OUT = os.path.join(os.environ.get("CONPA_ROOT", str(pathlib.Path(__file__).resolve().parents[2])), "out")
core = json.load(open(os.path.join(OUT, "vector_reference_core.json"), encoding="utf-8"))
regions = []
for r in core["regions"]:
    r = dict(r)
    r.pop("rid", None)
    r.setdefault("members", [])
    regions.append(r)
ref = {
    "method": ("PyMuPDF vector extraction of KEY MARK & MATERIAL plans (p9 B1 1/150, p21 2F 1/120, p41 3F 1/120). "
               "Scale from CEN/015-치수선 extension-line x/y coordinates vs dimension text (2F/3F 31400, 19900, 1200, 6600; "
               "B1 39200/7800/6100/7300 decoded from broken font) — all checks agree within 0.04%. "
               "Boundary layers rasterised at ~21 mm/px (2F/3F) and ~19.6 mm/px (B1): wall, wal, WID, COR, CONW, AR-창호, "
               "FL-FRAME, I-Door Frame, I-DOOR, ELEV, E3, black FL-DOOR, door; COL layer only for columns (0.72pt) and long "
               "(>=40pt) black finish/wall lines in small groups; filled '.' hatches; CEN door-swing polylines; '0' filled dash "
               "segments (3F dash-dot partitions). Door-swing arcs are replaced by their two radii so openings close on the wall "
               "line. 7px morphological close seals hairline gaps. Flood fill (4-conn) from every room-name and finish-tag "
               "text position; area = pixels + half the contour length (boundary-line correction) x (mm/px)^2 = net (안목) "
               "area, columns automatically excluded. Finish code = 2-line tag (number over letters, e.g. 02/DT -> DT-02) "
               "inside the filled region. Regions holding >1 room name or code = open_group; their area is apportioned per "
               "code by (a) eroding free space by 800 mm to cut at doorways/necks, (b) geodesic nearest-marker growth "
               "(markers = finish tags + uncoded room names such as TOILET/탕비실). No BOQ/내역서 data was opened."),
    "scale": core["scale"],
    "regions": regions,
    "floor_summary": core["floor_summary"],
    "by_code_total": core["by_code_total"],
    "limitations": [
        "Areas are net floor (안목) areas inside boundary lines at ~20 mm/px raster; expected pixel error about ±1-2% for rooms >10 m2, worse for small rooms (<5 m2).",
        "open_group per-code splits (2F OPEN-2F-3/9, 3F OPEN-3F-2/3) are geometric apportionments between tags, not drawn boundaries; the group total is reliable, the split is approximate (±10-20 m2 possible in 3F OPEN-3F-2 between DT-02 corridor/lounge and DT-03 office).",
        "3F 대회협력실(4名)/미디어소통팀 and 2F 윤리팀/사업팀/평가팀/재무팀/회원팀 have no own tag; they were assigned to the nearest tag (DT-02 or DT-03). 3F 대회협력실 got split between DT-02 and DT-03 by the geodesic rule; likely all DT-03 in reality.",
        "Stairs (주계단실/부계단실), EV shaft, P.S and unlabeled spaces were not measured. B1 unlabeled open area (west half, lobby/parking side, no room names or tags on p9) and B1 toilets were not measured.",
        "Several enclosed rooms have no finish tag on the plan (B1 준비실, 이사장실, 방송실, 기사대기실, ELE'V HALL; 2F 직원휴게실, INFO'MATION, O.A ROOM; 3F O.A ROOM) -> code null, counted as uncoded even if a finish note text exists (e.g. B1 기사대기실 '~DELUXE TILE FIN.', 2F 직원휴게실 '~DECO TILE FIN.').",
        "B1 서고 region includes the small passage in front of 방송실 (door gap); B1 법률구조재단 DT-01 region includes the lobby strip in front of 이사장실/준비실. Possible +2~4 m2 each.",
        "2F 금고 tag reads DE-01 but its text note says P-TILE FIN.; tag value used as-is.",
        "Toilet/ELE'V HALL groups (2F, 3F) merge toilets with lift lobby; toilet part (~23 m2 each) is code null.",
        "Scale for 3F reuses 2F dimension evidence (identical dimension strings and CEN coordinates on p41).",
    ],
}
for p in [os.path.join(OUT, "vector_reference.json")]:
    json.dump(ref, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("ok")
