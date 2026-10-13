"""v6 결과 -> 내역서 양식 엑셀(공종별집계 + 산출근거서 + 검토 필요 + 실험 기록)"""
import json, re
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
v6 = json.loads((ROOT / "runs/v6/output.json").read_text())
sc = json.loads((ROOT / "harness/scores.json").read_text())
vec = json.loads((ROOT / "truth/vector_reference.json").read_text())
boq = json.loads((ROOT / "truth/boq_truth.json").read_text())["by_code"]

F = "Arial"
H = Font(name=F, bold=True, color="FFFFFF"); HF = PatternFill("solid", fgColor="2B3A42")
B = Font(name=F); BB = Font(name=F, bold=True); BLUE = Font(name=F, color="0000FF"); GREEN = Font(name=F, color="008000")
thin = Side(style="thin", color="BFBFBF"); BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
WRAP = Alignment(wrap_text=True, vertical="top")

def header(ws, row, cols, widths):
    for i, (c, w) in enumerate(zip(cols, widths), 1):
        cell = ws.cell(row=row, column=i, value=c); cell.font = H; cell.fill = HF
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True); cell.border = BOX
        ws.column_dimensions[get_column_letter(i)].width = w

ITEM = {"DE-01": ("비닐타일 깔기 [DE-01]", "디럭스타일 THK3 (도면 범례 450x450)"),
        "DT-01": ("비닐타일 깔기 [DT-01]", "데코타일 (MATERIAL LIST 600x600 T5)"),
        "DT-02": ("비닐타일 깔기 [DT-02]", "데코타일 457x914"),
        "DT-03": ("비닐타일 깔기 [DT-03]", "데코타일 457x914"),
        "CT-01": ("타일카펫 깔기 [CT-01]", "타일카펫 610x610"),
        "CT-02": ("타일카펫 깔기 [CT-02]", "타일카펫 610x610"),
        "CT-03": ("타일카펫 깔기 [CT-03]", "타일카펫 610x610")}
NOTE = {"DE-01": "내역서 규격 300x300 ↔ 도면 450x450 (규격 불일치 확인 필요)",
        "DT-01": "내역서 규격 450x450 ↔ MATERIAL LIST 600x600 (규격 불일치 확인 필요)",
        "CT-01": "B1 다목적 대회의실 단상(우드플로링) AI가 약 9.4㎡ 공제 (내역 단상 6000x1200=7.2㎡)"}

wb = Workbook()
# ---------------- 산출근거서 ----------------
ws2 = wb.active; ws2.title = "산출근거서"
ws2["A1"] = "산출근거서 - 대한변호사협회 신회관 인테리어 공사 / 바닥 마감 (AI 산출 v6)"; ws2["A1"].font = Font(name=F, bold=True, size=13)
ws2["A2"] = "파란 글씨 = AI가 도면에서 읽은 값(입력값). 오차 열은 수식. 도면 기준 = PDF 벡터 정밀 측정(벽으로 닫힌 실만)."; ws2["A2"].font = Font(name=F, italic=True, color="666666")
cols = ["No", "층", "실명", "마감코드", "가로(mm)", "세로(mm)", "면적(㎡)", "걸레받이(m)", "산출 근거 (도면·치수)", "신뢰도", "검토 기록", "도면 기준(㎡)", "오차(%)"]
header(ws2, 4, cols, [5, 6, 24, 9, 9, 9, 10, 11, 70, 8, 45, 12, 9])
ref_by = {}
for m in sc["versions"][-1]["room_matches"]:
    ref_by[(m["floor"], m["ai"])] = m["ref"]
r0 = 5
order = {"B1": 0, "2F": 1, "3F": 2}
rooms = sorted(v6["rooms"], key=lambda r: (order.get(r["floor"], 9), r["code"] or ""))
for i, r in enumerate(rooms):
    row = r0 + i
    vals = [i + 1, r["floor"], r["room"], r["code"], r.get("w_mm"), r.get("d_mm"), r.get("area_m2"), r.get("baseboard_m"),
            r.get("basis", ""), r.get("confidence"), r.get("review", "")]
    for c, v in enumerate(vals, 1):
        cell = ws2.cell(row=row, column=c, value=v); cell.border = BOX; cell.alignment = WRAP
        cell.font = BLUE if c in (5, 6, 7, 8) else B
    ref = ref_by.get((r["floor"], round(r["area_m2"], 2))) if r.get("area_m2") else None
    if ref:
        ws2.cell(row=row, column=12, value=ref).font = GREEN
        ws2.cell(row=row, column=13, value=f"=IFERROR((G{row}-L{row})/L{row},\"\")")
    for c in (12, 13):
        ws2.cell(row=row, column=c).border = BOX
    ws2.cell(row=row, column=7).number_format = "#,##0.00"; ws2.cell(row=row, column=13).number_format = "0.0%"
    ws2.row_dimensions[row].height = 60
