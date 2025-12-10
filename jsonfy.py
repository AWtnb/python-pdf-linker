import csv
import json
import re
import sys
import os
from itertools import groupby
from dataclasses import asdict
from pathlib import Path

from entry import HighlightEntry, JsonEntry, Location, KiriCSV
from helpers import smart_log, stepped_outpath


def remove_spaces(s: str) -> str:
    def _replacer(m: re.Match) -> str:
        t = str(m.group(0))
        if t[0].isascii() and t[2].isascii():
            return t
        return t[0] + t[2]

    s = re.sub(r" +", " ", s.strip())
    return re.sub(r". .", _replacer, s)


def csv_to_json(csv_path: str) -> None:
    smart_log("debug", "処理開始", target_path=csv_path)

    out_csv_path = stepped_outpath(csv_path, 2, ".csv", "_kiri")
    out_json_path = stepped_outpath(csv_path, 3, ".json")

    if out_json_path.exists():
        smart_log(
            "warning",
            "出力先のjsonファイルが既に存在しています",
            target_path=out_json_path,
        )
        return

    hs: list[HighlightEntry] = []

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        for i, r in enumerate(reader):
            if i == 0:
                continue
            h = HighlightEntry(
                Id=r[0],
                PageIndex=int(r[1]),
                Nombre=r[2],
                Name=r[3].strip(),  # 手入力で入るかもしれないスペースを除去
                Text=r[4],
                X0=float(r[5]),
                Y0=float(r[6]),
                X1=float(r[7]),
                Y1=float(r[8]),
            )

            if h.Name == "":
                smart_log("info", "Name列が空です", target_str=h.Text, skip=True)
            else:
                hs.append(h)

    json_content: list[dict] = []
    kiri_csv = KiriCSV()
    idx = 0

    # 同じ `Name` （ckh, xah, rhv, ...など）を持つエントリでグループ化
    name_groups = [list(g) for _, g in groupby(hs, key=lambda x: x.Name)]
    for name_group in name_groups:

        idx += 1
        text = ""
        locations: list[Location] = []
        single_paged = len(set([g.PageIndex for g in name_group])) == 1

        # グループごとに `Text` と座標（X0・Y0・X1・Y1）を集約
        for record in name_group:
            text += record.Text
            locations.append(
                Location(
                    PageIndex=record.PageIndex,
                    Rect=(record.X0, record.Y0, record.X1, record.Y1),
                )
            )
        text = remove_spaces(text)

        ent = JsonEntry(
            Id=f"id{idx:04d}",
            PageIndex=name_group[0].PageIndex,  # 先頭のページインデックス
            Nombre=name_group[0].Nombre,  # 先頭のノンブル
            Text=text,
            Href="",
            AutoFlag=(1 if single_paged else 0),
            Locations=locations,
        )
        json_content.append(asdict(ent))
        kiri_csv.register(ent)

    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(json_content, f, indent=2, ensure_ascii=False)

    kiri_csv.write_csv(out_csv_path)


def main(args: list[str]) -> None:
    if len(args) < 2:
        print(
            f"使用方法: `uv run .\\{os.path.basename(__file__)} target\\directory\\path`"
        )
        return
    d = Path(args[1])
    if not d.exists():
        smart_log("error", "存在しないパスです", target_path=d)
        return
    if d.is_file():
        if d.suffix == ".csv":
            csv_to_json(str(d))
        else:
            smart_log("error", "CSVファイルを指定してください")
    else:
        for p in d.glob("*.csv"):
            csv_to_json(str(p))


if __name__ == "__main__":
    args = sys.argv
    main(args)
