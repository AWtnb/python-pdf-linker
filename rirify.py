import sys

from pathlib import Path

import yaml

from entry import YamlEntry
from helpers import smart_log, stepped_outpath


def yaml_to_tsv(yaml_path: str) -> None:
    smart_log("info", "処理開始", target_path=yaml_path)

    out_tsv_path = stepped_outpath(yaml_path, 3, "txt", "_riri")
    if out_tsv_path.exists():
        smart_log(
            "warning",
            "出力先のtxtファイルが既に存在しています",
            target_path=out_tsv_path,
        )
        return

    entries: list[YamlEntry] = []
    with open(yaml_path, "r", encoding="utf-8") as f:
        content = yaml.safe_load(f)
        for item in content:
            ent = YamlEntry(
                Id=item["Id"],
                Page=item["Page"],
                Text=item["Text"],
                Href=str(
                    item["Href"]
                ).strip(),  # 手入力で入るかもしれないスペースを除去
                AutoFlag=item["AutoFlag"],
                Rects=item["Rects"],
            )
            entries.append(ent)

    tsv_lines: list[str] = ["FileVer:3"]
    genre = "4"
    for ent in entries:
        if ent.Href == "":
            smart_log(
                "warning",
                f"{ent.Id} page{ent.Page} リンク先が指定されていません。スキップします",
                target_str=ent.Text,
            )
            continue
        line = "\t".join([genre, str(ent.AutoFlag), ent.Text, ent.Href])
        tsv_lines.append(line)

    out_tsv_path.write_text(encoding="utf-16", data="\n".join(tsv_lines))


def main(args: list[str]) -> None:
    if len(args) < 2:
        print("使用方法: `uv run .\\rirify.py target\\directory\\path`")
        return
    d = Path(args[1])
    if not d.exists():
        smart_log("error", "存在しないパスです", target_path=d)
        return
    if d.is_file():
        yaml_to_tsv(str(d))
    else:
        for p in d.glob("*.yaml"):
            yaml_to_tsv(str(p))


if __name__ == "__main__":
    args = sys.argv
    main(args)
