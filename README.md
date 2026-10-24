# gomi-data

自治体の家庭ごみ収集日程を、機械可読な形（曜日の規則＋例外日＋地区割）で公開するリポジトリ。
現在はさいたま市のみ。

| 自治体 | 版 | 範囲 | 配信JSON | カレンダー購読 |
| --- | --- | --- | --- | --- |
| さいたま市（111007） | 2026-04 | 全10区・322町丁目・77コース | `docs/saitama/v1/courses.json` | `docs/saitama/ics/<コース>.ics` |

配信URL（GitHub Pages を `main` の `/docs` で有効化した場合）:
`https://<account>.github.io/gomi-data/saitama/v1/courses.json`

## 出典と検証（さいたま市）

- 出典: [家庭ごみの出し方マニュアル 令和8年度版](https://www.city.saitama.lg.jp/001/006/010/003/p005300_d/fil/r8_jp_gomimanual.pdf) p.18-19「地区別ごみ収集曜日一覧表」（令和8年3月1日時点）
- 抽出: PDFのテキスト層を列ごとの連続列として読み、区ごとの件数一致（町名N件＝曜日N件）で列を対応付け。全10区で余り0
- 独立照合: 市の[びん収集運搬業務委託仕様書](https://www.city.saitama.lg.jp/005/001/017/006/003/p081629_d/fil/b.pdf)（桜・浦和・南・緑・大宮区）別表と丁目単位で突き合わせ、資源物1類 302件一致・不一致0。可燃物収集の仕様書（見沼・北・大宮区）の5地区も全件一致。`scripts/verify_saitama_bin.py` がCIで毎回確認する
- ルール: 祝日も収集。休みは1月1日〜3日のみ。収集当日 8:30 まで（もえるごみ早朝地区は 5:30）
- 要確認地区: 「吉敷町2丁目（線路より東／西）」「神明1・2丁目の大部分／一部」「イーストシティ地域」など、町名だけでは曜日が決まらない地区には `note: 要確認` を付けている

## ライセンス

データの出典はさいたま市。市はオープンデータライセンスを明示していないため、現時点では**出典を明記し、市サイトの利用規約に準拠**して利用してください。市への利用確認の結果が得られ次第、CC BY 4.0 に切り替える予定です。スクリプトは MIT。

## 構成

```
municipalities/111007_saitama/
  saitama.yaml            正本（人がレビューする）
  raw/r8_manual_p18-19.txt  PDFから抽出したテキスト（1トークン1行）
scripts/
  extract_saitama.py      raw → yaml
  verify_saitama_bin.py   独立資料との照合
  build.py                yaml → docs/（JSON・ics・index）
docs/                     配信物（GitHub Pages）
tests/                    整合性テスト
```

## データ形式（courses.json）

```json
{
  "municipality": {"code": "111007", "name": "さいたま市", "prefecture": "埼玉県"},
  "version": "2026-04",
  "exceptions": ["2027-01-01", "2027-01-02", "2027-01-03"],
  "categories": [{"id": "burnable", "name": "もえるごみ"}, ...],
  "courses": [
    {"id": "西区-03", "ward": "西区", "earlyMorning": false,
     "schedule": {"burnable": [2, 5], "nonburnable": [1], "recyclable1": [4]},
     "areas": [{"name": "宝来"}, {"name": "指扇"}, ...]}
  ]
}
```
曜日は 1=月 … 7=日。`schedule` は iCalendar の `RRULE:FREQ=WEEKLY;BYDAY=` にそのまま写像できる。

## 更新手順

年1回（4月）と年末年始（12月）。

1. 新年度PDFからp.18-19のテキストを抽出して `raw/` に置く（PDFの作りが変わって抽出できなくなったら、セルの色から読む方式を検討）
2. `python scripts/extract_saitama.py raw/... -o saitama.yaml --version 2027-04 --retrieved ... --exceptions ...`
3. `python scripts/verify_saitama_bin.py` と `python -m pytest tests` が通ることを確認。区ごとの件数が前年±5%を超えたら要確認
4. `python scripts/build.py` で `docs/` を再生成し、差分をPull Requestでレビューしてマージ
5. 12月は `exceptions` だけ更新して 4 を実行

## 間違いを見つけたら

「区・町名・区分・正しい曜日・根拠（収集所の掲示など）」を Issue に書いてください。
