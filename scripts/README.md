# scripts

도면 PDF에서 실험 입력과 실측 기준을 만드는 스크립트입니다. Python 3.13, PyMuPDF, OpenCV, SciPy, NumPy.

- 원본 도면은 저장소에 없습니다. [발주처 공고](https://www.koreanbar.or.kr/pages/news/view.asp?page=1&seq=12337&types=1)에서 `03 ... 기본도면.pdf`를 받아 `data/raw_kba/plan.pdf`로 두세요.
- 작업 폴더는 환경변수 `CONPA_ROOT`로 지정합니다(기본값: 저장소 루트). 결과는 `out/`에 생깁니다.

| 파일 | 하는 일 |
|---|---|
| `make_inputs.py` | 마감·치수 평면도를 overview + 4분할 타일 이미지로 렌더링 (AI 입력) |
| `vector/measure_rooms.py` | 경계 레이어 래스터화 → 실 이름 위치에서 flood fill → 안목 면적·둘레 |
| `vector/build_reference.py` | 열린 공간을 마감 태그 기준으로 분할, `vector_reference.json`과 오버레이 생성 |
| `vector/export_3d.py` | 실측 영역 폴리곤과 벽·창호 선분을 웹 3D용 `scene.json`으로 추출 |
| `vector/probe_*.py`, `layer_view.py`, `style_view.py` | 레이어·축척 조사용 |
