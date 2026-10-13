"""채점기: AI 산출(v1~v5)을 두 개의 기준과 비교한다.
 A) 도면 기준(CAD 벡터 정밀 측정)  -> AI가 도면을 얼마나 정확히 읽었나
 B) 내역서 기준(전문 적산사 수량)  -> 도면만으로 낸 물량이 실제 내역과 얼마나/왜 다른가
"""
import json, re, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VEC = json.loads((ROOT / "truth/vector_reference.json").read_text())
BOQ = json.loads((ROOT / "truth/boq_truth.json").read_text())
VERSIONS = ["v1", "v2", "v3", "v4", "v5", "v6"]
CODES = ["DE-01", "DT-01", "DT-02", "DT-03", "CT-01", "CT-02", "CT-03"]

# 검증 세트: 벽으로 닫혀 있고 마감 코드가 있는 실 (벡터 측정이 확실한 실)
def norm(s):
    s = re.sub(r"\(.*?\)|\[.*?\]", "", s or "")
    s = re.sub(r"배석.*$", "", s)
    s = s.replace(" ", "").replace("장고", "창고").replace("바서", "비서")
    return s

VALID = {}
for r in VEC["regions"]:
    if r["kind"] == "closed" and r.get("code") and not r.get("leak"):
        n = norm(r["name"])
        if n == "CORRIDOR":  # 복도는 경계 해석이 갈려 검증 세트에서 제외
            continue
        VALID[(r["floor"], n)] = r
# 중회의실(임원휴게실) 과 중회의실-1 구분 유지
for r in VEC["regions"]:
    if r["name"].startswith("중회의실 (임원"):
        VALID.pop((r["floor"], norm(r["name"])), None)
        VALID[(r["floor"], "중회의실임원휴게실")] = r

def room_key(floor, name):
    raw = name or ""
    if "임원" in raw:
        return (floor, "중회의실임원휴게실")
    return (floor, norm(raw))

def score_version(v):
    d = json.loads((ROOT / f"runs/{v}/output.json").read_text())
    t = d["totals"]
    rooms = d.get("rooms", [])
    out = {"version": v, "totals": t, "n_rooms": len(rooms)}
    # 1) 실 단위 정확도 (검증 세트)
    matches = []
    for r in rooms:
        k = room_key(r["floor"], r["room"])
        if k in VALID and r.get("area_m2"):
            ref = VALID[k]["area_m2"]
            matches.append({"floor": k[0], "room": VALID[k]["name"], "code": VALID[k]["code"],
                            "ai": round(r["area_m2"], 2), "ref": ref,
                            "err_pct": round((r["area_m2"] - ref) / ref * 100, 1),
                            "confidence": r.get("confidence"), "basis": r.get("basis", "")})
    out["room_matches"] = matches
    out["room_coverage"] = f"{len(matches)}/{len(VALID)}"
    out["room_mape"] = round(st.mean(abs(m["err_pct"]) for m in matches), 1) if matches else None
    out["room_within5"] = sum(abs(m["ai"] - m["ref"]) / m["ref"] <= 0.05 for m in matches)  # 반올림 전 값으로 판정
    # 2) 근거 추적성: 숫자 근거(high/mid)로 낸 면적 비율
    tot = sum((r.get("area_m2") or 0) for r in rooms)
    traced = sum((r.get("area_m2") or 0) for r in rooms if r.get("confidence") in ("high", "mid"))
    out["traceable_share"] = round(traced / tot * 100, 1) if tot else 0.0
    # 3) 코드별 합계 vs 도면 기준
    vref = VEC["by_code_total"]
    out["code_err_vs_drawing"] = {c: round((t.get(c, 0) - vref[c]) / vref[c] * 100, 1) for c in CODES}
    out["code_mape_vs_drawing"] = round(st.mean(abs(x) for x in out["code_err_vs_drawing"].values()), 1)
    drawing_total = round(sum(vref.values()), 2)
    out["total_err_vs_drawing"] = round((t["floor_total"] - drawing_total) / drawing_total * 100, 1)
    # 4) 내역서 기준 (자재 종류별)
    b = BOQ["by_code"]
    cat_boq = {"DE": b["DE-01"], "DT": b["DT-01"] + b["DT-02"] + b["DT-03"],
               "CT": sum(b[k] for k in b if k.startswith("CT"))}
    cat_ai = {"DE": t["DE-01"], "DT": t["DT-01"] + t["DT-02"] + t["DT-03"],
              "CT": t["CT-01"] + t["CT-02"] + t["CT-03"]}
    out["cat_vs_boq"] = {k: {"ai": round(cat_ai[k], 1), "boq": cat_boq[k],
                             "err_pct": round((cat_ai[k] - cat_boq[k]) / cat_boq[k] * 100, 1)} for k in cat_ai}
    out["total_err_vs_boq"] = round((t["floor_total"] - sum(b.values())) / sum(b.values()) * 100, 1)
    out["baseboard_err_vs_boq"] = round((t["baseboard_m"] - BOQ["baseboard_m"]) / BOQ["baseboard_m"] * 100, 1)
    return out

if __name__ == "__main__":
    vref = VEC["by_code_total"]
    res = {"validation_set": [{"floor": k[0], "room": r["name"], "code": r["code"], "ref": r["area_m2"]} for k, r in VALID.items()],
           "drawing_by_code": vref, "drawing_total": round(sum(vref.values()), 2),
           "boq": BOQ, "versions": [score_version(v) for v in VERSIONS]}
    (ROOT / "harness/scores.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print("검증 세트", len(VALID), "실 / 도면 기준 합계", res["drawing_total"])
    for s in res["versions"]:
        print(s["version"], "실MAPE", s["room_mape"], "(", s["room_coverage"], " ±5%이내", s["room_within5"], ")",
              "근거비율", s["traceable_share"], "| 코드MAPE", s["code_mape_vs_drawing"], "| 합계오차(도면)", s["total_err_vs_drawing"],
              "| 합계오차(내역)", s["total_err_vs_boq"], "| 걸레받이(내역)", s["baseboard_err_vs_boq"])
