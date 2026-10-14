"""채점기 회귀 테스트: 정답 데이터·채점 규칙·공개된 점수가 서로 맞는지 확인한다."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness"))
import score  # noqa: E402

PUBLISHED = json.loads((ROOT / "harness/scores.json").read_text())


def test_validation_set_is_19_closed_rooms():
    assert len(score.VALID) == 19
    assert all(r["kind"] == "closed" and r["code"] for r in score.VALID.values())


@pytest.mark.parametrize("raw, expected", [
    ("장고", "창고"),                      # 도면 OCR 오타 보정
    ("바서", "비서"),
    ("다목적 대회의실 (배석)", "다목적대회의실"),  # 괄호 설명 제거
    ("법률구조재단 배석판사실", "법률구조재단"),    # '배석' 이후 제거
])
def test_norm(raw, expected):
    assert score.norm(raw) == expected


def test_executive_lounge_kept_separate_from_meeting_room_1():
    assert score.room_key("3F", "중회의실(임원휴게실)") == ("3F", "중회의실임원휴게실")
    assert score.room_key("3F", "중회의실-1") != score.room_key("3F", "중회의실(임원휴게실)")


@pytest.mark.parametrize("v", score.VERSIONS)
def test_scores_reproduce_published_numbers(v):
    """README·결과 페이지에 적은 숫자가 지금 코드로 다시 나오는지."""
    pub = next(s for s in PUBLISHED["versions"] if s["version"] == v)
    got = score.score_version(v)
    for key in ("room_mape", "room_within5", "room_coverage", "total_err_vs_drawing", "traceable_share"):
        assert got[key] == pub[key], (v, key, got[key], pub[key])


def test_headline_claims():
    v2, v6 = (score.score_version(v) for v in ("v2", "v6"))
    assert (v2["room_mape"], v6["room_mape"]) == (16.3, 4.3)
    assert v6["room_within5"] == 13


def test_within5_uses_unrounded_ratio():
    """±5% 판정은 반올림 전 값으로 한다. 반올림한 오차(%)로 세면 경계의 실이 하나 더 통과해 14가 된다."""
    m = score.score_version("v6")["room_matches"]
    strict = sum(abs(x["ai"] - x["ref"]) / x["ref"] <= 0.05 for x in m)
    rounded = sum(abs(x["err_pct"]) <= 5.0 for x in m)
    assert strict == 13
    assert rounded == 14


def test_truth_totals():
    assert round(sum(score.VEC["by_code_total"].values()), 2) == 1197.58
    assert sum(score.BOQ["by_code"].values()) == 1323