last = r0 + len(rooms) - 1
ws2.freeze_panes = "D5"

# ---------------- 공종별집계 ----------------
ws = wb.create_sheet("공종별집계", 0)
ws["A1"] = "공종별집계 - 바닥 마감 (목공사및수장공사 중)"; ws["A1"].font = Font(name=F, bold=True, size=13)
ws["A2"] = "수량 = 산출근거서 합계(SUMIFS). 도면 기준 = PDF 벡터 측정, 내역서 = 발주처 공개 공내역서(2022). 수량은 정미량(할증은 일위대가에서 처리)."; ws["A2"].font = Font(name=F, italic=True, color="666666")
header(ws, 4, ["품명", "규격", "단위", "AI 산출 수량", "도면 기준(벡터)", "내역서 수량", "AI-도면 오차", "AI-내역 차이", "비고"], [26, 34, 6, 13, 14, 12, 12, 12, 50])
row = 5
for code, (name, spec) in ITEM.items():
    ws.cell(row=row, column=1, value=name); ws.cell(row=row, column=2, value=spec); ws.cell(row=row, column=3, value="M2")
    ws.cell(row=row, column=4, value=f"=SUMIFS(산출근거서!$G${r0}:$G${last},산출근거서!$D${r0}:$D${last},\"{code}\")")
    ws.cell(row=row, column=5, value=vec["by_code_total"][code]).font = GREEN
    ws.cell(row=row, column=6, value=boq[code]).font = BLUE
    ws.cell(row=row, column=7, value=f"=(D{row}-E{row})/E{row}")
    ws.cell(row=row, column=8, value=f"=D{row}-F{row}")
    ws.cell(row=row, column=9, value=NOTE.get(code, ""))
    row += 1
for code in ("CT-04", "CT-05"):
    ws.cell(row=row, column=1, value=f"타일카펫 깔기 [{code}]"); ws.cell(row=row, column=2, value="타일카펫"); ws.cell(row=row, column=3, value="M2")
    ws.cell(row=row, column=4, value=0); ws.cell(row=row, column=5, value=0).font = GREEN
    ws.cell(row=row, column=6, value=boq[code]).font = BLUE
    ws.cell(row=row, column=8, value=f"=D{row}-F{row}")
    ws.cell(row=row, column=9, value="도면 범례·MATERIAL LIST에 없는 코드. 내역 CT 번호 체계가 도면과 달라(내역 CT-01 101㎡ < 도면 CT-01인 B1 대회의실 135㎡) 코드별 대조 불가 → 아래 종류별 대조 참고")
    row += 1
tot = row
ws.cell(row=tot, column=1, value="바닥 마감 소계").font = BB
for col in (4, 5, 6):
    L = get_column_letter(col); ws.cell(row=tot, column=col, value=f"=SUM({L}5:{L}{tot-1})").font = BB
ws.cell(row=tot, column=7, value=f"=(D{tot}-E{tot})/E{tot}"); ws.cell(row=tot, column=8, value=f"=D{tot}-F{tot}")
ws.cell(row=tot, column=9, value="참고: 내역서 '기존면바탕정리(바닥)' 1,324㎡ ≈ 바닥재 합 1,323㎡ → 내역 수량은 정미량")
bb = tot + 1
ws.cell(row=bb, column=1, value="걸레받이 설치 - MDF+인테리어필름"); ws.cell(row=bb, column=2, value="T=9, H=30 (내역서 규격)"); ws.cell(row=bb, column=3, value="M")
ws.cell(row=bb, column=4, value=f"=SUM(산출근거서!$H${r0}:$H${last})"); ws.cell(row=bb, column=6, value=765).font = BLUE
ws.cell(row=bb, column=8, value=f"=D{bb}-F{bb}")
ws.cell(row=bb, column=9, value="미해결: AI 산출이 내역 대비 약 -40%. 열린 사무실·복도 둘레, 가구 뒤, 기둥 둘레 처리 기준 확인 필요")
for r in range(5, bb + 1):
    for c in range(1, 10):
        cell = ws.cell(row=r, column=c); cell.border = BOX
        if cell.font.name != F:
            cell.font = Font(name=F, bold=cell.font.bold, color=cell.font.color)
        cell.alignment = Alignment(vertical="center", wrap_text=(c in (2, 9)))
    for c in (4, 5, 6, 8):
        ws.cell(row=r, column=c).number_format = "#,##0.0"
    ws.cell(row=r, column=7).number_format = "0.0%"
    ws.row_dimensions[r].height = 30

