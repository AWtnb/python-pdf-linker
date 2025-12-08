import csv
import json
import os
import sys

from pathlib import Path

import pymupdf
from pymupdf import Rect

from entry import JsonEntry
from helpers import smart_log, stepped_outpath
from extract import text_by_rect


def from_jsonpath(json_path: str) -> str:
    p = Path(json_path)
    s = p.stem
    pdf_path = (
        p.with_name(s[:-6] + ".pdf")
        if s[:-1].endswith("_step")
        else p.with_suffix(".pdf")
    )
    if pdf_path.exists():
        return str(pdf_path)
    return ""


def insert_links(json_path: str) -> None:
    smart_log("debug", "処理開始", target_path=json_path)

    out_pdf_path = stepped_outpath(json_path, 3, ".pdf", "_linked")
    if out_pdf_path.exists():
        smart_log(
            "warning",
            "出力先のPDFファイルが既に存在しています",
            target_path=out_pdf_path,
        )
        return

    pdf_path = from_jsonpath(json_path)
    if pdf_path == "":
        smart_log(
            "error",
            "jsonファイル名からPDFファイルを特定できません",
            target_path=json_path,
        )
        return

    entries: list[JsonEntry] = []
    with open(json_path, "r", encoding="utf-8") as f:
        content = json.load(f)
        for item in content:
            ent = JsonEntry(
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

    doc = pymupdf.Document(pdf_path)
    csv_entries: list[tuple] = []
    entry_idx = 0

    for ent in entries:
        rect_elem_count = len(ent.Rects)
        if rect_elem_count % 4 != 0:
            smart_log(
                "warning",
                f"{ent.Id} p.{ent.Page} 矩形を定義するための座標情報数が4の倍数ではありません",
                target_str=ent.Text,
                skip=True,
            )
            continue

        page = doc[ent.Page - 1]

        rect_count = int(rect_elem_count / 4)
        for i in range(rect_count):
            if ent.Text == "":
                smart_log(
                    "warning",
                    f"{ent.Id} p.{ent.Page} リンクとして挿入すべき文字列が指定されていません",
                    target_str=ent.Text,
                    skip=True,
                )
                continue

            r = ent.Rects[i * 4 : i * 4 + 4]
            link_rect = Rect(r)
            t, _ = text_by_rect(page, link_rect)
            csv_entries.append(tuple([f"id{entry_idx:04d}", ent.Page, t, ent.Href] + r))

            page.insert_link(
                {
                    "kind": pymupdf.LINK_URI,
                    "from": link_rect,
                    "uri": ent.Href,
                }
            )

            entry_idx += 1

    out_csv_path = out_pdf_path.with_suffix(".csv")
    with open(out_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(("Id", "Page", "Text", "Href", "X0", "Y0", "X1", "Y1"))
        for c in csv_entries:
            writer.writerow(c)

    doc.save(str(out_pdf_path), garbage=3, clean=True, pretty=True)
    doc.close()


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
        if d.suffix == ".json":
            insert_links(str(d))
        else:
            smart_log("error", "jsonファイルを指定してください")
    else:
        for p in d.glob("*.json"):
            insert_links(str(p))


if __name__ == "__main__":
    args = sys.argv
    main(args)
