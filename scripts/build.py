#!/usr/bin/env python3
"""municipalities/*/<name>.yaml（正本）→ docs/（配信物）

生成物:
  docs/<slug>/v1/courses.json   アプリが読む形式（YAMLとほぼ同じ構造、JSON）
  docs/<slug>/ics/<course>.ics  コース別 iCalendar（規則 RRULE + 例外日 EXDATE）
  docs/<slug>/ics/index.csv     町名 → コース → ics パス
  docs/index.json               自治体一覧

使い方: python scripts/build.py
"""
import csv
import datetime as dt
import hashlib
import json
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = {  # slug → yaml
    "saitama": "municipalities/111007_saitama/saitama.yaml",
}
WD = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]


def ics_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;")


def build_ics(doc, course, out_path, generated):
    muni = doc["municipality"]["name"]
    cat_names = {c["id"]: c["name"] for c in doc["categories"]}
    exdates = [d.replace("-", "") for d in doc.get("exceptions", [])]
    # DTSTART は version の年度開始日（4/1）以降、最初の該当曜日
    y, m = (int(x) for x in doc["version"].split("-"))
    start = dt.date(y, m, 1)
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//gomi-data//JP", "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{muni} ごみ収集 {course['ward']} {course['id']}", "X-WR-TIMEZONE:Asia/Tokyo",
    ]
    areas = "、".join(a["name"] for a in course["areas"])
    for cid, days in course["schedule"].items():
        if not days:
            continue
        byday = ",".join(WD[d - 1] for d in days)
        first = start
        while WD[first.weekday()] not in byday.split(","):
            first += dt.timedelta(days=1)
        uid = hashlib.md5(f"{doc['municipality']['code']}-{course['id']}-{cid}".encode()).hexdigest()
        summary = cat_names.get(cid, cid)
        if course.get("earlyMorning") and cid == "burnable":
            summary += f"（早朝 {doc['rules']['earlyMorningPutOutBy']}まで）"
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}@gomi-data",
            f"DTSTAMP:{generated}T000000Z",
            f"DTSTART;VALUE=DATE:{first.strftime('%Y%m%d')}",
            f"RRULE:FREQ=WEEKLY;BYDAY={byday}",
        ]
        if exdates:
            lines.append("EXDATE;VALUE=DATE:" + ",".join(exdates))
        lines += [
            f"SUMMARY:{ics_escape(summary)}",
            f"DESCRIPTION:{ics_escape(f'対象: {areas} / {doc['rules']['putOutBy']}までに / 出典: {doc['source']['title']}')}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        f.write("\r\n".join(lines) + "\r\n")


def main():
    generated = dt.date.today().strftime("%Y%m%d")
    index = []
    for slug, rel in SOURCES.items():
        doc = yaml.safe_load(open(os.path.join(ROOT, rel), encoding="utf-8"))
        out = os.path.join(ROOT, "docs", slug)
        os.makedirs(os.path.join(out, "v1"), exist_ok=True)
        os.makedirs(os.path.join(out, "ics"), exist_ok=True)

        payload = dict(doc)
        payload["generatedAt"] = dt.date.today().isoformat()
        with open(os.path.join(out, "v1", "courses.json"), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

        # 古い ics を消してから作り直す
        for name in os.listdir(os.path.join(out, "ics")):
            os.remove(os.path.join(out, "ics", name))
        rows = []
        for c in doc["courses"]:
            path = f"ics/{c['id']}.ics"
            build_ics(doc, c, os.path.join(out, path), generated)
            for a in c["areas"]:
                rows.append([c["ward"], a["name"], c["id"], a.get("note", ""), path])
        with open(os.path.join(out, "ics", "index.csv"), "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["区", "町名", "コースID", "注記", "ics"])
            w.writerows(rows)

        index.append({
            "slug": slug,
            "code": doc["municipality"]["code"],
            "name": doc["municipality"]["name"],
            "prefecture": doc["municipality"]["prefecture"],
            "version": doc["version"],
            "courses": len(doc["courses"]),
            "areas": len(rows),
            "json": f"{slug}/v1/courses.json",
        })
        print(f"{slug}: version={doc['version']} courses={len(doc['courses'])} areas={len(rows)}")

    with open(os.path.join(ROOT, "docs", "index.json"), "w", encoding="utf-8") as f:
        json.dump({"generatedAt": dt.date.today().isoformat(), "municipalities": index}, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    sys.exit(main())
