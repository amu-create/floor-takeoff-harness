import json
p="site/template.html"; s=open(p).read()
R=[
("실제 공공 인테리어 공사의 도면 133장으로 바닥재 물량을 AI에게 산출시키고, 같은 모델·같은 도면에서 지시와 도구만 바꿔 6번 돌렸습니다. 방 19개를 PDF 속 CAD 벡터로 직접 측정해 채점했습니다.",
 "실제 공공 인테리어 공사의 도면(133장 중 7장)으로 바닥재 물량을 AI에게 산출시키고, 같은 모델로 지시·도구·입력 해상도를 단계적으로 바꿔 6번 돌렸습니다. 방 19개를 PDF 속 CAD 벡터로 직접 측정해 채점했습니다."),
("v2(표 형식만) → v6(타일 판독 + 실무 규칙 + 검토자 + 오차 패턴 규칙)","v2(표 형식만) → v6(고해상도 타일·치수 도면 + 실무 규칙 + 오차 패턴 규칙)"),
('<span class="n"><s>6</s> → 14 / 19</span>','<span class="n"><s>6</s> → 13 / 19</span>'),
('<span class="label">숫자 근거가 붙은 면적</span><span class="n"><s>0%</s> → 68%</span><span class="d">v1은 합계만 내서 검증 불가</span>',
 '<span class="label">AI가 신뢰도 중 이상으로 표기한 면적</span><span class="n"><s>34%</s> → 68%</span><span class="d">v2 대비 v6 · v1은 합계만 내서 검증 불가</span>'),
('<th class="num">근거 면적</th>','<th class="num">신뢰 중↑ 면적</th>'),
("축척은 치수 4곳으로 교차 확인했고 서로 0.04% 안에서 맞았습니다.","축척은 층마다 치수 4곳으로 교차 확인했고 0.07% 안에서 맞았습니다(3층은 2층과 같은 치수 사용)."),
('alt="2층 소회의실 치수: 실 깊이 3390 뒤에 창까지 555 띠가 따로 적혀 있음"','alt="2층 소회의실 치수: 실 깊이 치수선 뒤에 창까지 555 띠가 따로 적혀 있음"'),
("<q>창가 방이 전부 10~18% 작게 나왔다. 실 깊이 3390 뒤에, 창까지 555mm 띠가 따로 적혀 있었다.</q>",
 "<q>창가 회의실·임원실 8곳이 10~19% 작게 나왔다. 실 깊이 치수선 뒤에, 창까지 555mm 띠가 따로 적혀 있었다.</q>"),
("AI는 실 치수선만 읽고 창 앞 FCU 박스 구간을 빠뜨렸습니다. 이 띠는 층마다 30㎡ 정도입니다.",
 "AI는 실 치수선만 읽고 창 앞 FCU 박스 구간을 빠뜨렸습니다. 이 띠는 2층·3층에서 각각 약 30㎡(합 61㎡)입니다. 정책조정실·접견실은 원래 오차가 작아서 띠를 더한 뒤 오히려 4~6% 커졌습니다."),
("손실 할증은 수량이 아니라 일위대가 쪽에 들어가 있다는 뜻이라, AI에게 정미량으로 내라고 지시했습니다.",
 "손실 할증은 수량이 아니라 일위대가 쪽에 들어가 있는 것으로 보여서, AI에게 정미량으로 내라고 지시했습니다."),
("<p>v2·v3는 작은 글씨를 잘못 읽었습니다. 4분할 고해상도 타일로 바꾼 v4부터 사라졌습니다. 도면 한 장을 통째로 보여주면 치수 숫자도 같은 식으로 틀립니다.</p>",
 "<p>v2·v3에서 지하 \"창고\"를 \"장고\"로 읽었고 v4부터 사라졌습니다. 타일은 v3부터 줬기 때문에 정확한 원인은 아직 확인하지 못했습니다. 실 이름 하나 틀린 것이지만, 같은 방식으로 치수 숫자가 틀리면 수량이 바로 틀어집니다.</p>"),
("<p>지하 기사대기실, 2층 직원휴게실은 코드 태그 없이 \"DECO TILE FIN.\" 같은 문구만 있습니다. v4는 임의로 코드를 붙였고, v5 검토자가 규칙 위반으로 걷어냈습니다. 약 21㎡가 이 판단에 걸려 있습니다.</p>",
 "<p>2층 직원휴게실은 코드 태그 없이 \"DECO TILE FIN.\" 문구만 있습니다. v4는 이런 실 3곳(직원휴게실·대회협력실·탕비 구역)에 임의로 코드를 붙였고, v5 검토자가 규칙 위반으로 걷어냈습니다(약 48㎡). 지하 기사대기실은 문구만 있는데도 DE-01로 남아 있어 확인이 필요합니다.</p>"),
("<p>지하 대회의실의 우드플로링 단상(6000×1200)은 내역에 단상설치 1EA로 따로 잡혀 있습니다. AI는 카펫 면적에서 이 부분을 뺐고, 실측 기준과의 −8%는 대부분 이 공제입니다.</p>",
 "<p>지하 대회의실의 우드플로링 단상은 내역에 단상설치 1EA(6000×1200 = 7.2㎡)로 따로 잡혀 있습니다. AI는 도면 비례로 약 9.4㎡를 카펫 면적에서 뺐고, 실측 기준과의 −8%는 대부분 이 공제입니다.</p>"),
("<li><b>표본이 작습니다.</b>","<li><b>실측 기준에도 오차가 있습니다.</b> 10㎡ 넘는 방은 ±1~2%, 작은 방은 더 큽니다. 지하 서고·법률구조재단은 앞쪽 통로가 섞여 2~4㎡ 클 수 있어서, 이 방들은 ±5% 판정 자체가 빠듯합니다.</li>\n    <li><b>표본이 작습니다.</b>"),
("<li><b>v6 규칙은 검증 세트에서 찾았습니다.</b> 같은 세트로 평가했으니 4.3%는 낙관적인 숫자입니다.","<li><b>v6 규칙은 검증 세트에서 찾았습니다.</b> 같은 세트로 평가했으니 4.3%는 낙관적인 숫자입니다. v1·v2는 도면 4장만 받았고 v3부터 치수 도면과 타일이 더해졌으니, 개선에는 입력 변화도 섞여 있습니다."),
('v3:"고해상도 4분할 타일 + 치수 도면, 적힌 숫자만"','v3:"입력 추가: 치수 도면 + 고해상도 4분할 타일, 적힌 숫자만"'),
('v5:"검토자 에이전트가 도면과 대조해 수정"','v5:"검토자 에이전트가 대조 (방 정확도는 그대로, 규칙 위반·걸레받이 정리)"'),
]
for a,b in R:
    if a in s: s=s.replace(a,b)
    elif b not in s: raise SystemExit("MISSING: "+a[:50])
