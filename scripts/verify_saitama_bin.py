#!/usr/bin/env python3
"""独立資料との照合: さいたま市 びん収集運搬業務委託仕様書（桜・浦和・南・緑・大宮区, R8.4〜R16.3）別表の
資源物1類曜日と、saitama.yaml の recyclable1 を丁目単位で突き合わせる。

出典: https://www.city.saitama.lg.jp/005/001/017/006/003/p081629_d/fil/b.pdf
不一致が 1 件でもあれば終了コード 1。
"""
import os, re, sys
import yaml

BIN = {
"月": {"浦和区": "岸町1,2,3,4,5,6,7丁目|神明1,2丁目|高砂1,2,4丁目|常盤1,2,3,4,6,7,8丁目|仲町1,3,4丁目|東高砂町",
       "南区": "白幡2丁目|神明1,2丁目|大字太田窪|辻1,7,8丁目|文蔵1,2,3,4,5丁目|別所1,2,3,4,5,6,7丁目|南本町1,2丁目|大字円正寺|大字大谷口",
       "緑区": "大字大崎|大字上野田|大字北原|大字玄蕃新田|大字下野田|太田窪3丁目|大字大門|大字代山|大字高畑|大字寺山|大字中野田|大字南部領辻|東大門1,2,3丁目|大字間宮|美園1,2,3,4,5,6丁目"},
"火": {"桜区": "大字大久保領家|大字五関|桜田1,2,3丁目|大字神田|大字塚本|大字道場|道場1,2,3,4,5丁目|大字西堀|西堀1,2,3,4,5,6,7,8,9,10丁目|大字町谷|町谷1,2,3,4丁目|大字南元宿|南元宿1,2丁目",
       "浦和区": "東岸町|元町1,2,3丁目|本太1,2,3,4,5丁目",
       "南区": "関1,2丁目|太田窪2丁目|鹿手袋1,2,3,4,5,6,7丁目",
       "緑区": "太田窪1丁目"},
"水": {"桜区": "西堀ラミーユ浦和ハイライズ|大字新開|新開1,2,3,4丁目|大字田島|田島1,2,3,4,5,6,7,8,9,10丁目",
       "浦和区": "北浦和1,2,3,4丁目|針ヶ谷1,2,3丁目|前地1,2,3丁目|常盤5,9,10丁目",
       "南区": "白幡1,3,4,5,6丁目|沼影1,2,3丁目|根岸1,2,3,4,5丁目|曲本1,2,3,4,5丁目|松本1,2,3,4丁目|南浦和1,2,3,4丁目|内谷1,2,3,4,5,6,7丁目|四谷1,2,3丁目"},
"木": {"桜区": "大久保団地|大字上大久保|大字在家|大字栄和|栄和1,2,3,4,5,6丁目|大字下大久保|大字宿|大字白鍬|大字中島|中島1,2,3,4丁目|大字山久保|山久保1,2丁目",
       "南区": "大字大谷口（飛地）|辻2,3,4,5,6丁目|大字広ヶ谷戸",
       "緑区": "大字大牧|大字大間木|大間木2,3丁目|大字大谷口|芝原1,2,3丁目|大字下山口新田|大字中尾|大字蓮見新田|馬場1,2丁目|東浦和1,2,3,4,5,6,7,8,9丁目|松木1,2,3丁目|大字三浦|大字見沼|大字三室|宮本1,2丁目"},
"金": {"浦和区": "大原1,2,3,4,5丁目|上木崎1,2,3,4,5,6,7,8丁目|木崎1,2,3,4,5丁目|北浦和5丁目|皇山町|駒場1,2丁目|瀬ヶ崎1,2,3,4,5丁目|大東1,2,3丁目|高砂3丁目|仲町2丁目|針ヶ谷4丁目|東仲町|大字三崎|領家1,2,3,4,5,6,7丁目",
       "南区": "大谷口（イーストシティ）|大谷場1,2丁目|太田窪4,5丁目",
       "緑区": "道祖土1,2,3,4丁目|原山1,2,3,4丁目|東浦和（イーストシティ）|山崎1丁目",
       "大宮区": "大原6,7丁目"},
}

def expand(spec):
    """'岸町1,2,3丁目' -> {'岸町1丁目',...}; '大字大崎' -> {'大崎'}"""
    out=set()
    for item in spec.split("|"):
        item=item.strip()
        m=re.fullmatch(r"(.+?)([\d,]+)丁目", item)
        if m:
            for n in m.group(2).split(","):
                out.add(f"{m.group(1)}{n}丁目")
        else:
            out.add(item.replace("大字",""))
    return out

bin_map={}  # (ward, chome) -> weekday
for wd, wards in BIN.items():
    for ward, spec in wards.items():
        for ch in expand(spec):
            bin_map[(ward,ch)]=wd

Z2H=str.maketrans("０１２３４５６７８９","0123456789")
def expand_area(area):
    """抽出データの町名表記を丁目単位に展開。'常盤3・4・6～8丁目' -> 常盤3,4,6,7,8丁目; '道場（大字）、道場1・3～5丁目' -> 道場, 道場1,3,4,5丁目"""
    area=area.translate(Z2H)
    res=set()
    for part in re.split(r"[、,]", area):
        part=part.strip()
        if not part: continue
        part=re.sub(r"\s*（.*?）$", lambda m: "" if "大字" in m.group(0) else m.group(0), part)
        m=re.fullmatch(r"(.+?)([\d・～\-]+)丁目(.*)", part)
        if m:
            base=m.group(1); nums=set()
            for seg in m.group(2).split("・"):
                if "～" in seg:
                    a,b=seg.split("～"); nums.update(range(int(a),int(b)+1))
                else: nums.add(int(seg))
            for n in nums: res.add(f"{base}{n}丁目")
        else:
            res.add(part)
    return res

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
doc=yaml.safe_load(open(os.path.join(ROOT,"municipalities/111007_saitama/saitama.yaml"),encoding="utf-8"))
INT2JP={1:"月",2:"火",3:"水",4:"木",5:"金",6:"土",7:"日"}
areas=[{"ward":c["ward"],"area":a["name"],"resources1":INT2JP[c["schedule"]["recyclable1"][0]]}
       for c in doc["courses"] for a in c["areas"]]
match=mismatch=0; unmatched=[]; details=[]
for a in areas:
    if a["ward"] not in {"桜区","浦和区","南区","緑区","大宮区"}: continue
    hits=[]
    for ch in expand_area(a["area"]):
        key=(a["ward"],ch)
        if key in bin_map: hits.append((ch,bin_map[key]))
    if not hits:
        unmatched.append((a["ward"],a["area"])); continue
    for ch,wd in hits:
        if wd==a["resources1"]: match+=1
        else:
            mismatch+=1; details.append((a["ward"],a["area"],ch,"抽出="+a["resources1"],"仕様書="+wd))
print(f"照合: 一致 {match} / 不一致 {mismatch} / 仕様書に見つからず {len(unmatched)}")
for d in details: print("  ✗", d)
if unmatched:
    print("未照合の町名（仕様書側に無い。大宮区の大半は別契約・直営のため対象外）:")
    for u in unmatched: print("  ", u)
sys.exit(1 if mismatch else 0)
