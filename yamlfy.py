import csv
import re
import sys
from itertools import groupby
from dataclasses import asdict
from pathlib import Path

import yaml

from record import HighlightEntry, YamlEntry
from logger import logfy


def remove_spaces(s: str) -> str:
    def _replacer(m: re.Match) -> str:
        t = str(m.group(0))
        if t[0].isascii() and t[2].isascii():
            return t
        return t[0] + t[2]

    s = re.sub(r" +", " ", s.strip())
    return re.sub(r". .", _replacer, s)


def csv_to_yaml(path: str) -> None:
    out_yaml_path = Path(path).with_suffix(".yaml")

    if out_yaml_path.exists():
        print(
            logfy(
                "skip",
                "出力先のyamlファイルが既に存在してます",
                target_path=str(out_yaml_path),
            )
        )
        return

    print(logfy("processing", path))

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
                X0=float(r[4]),
                Y0=float(r[5]),
                X1=float(r[6]),
                Y1=float(r[7]),
            )
            hs.append(h)

    yaml_content: list[dict] = []
    idx = 0
    manual_check_targets: list[tuple] = []

    # まず `Name` 列（ckh, xah, rhv, ...など）でグループ化して、
    for _, name_group in groupby(hs, key=lambda x: x.Name):
        # https://docs.python.org/3.14/library/itertools.html#itertools.groupby
        name_group = list(name_group)

        # それから、各グループをさらに `Page` ごとにグループ化する
        for page, page_group in groupby(name_group, key=lambda y: y.Page):
            page_group = list(page_group)

            single_paged = len(page_group) == 1
            text = ""
            rects: list[float] = []

            # グループごとに `Text` と座標（X0・Y0・X1・Y1）を集約
            for record in page_group:
                text += record.Text
                rects += [record.X0, record.Y0, record.X1, record.Y1]

            text = remove_spaces(text)
            if not single_paged:
                manual_check_targets.append((page, text))

            ent = YamlEntry(
                Id=f"id{idx:04d}",
                Page=page,
                Text=text,
                Href="",
                AutoFlag=(1 if single_paged else 0),
                Rects=rects,
            )
            yaml_content.append(asdict(ent))
            idx += 1

    with open(out_yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(yaml_content, f, sort_keys=False, allow_unicode=True)

    if 0 < len(manual_check_targets):
        p = Path(path)
        checklist_path = p.with_name(f"_checklist_{p.stem}.csv")
        print(
            logfy(
                "warning",
                "ページをまたいだマーカーがあります。チェックリストのファイルを出力したので確認してください",
                target_path=str(checklist_path),
            )
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
        print(logfy("error", "存在しないパスです", target_path=str(d)))
        return
    if d.is_file():
        csv_to_yaml(str(d))
    else:
        for p in d.glob("*.csv"):
            csv_to_yaml(str(p))


if __name__ == "__main__":
    args = sys.argv
    main(args)