open(p,"w").write(s)
sc=json.load(open("harness/scores.json"))
vers=[{k:x[k] for k in ("version","room_mape","room_within5","traceable_share","total_err_vs_drawing")} for x in sc["versions"]]
rooms=json.load(open("site/rooms.json"))
open("site/index.html","w").write(s.replace("__VERSIONS__",json.dumps(vers,ensure_ascii=False)).replace("__ROOMS__",json.dumps(rooms,ensure_ascii=False)))
print("built")

# ---- 3D 섹션 삽입 ----
html = open("site/index.html").read()
sec = open("site/three_section.html").read()
app = open("site/three_app.js").read().replace("__SCENE__", open("site/scene.json").read())
for a, b in [('<span class="label">03 · 찾아낸 것</span>', '<span class="label">04 · 찾아낸 것</span>'),
             ('<span class="label">04 · 도면 vs 내역서</span>', '<span class="label">05 · 도면 vs 내역서</span>'),
             ('<span class="label">05 · 아직 못 푼 것</span>', '<span class="label">06 · 아직 못 푼 것</span>'),
             ('<span class="label">06 · 하네스 구조</span>', '<span class="label">07 · 하네스 구조</span>'),
             ('<span class="label">07 · 입사하면 첫 2주</span>', '<span class="label">08 · 입사하면 첫 2주</span>')]:
    html = html.replace(a, b)
html = html.replace('<section id="finds">', sec + '\n<section id="finds">', 1)
html = html.replace("const ROOMS = ", "const ROOMS = window.ROOMS_DATA = ", 1)
CDN = ('<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>\n'
       '<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>\n')
tail = "\n" + CDN + "<script>\n" + app + "\n</script>\n"
open("site/index.html", "w").write(html + tail)
S = "/tmp/claude-0/-home-claude/e6d269e6-a8f4-55ff-9b01-b7c6d89ef12a/scratchpad"
local = (html + tail).replace("https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js", f"file://{S}/npm/package/build/three.min.js") \
    .replace("https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js", f"file://{S}/npm/package/examples/js/controls/OrbitControls.js")
open("site/_preview.html", "w").write("<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'><style>img{max-width:100%}[hidden]{display:none!important}body{margin:0}</style></head><body>" + local + "</body></html>")
print("3d inserted", len(html + tail))
