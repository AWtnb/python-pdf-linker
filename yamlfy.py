import csv
import re
import sys
from itertools import groupby
from dataclasses import asdict
from pathlib import Path

import yaml

from entry import HighlightEntry, YamlEntry
from helpers import smart_log


def remove_spaces(s: str) -> str:
    def _replacer(m: re.Match) -> str:
        t = str(m.group(0))
        if t[0].isascii() and t[2].isascii():
            return t
        return t[0] + t[2]

    s = re.sub(r" +", " ", s.strip())
    return re.sub(r". .", _replacer, s)


def csv_to_yaml(path: str) -> None:
    smart_log("debug", "処理開始", target_path=path)

    out_yaml_path = Path(path).with_suffix(".yaml")

    if out_yaml_path.exists():
        smart_log(
            "warning",
            "出力先のyamlファイルが既に存在してます",
            target_path=out_yaml_path,
        )
        return

    hs: list[HighlightEntry] = []

    with open(path, encoding="utf-8") as f:
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

            # Name が空文字であればスキップする
            if h.Name != "":
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
            manuaul_check_flag = not single_paged or any([x.Multilined for x in page_group])
            if manuaul_check_flag:
                manual_check_targets.append((page, text))

            ent = YamlEntry(
                Id=f"id{idx:04d}",
                Page=page,
                Text=text,
                Href="",
                AutoFlag=(1 if manuaul_check_flag else 0),
                Rects=rects,
            )
            yaml_content.append(asdict(ent))
            idx += 1

    with open(out_yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(yaml_content, f, sort_keys=False, allow_unicode=True)

    if 0 < len(manual_check_targets):
        p = Path(path)
        checklist_path = p.with_name(f"{p.stem}_checklist.csv")
        smart_log(
            "warning",
            "ページをまたいだマーカーがあります。チェックリストのファイルを確認してください",
            target_path=checklist_path,
        )
        with open(checklist_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(("Page", "Text"))
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
    if d.is_file():
        csv_to_yaml(str(d))
    else:
        for p in d.glob("*.csv"):
            csv_to_yaml(str(p))


if __name__ == "__main__":
    args = sys.argv
    main(args)
