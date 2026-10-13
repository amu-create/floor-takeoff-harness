"""artifact용 site/index.html -> Vercel용 단독 페이지(dist/) 생성"""
import shutil, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
SITE_URL = os.environ.get("SITE_URL", "https://floor-takeoff-harness.vercel.app")
REPO = "https://github.com/amu-create/floor-takeoff-harness"
XLSX = "산출근거서_대한변협신회관_바닥마감.xlsx"
html = (ROOT / "site/index.html").read_text()
title = "변협 신회관 바닥 물량 실험"
desc = "실제 공공 인테리어 공사 도면으로 AI 바닥재 물량산출을 6번 개선하고 CAD 벡터 실측으로 채점한 실험 노트. 방 단위 오차 16.3% → 4.3%."
head = f"""<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="{desc}">
<meta property="og:type" content="website"><meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}"><meta property="og:image" content="{SITE_URL}/og.png">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:url" content="{SITE_URL}/">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' fill='%230D6A61'/%3E%3Cpath d='M7 25V7h18v18zM7 16h9V7' fill='none' stroke='white' stroke-width='2.5'/%3E%3C/svg%3E">
<style>html{{color-scheme:light}}body{{margin:0}}img{{max-width:100%}}[hidden]{{display:none!important}}:root{{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}</style>
"""
old_note = '산출근거서 엑셀(공종별집계 · 실별 산출근거 · 검토 필요 항목 · 실험 기록)은 메일에 첨부했습니다. 모든 합계는 실별 행에서 수식으로 계산됩니다.'
assert old_note in html
html = html.replace(old_note, f'<a href="files/floor_takeoff_basis.xlsx" download="{XLSX}">산출근거서 엑셀 받기</a> (공종별집계 · 실별 산출근거 · 검토 필요 항목 · 실험 기록). 모든 합계는 실별 행에서 수식으로 계산됩니다.')
old_foot = '<span>작업자 AI는 Claude Sonnet'
assert old_foot in html
html = html.replace(old_foot, f'<span><a href="{REPO}" target="_blank" rel="noopener">GitHub: 실험 지시문·결과·채점기 전체</a> · <a href="media/conpa_3d_tour.mp4">3D 투어 영상</a></span>\n  <span>작업자 AI는 Claude Sonnet', 1)
html = html.replace('<button class="m3-tour" id="m3tour" type="button">자동 둘러보기</button>', '<button class="m3-tour" id="m3tour" type="button">자동 둘러보기</button><a class="m3-dl" href="media/conpa_3d_tour.mp4">영상으로 보기 (27초)</a>')
html = html.replace(".m3-bar{display:flex;", ".m3-dl{font-family:var(--ff-mono);font-size:13px}\n.m3-bar{display:flex;")
if DIST.exists(): shutil.rmtree(DIST)
(DIST / "files").mkdir(parents=True); (DIST / "media").mkdir()
(DIST / "index.html").write_text(head + "</head><body>\n" + html + "\n</body></html>\n")
shutil.copytree(ROOT / "site/assets", DIST / "assets", ignore=shutil.ignore_patterns("*.xlsx"))
shutil.copy(ROOT / "site/assets" / XLSX, DIST / "files" / "floor_takeoff_basis.xlsx")
for f in ("conpa_3d_tour.mp4", "conpa_3d_tour.gif"): shutil.copy(ROOT / "site/media" / f, DIST / "media" / f)
shutil.copy(ROOT / "site/og.png", DIST / "og.png")
print("dist ready", sum(p.stat().st_size for p in DIST.rglob('*') if p.is_file()))
