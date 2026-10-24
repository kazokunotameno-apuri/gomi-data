#!/usr/bin/env python3
"""さいたま市: マニュアル p.18-19 のテキスト層 → municipalities/111007_saitama/saitama.yaml

入力はPDFから抽出したテキスト（1トークン1行）。抽出のしかたは README を参照。
列の対応（町名 → もえるごみ → もえないごみ等 → 資源物1類）は、区ごとに
「町名N件・もえるごみN件・単一曜日2N件」が並ぶ構造を使って件数一致で決める。

使い方:
  python scripts/extract_saitama.py municipalities/111007_saitama/raw/r8_manual_p18-19.txt \
      --version 2026-04 --source-url <PDFのURL> --source-title "..." \
      -o municipalities/111007_saitama/saitama.yaml
"""
import argparse
import re
import sys
from collections import Counter

import yaml

DAYS = "月火水木金土"
JP2INT = {"月": 1, "火": 2, "水": 3, "木": 4, "金": 5, "土": 6, "日": 7}
# PDF上の出現順（区ブロックの順）。マニュアルのレイアウトが変わったらここを直す
BLOCK_WARDS = ["岩槻区", "西区", "中央区", "大宮区", "見沼区", "桜区", "浦和区", "北区", "南区", "緑区"]
CATEGORIES = [
    {"id": "burnable", "name": "もえるごみ"},
    {"id": "nonburnable", "name": "もえないごみ・有害危険ごみ・資源物2類"},
    {"id": "recyclable1", "name": "資源物1類（びん・かん・ペット・プラ）"},
]
NOTE_KEYWORDS = ["線路より", "大部分", "一部", "イーストシティ", "旧指扇", "飛地"]


def classify(t: str) -> str:
    if re.fullmatch(r"[月火水木金土]・[月火水木金土]", t):
        return "burn"
    if t in DAYS:
        return "single"
    if re.fullmatch(r"[ぁ-ん]", t):
        return "kana"
    if "▼" in t or "清掃事務所" in t or (len(t) == 1 and t in "区西東槻央沼和宮"):
        return "marker"
    return "town"


def parse(lines):
    runs = []
    for t in lines:
        c = classify(t)
        if runs and runs[-1][0] == c:
            runs[-1][1].append(t)
        else:
            runs.append([c, [t]])

    pending_towns, pending_values, records, errors = [], [], [], []
    ward_idx = 0
    i = 0
    while i < len(runs):
        c, toks = runs[i]
        if c == "town":
            pending_towns.extend(toks)
        elif c == "burn":
            n = len(toks)
            if i + 1 < len(runs) and runs[i + 1][0] == "single" and len(runs[i + 1][1]) == 2 * n:
                s = runs[i + 1][1]
                pending_values.append((n, toks, s[:n], s[n:]))
                i += 1
            else:
                errors.append(f"burn run of {n} at run {i} not followed by {2*n} singles")
        while pending_values and pending_towns:
            n, b, u, r = pending_values[0]
            if len(pending_towns) < n:
                break
            towns, pending_towns = pending_towns[:n], pending_towns[n:]
            pending_values.pop(0)
            if ward_idx >= len(BLOCK_WARDS):
                errors.append("more blocks than wards")
                break
            ward = BLOCK_WARDS[ward_idx]
            ward_idx += 1
            for k in range(n):
                name = towns[k]
                m = re.match(r"(★\d)\s*(.*)", name)
                mark, name = (m.group(1), m.group(2)) if m else ("", name)
                name = name.replace("　", "").strip()
                records.append({
                    "ward": ward, "area": name, "mark": mark,
                    "burnable": [JP2INT[d] for d in b[k].split("・")],
                    "nonburnable": [JP2INT[u[k]]],
                    "recyclable1": [JP2INT[r[k]]],
                    "early_morning": mark == "★1",
                })
        i += 1
    if pending_towns or pending_values:
        errors.append(f"leftover towns={len(pending_towns)} values={len(pending_values)}")
    return records, errors


def to_courses(records):
    groups = {}
    for r in records:
        key = (r["ward"], tuple(r["burnable"]), tuple(r["nonburnable"]), tuple(r["recyclable1"]), r["early_morning"])
        groups.setdefault(key, []).append(r)
    courses, counter = [], Counter()
    for key, rs in sorted(groups.items()):
        ward = key[0]
        counter[ward] += 1
        areas = []
        for r in rs:
            a = {"name": r["area"]}
            if r["mark"]:
                a["mark"] = r["mark"]
            if any(k in r["area"] for k in NOTE_KEYWORDS) or r["mark"] == "★3":
                a["note"] = "要確認"
            areas.append(a)
        courses.append({
            "id": f"{ward}-{counter[ward]:02d}",
            "ward": ward,
            "earlyMorning": key[4],
            "schedule": {"burnable": list(key[1]), "nonburnable": list(key[2]), "recyclable1": list(key[3])},
            "areas": areas,
        })
    return courses


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--version", required=True, help="例: 2026-04（年度の開始月）")
    ap.add_argument("--source-url", required=True)
    ap.add_argument("--source-title", required=True)
    ap.add_argument("--retrieved", required=True, help="YYYY-MM-DD")
    ap.add_argument("--exceptions", default="", help="休止日 YYYY-MM-DD をカンマ区切り")
    args = ap.parse_args()

    lines = [l.strip() for l in open(args.raw, encoding="utf-8")]
    lines = [l for l in lines if l]
    records, errors = parse(lines)
    if errors:
        print("ERROR:", errors, file=sys.stderr)
        sys.exit(1)
    courses = to_courses(records)
    doc = {
        "schema": 1,
        "municipality": {"code": "111007", "name": "さいたま市", "prefecture": "埼玉県"},
        "version": args.version,
        "source": {
            "title": args.source_title,
            "url": args.source_url,
            "retrieved": args.retrieved,
            "license": "出典明記。さいたま市サイトの利用規約に準拠（オープンデータライセンスは市に確認中）",
            "method": "PDFテキスト層から抽出し、区ごとの件数一致で列を対応付け。収集運搬委託仕様書と独立照合",
        },
        "rules": {
            "holidaysCollected": True,
            "putOutBy": "08:30",
            "earlyMorningPutOutBy": "05:30",
            "dictionaryUrl": "https://www.city.saitama.lg.jp/001/006/010/003/p042612.html?page=dictionary",
            "notes": [
                "★1 もえるごみ早朝地区（北浦和1・3丁目は一部のみ）",
                "★2 旧指扇地区の範囲は市サイト参照",
                "★3 収集所の場所と曜日は近隣・自治会に確認",
                "丁目の境など、一部表と異なる収集所がある",
                "南区大谷口は大字・飛地・イーストシティの3区分",
            ],
        },
        "exceptions": [e.strip() for e in args.exceptions.split(",") if e.strip()],
        "categories": CATEGORIES,
        "courses": courses,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False, width=200)
    print(f"areas={len(records)} courses={len(courses)} wards={Counter(r['ward'] for r in records)}")


if __name__ == "__main__":
    main()
