import csv
import re
import sys
from itertools import groupby
from dataclasses import asdict
from pathlib import Path

import yaml

from entry import HighlightEntry, YamlEntry
from helpers import smart_log, stepped_outpath


def remove_spaces(s: str) -> str:
    def _replacer(m: re.Match) -> str:
        t = str(m.group(0))
        if t[0].isascii() and t[2].isascii():
            return t
        return t[0] + t[2]

    s = re.sub(r" +", " ", s.strip())
    return re.sub(r". .", _replacer, s)


def csv_to_yaml(csv_path: str) -> None:
    smart_log("debug", "処理開始", target_path=csv_path)

    out_yaml_path = stepped_outpath(csv_path, 2, ".yaml")

    if out_yaml_path.exists():
        smart_log(
            "warning",
            "出力先のyamlファイルが既に存在しています",
            target_path=out_yaml_path,
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
                Page=int(r[1]),
                Name=r[2].strip(),  # 手入力で入るかもしれないスペースを除去
                Text=r[3],
                Multilined=(r[4] == "True"),
                X0=float(r[5]),
                Y0=float(r[6]),
                X1=float(r[7]),
                Y1=float(r[8]),
            )

            if h.Name == "":
                smart_log("info", "Name列が空の行をスキップします", target_str=h.Text)
            else:
                hs.append(h)

    yaml_content: list[dict] = []
    manual_check_targets: list[tuple] = []
    idx = 0

    # まず `Name` 列（ckh, xah, rhv, ...など）でグループ化して、
    name_groups = [list(g) for _, g in groupby(hs, key=lambda x: x.Name)]
    for name_group in name_groups:  # name_group は同じ Name を持つ要素からなるリスト

        # それから、各グループをさらに `Page` ごとにグループ化する
        page_groups = [
            (p, list(g)) for p, g in groupby(name_group, key=lambda y: y.Page)
        ]
        single_paged = len(page_groups) == 1

        for (
            page,
            page_group,
        ) in (
            page_groups
        ):  # page_group は同じ Name を持ち、さらに同じ Page を持つ要素からなるリスト
            text = ""
            rects: list[float] = []

            # グループごとに `Text` と座標（X0・Y0・X1・Y1）を集約
            for record in page_group:
                text += record.Text
                rects += [record.X0, record.Y0, record.X1, record.Y1]
            text = remove_spaces(text)

            multiline_flag = any([x.Multilined for x in page_group])
            manuaul_check_flag = not single_paged or multiline_flag
            if manuaul_check_flag:
                check_type = "泣き別れ" if not single_paged else "行間詰まり"
                manual_check_targets.append((page, check_type, text))

            ent = YamlEntry(
                Id=f"id{idx:04d}",
                Page=page,
                Text=text,
                Href="",
                AutoFlag=(0 if manuaul_check_flag else 1),
                Rects=rects,
            )
            yaml_content.append(asdict(ent))
            idx += 1

    with open(out_yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(yaml_content, f, sort_keys=False, allow_unicode=True)

    if 0 < len(manual_check_targets):
        # p = Path(path)
        checklist_path = stepped_outpath(csv_path, 2, ".csv", "_checklist")
        smart_log(
            "warning",
            "手動でチェックしたほうが安全なマーカーが見つかりました。チェックリストのファイルを確認してください",
            target_path=checklist_path,
        )
        with open(checklist_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(("Page", "Type", "Text"))
            for c in manual_check_targets:
                writer.writerow(c)


def main(args: list[str]) -> None:
    if len(args) < 2:
        print("使用方法: `uv run .\\yamlfy.py target\\directory\\path`")
        return
    d = Path(args[1])
    if not d.exists():
        smart_log("error", "存在しないパスです", target_path=d)
        return
    if d.is_file() :
        if d.suffix == ".csv":
            csv_to_yaml(str(d))
        else:
            smart_log("error", "CSVファイルを指定してください")
    else:
        for p in d.glob("*.csv"):
            csv_to_yaml(str(p))


if __name__ == "__main__":
    args = sys.argv
    main(args)