cat0 = bb + 2
ws.cell(row=cat0, column=1, value="자재 종류별 대조 (코드 번호 체계 차이를 피해서 비교)").font = BB
header_row = cat0 + 1
for i, c in enumerate(["종류", "", "단위", "AI 산출", "도면 기준(벡터)", "내역서", "AI-도면 오차", "도면-내역 차이", "해석"], 1):
    cell = ws.cell(row=header_row, column=i, value=c); cell.font = H; cell.fill = HF; cell.border = BOX
CAT = [("DE 디럭스타일", ["DE-01"], "도면이 7㎡ 많음 - 태그 해석 차이(2F 금고 P-TILE 문구 등)"),
       ("DT 데코타일", ["DT-01", "DT-02", "DT-03"], "내역이 103㎡ 많음 - 무코드 실·미표기 구역 포함 추정"),
       ("CT 타일카펫", ["CT-01", "CT-02", "CT-03", "CT-04", "CT-05"], "내역이 29㎡ 많음 - 창측 띠/단상 처리 차이 추정")]
for k, (nm, codes, why) in enumerate(CAT):
    rr = header_row + 1 + k
    ws.cell(row=rr, column=1, value=nm); ws.cell(row=rr, column=3, value="M2")
    rows_ = [5 + list(ITEM).index(c) if c in ITEM else 5 + len(ITEM) + ["CT-04", "CT-05"].index(c) for c in codes]
    for col in (4, 5, 6):
        L = get_column_letter(col); ws.cell(row=rr, column=col, value="=" + "+".join(f"{L}{x}" for x in rows_))
    ws.cell(row=rr, column=7, value=f"=(D{rr}-E{rr})/E{rr}"); ws.cell(row=rr, column=8, value=f"=F{rr}-E{rr}")
    ws.cell(row=rr, column=9, value=why)
    for c in range(1, 10):
        cell = ws.cell(row=rr, column=c); cell.border = BOX; cell.font = Font(name=F); cell.alignment = Alignment(vertical="center", wrap_text=(c == 9))
    for c in (4, 5, 6, 8): ws.cell(row=rr, column=c).number_format = "#,##0.0"
    ws.cell(row=rr, column=7).number_format = "0.0%"; ws.row_dimensions[rr].height = 30

