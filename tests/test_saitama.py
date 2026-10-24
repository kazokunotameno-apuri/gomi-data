"""saitama.yaml の整合性テスト（pytest）"""
import json
import os
import re

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YAML = os.path.join(ROOT, "municipalities/111007_saitama/saitama.yaml")
JSON = os.path.join(ROOT, "docs/saitama/v1/courses.json")


def load():
    return yaml.safe_load(open(YAML, encoding="utf-8"))


def test_counts():
    d = load()
    assert len(d["courses"]) == 77
    areas = [a for c in d["courses"] for a in c["areas"]]
    assert len(areas) == 322
    by_ward = {}
    for c in d["courses"]:
        by_ward[c["ward"]] = by_ward.get(c["ward"], 0) + len(c["areas"])
    assert by_ward == {"岩槻区": 71, "見沼区": 36, "浦和区": 36, "緑区": 35, "西区": 33,
                       "南区": 30, "大宮区": 26, "桜区": 25, "北区": 17, "中央区": 13}


def test_schedule_shape():
    d = load()
    for c in d["courses"]:
        s = c["schedule"]
        assert len(s["burnable"]) == 2, c["id"]          # もえるごみは週2回
        assert len(s["nonburnable"]) == 1, c["id"]
        assert len(s["recyclable1"]) == 1, c["id"]
        assert tuple(s["burnable"]) in {(1, 4), (2, 5), (3, 6)}, c["id"]  # 月木/火金/水土
        assert all(1 <= x <= 6 for v in s.values() for x in v), c["id"]  # 日曜収集なし
        assert s["nonburnable"][0] != s["recyclable1"][0], c["id"]
        assert s["nonburnable"][0] not in s["burnable"], c["id"]
        assert s["recyclable1"][0] not in s["burnable"], c["id"]


def test_unique_area_names_within_ward():
    d = load()
    seen = set()
    for c in d["courses"]:
        for a in c["areas"]:
            key = (c["ward"], a["name"])
            assert key not in seen, key
            seen.add(key)


def test_known_values():
    d = load()
    idx = {(c["ward"], a["name"]): c for c in d["courses"] for a in c["areas"]}
    assert idx[("西区", "宝来")]["schedule"] == {"burnable": [2, 5], "nonburnable": [1], "recyclable1": [4]}
    assert idx[("浦和区", "常盤1・2丁目")]["earlyMorning"] is True
    assert idx[("浦和区", "前地1～3丁目")]["schedule"]["recyclable1"] == [3]
    assert idx[("緑区", "大崎")]["schedule"] == {"burnable": [2, 5], "nonburnable": [4], "recyclable1": [1]}


def test_early_morning_only_in_station_wards():
    d = load()
    early = {c["ward"] for c in d["courses"] if c["earlyMorning"]}
    assert early == {"大宮区", "浦和区", "南区"}


def test_exceptions_are_dates():
    d = load()
    for e in d["exceptions"]:
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", e), e


def test_docs_in_sync():
    """docs/ は build.py の出力と一致していなければならない（CIで検出）"""
    assert os.path.exists(JSON), "run: python scripts/build.py"
    d = load()
    j = json.load(open(JSON, encoding="utf-8"))
    assert j["version"] == d["version"]
    assert [c["id"] for c in j["courses"]] == [c["id"] for c in d["courses"]]
    for c in d["courses"]:
        assert os.path.exists(os.path.join(ROOT, "docs/saitama/ics", f"{c['id']}.ics")), c["id"]
