import csv
import re
import sys
from itertools import groupby
from dataclasses import asdict
from pathlib import Path

import yaml
from record import HighlightInfo, YamlEntry


def remove_spaces(s: str) -> str:
    def _replacer(m: re.Match) -> str:
        t = str(m.group(0))
        if t[0].isascii() and t[2].isascii():
            return t
        return t[0] + t[2]

    s = re.sub(r" +", " ", s.strip())
    return re.sub(r". .", _replacer, s)


def csv_to_yaml(path: str) -> None:
    his: list[HighlightInfo] = []

    with open(path, encoding="utf-8") as f:
        reader = csv.reader(f)
        for i, r in enumerate(reader):
            if i == 0:
                continue
            hi = HighlightInfo(
                Id=r[0],
                Page=int(r[1]),
                Name=r[2].strip(),  # for manual edit
                Text=r[3],
                X0=float(r[4]),
                Y0=float(r[5]),
                X1=float(r[6]),
                Y1=float(r[7]),
            )
            his.append(hi)

    yaml_content: list[dict] = []
    idx = 0

    # First, group record by `Name` (e.g. ckh, xah, rhv, ...)
    for _, name_group in groupby(his, key=lambda x: x.Name):
        # https://docs.python.org/3.14/library/itertools.html#itertools.groupby
        name_group = list(name_group)
        # Then, re-group each name-based-group by `Page`
        for page, page_group in groupby(name_group, key=lambda y: y.Page):
            # https://docs.python.org/3.14/library/itertools.html#itertools.groupby
            page_group = list(page_group)
            text = ""
            rects: list[float] = []
            for record in page_group:
                text += record.Text
                rects += [record.X0, record.Y0, record.X1, record.Y1]
            ent = YamlEntry(
                Id=f"id{idx:04d}",
                Page=page,
                Text=remove_spaces(text),
                Href="",
                Rects=rects,
            )
            yaml_content.append(asdict(ent))
            idx += 1

    out_yaml_path = Path(path).with_suffix(".yaml")
    with open(out_yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(yaml_content, f, sort_keys=False, allow_unicode=True)


if __name__ == "__main__":
    args = sys.argv
    if 1 < len(args):
        p = args[1]
        if Path(p).exists():
            csv_to_yaml(p)