# ---------------- 검토 필요 ----------------
ws3 = wb.create_sheet("검토 필요")
ws3["A1"] = "견적팀·발주처에 확인할 항목 (AI가 혼자 결정하면 안 되는 경계)"; ws3["A1"].font = Font(name=F, bold=True, size=13)
header(ws3, 3, ["#", "항목", "근거", "수량 영향", "질문"], [4, 26, 60, 18, 50])
Q = [
 ("창측 띠(FCU 박스 구간) 포함 여부", "치수선이 창 앞에서 끝나고 555/450/439mm 띠가 별도 기재. AI가 처음엔 이 띠를 빠뜨려 창가 회의실·임원실 8곳이 10~19% 작게 나옴", "+61.1㎡ (2F 31.4, 3F 29.8)", "FCU 박스 하부까지 바닥재를 까나요, 박스 앞에서 끊나요?"),
 ("내역 코드 번호 ≠ 도면 범례 번호", "도면에는 CT-01~03만 있는데 내역에는 CT-01~05. 내역 CT-01(101㎡)이 도면 CT-01 실(B1 대회의실 135㎡ 단독)보다 작음 → 번호 체계가 다름", "코드별 대조 불가", "내역 CT-01~05가 각각 어느 실인지 매핑표가 있나요?"),
 ("데코타일 면적 차이 +103㎡", "도면에서 코드가 붙은 DT 면적 760㎡ vs 내역 863㎡. 후보: 태그 없이 문구만 있는 실, 서버실·INFO·O.A ROOM 등 무코드 실, B1 미표기 구역", "+103㎡", "코드 태그가 없는 실(서버실 등)도 데코타일로 산출하나요?"),
 ("태그 없는 실의 마감 문구", "B1 기사대기실 '~DELUXE TILE FIN.', 2F 직원휴게실 '~DECO TILE FIN.' 등 코드 태그 없이 문구만 있음", "약 21㎡", "문구만 있는 실도 해당 코드로 산출하나요?"),
 ("단상(우드플로링) 하부", "B1 다목적 대회의실 단상 6000x1200 - 내역에 '단상설치 1EA' 별도", "-7.2㎡ (CT-01)", "단상 하부에 카펫을 깔지 않는 게 맞나요?"),
 ("규격 불일치 DE-01", "내역 300x300 ↔ 도면 범례 450x450", "단가 영향", "최종 규격은 어느 쪽인가요?"),
 ("규격 불일치 DT-01", "내역 450x450 ↔ MATERIAL LIST 600x600 T5", "단가 영향", "최종 규격은 어느 쪽인가요?"),
 ("폴딩도어 구간 걸레받이", "이동식 칸막이 하부는 벽이 아니므로 제외로 처리", "수 m", "폴딩도어 하부 걸레받이 처리 기준은?"),
 ("걸레받이 총량 차이", "AI 460m vs 내역 765m. 열린 사무실 외곽·기둥 둘레·가구 뒤 처리 기준이 다른 것으로 추정", "-305m", "기둥 둘레와 붙박이 가구 뒤에도 걸레받이를 넣나요?"),
]
for i, q in enumerate(Q, 1):
    for c, v in enumerate((i,) + q, 1):
        cell = ws3.cell(row=3 + i, column=c, value=v); cell.font = B; cell.alignment = WRAP; cell.border = BOX
    ws3.row_dimensions[3 + i].height = 45

# ---------------- 실험 기록 ----------------
ws4 = wb.create_sheet("실험 기록")
ws4["A1"] = "하네스 실험 기록 - 같은 도면, 같은 모델, 지시·도구만 바꿔 6회 실행"; ws4["A1"].font = Font(name=F, bold=True, size=13)
header(ws4, 3, ["버전", "바꾼 것", "실 단위 평균오차", "±5% 이내 실", "근거 있는 면적 비율", "합계 오차(도면 기준)"], [8, 50, 16, 12, 18, 18])
DESC = {"v1": "도면 4장 주고 '물량 산출해줘'", "v2": "실별 표 형식 + 근거·신뢰도 기재 강제", "v3": "입력 추가: 치수 도면 + 고해상도 4분할 타일, 적힌 숫자만 사용",
        "v4": "견적 실무 규칙 R1~R7 (안목, 기둥 공제, 이중계산 금지, 정미량, 층별 검산)", "v5": "검토자 에이전트가 v4를 도면과 대조해 수정",
        "v6": "검증 데이터에서 찾은 오차 패턴(창측 띠) 규칙 추가"}
for i, s in enumerate(sc["versions"], 4):
    vals = [s["version"], DESC[s["version"]], (s["room_mape"] / 100) if s["room_mape"] is not None else "채점 불가(근거 없음)",
            f'{s["room_within5"]}/19', s["traceable_share"] / 100, s["total_err_vs_drawing"] / 100]
    for c, v in enumerate(vals, 1):
        cell = ws4.cell(row=i, column=c, value=v); cell.font = B; cell.border = BOX; cell.alignment = WRAP
    for c in (3, 5, 6):
        ws4.cell(row=i, column=c).number_format = "0.0%"
ws4.cell(row=11, column=1, value="주의: v6 규칙은 검증 세트(19실)의 오차를 보고 찾았고 같은 세트로 평가했으므로 낙관적일 수 있음. 공사 1건·버전별 1회 실행.").font = Font(name=F, italic=True, color="666666")

out = ROOT / "site/assets/산출근거서_대한변협신회관_바닥마감.xlsx"
wb.save(out); print(out)
