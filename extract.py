import csv
import random
import re
import string
import os
import sys

from pathlib import Path
from dataclasses import astuple, fields
from typing import NamedTuple


import pymupdf
from pymupdf import Annot, Page, Rect, Quad

from entry import HighlightEntry
from helpers import smart_log, stepped_outpath


class ExcludedWord(NamedTuple):
    text: str
    coverage: float


def text_by_rect(page: Page, rect: Rect) -> tuple[str, list[ExcludedWord]]:
    s: str = page.get_text(clip=rect)  # type: ignore
    s = s.strip()
    if "\n" not in s:
        return s, []

    smart_log(
        "info",
        f"p.{page.number + 1} マーカーの矩形が上下の行と重なっています",  # type: ignore
        target_str=s.split("\n"),
    )

    # https://pymupdf.readthedocs.io/en/latest/textpage.html#TextPage.extractWORDS
    words: list[tuple] = page.get_text("words", clip=rect)  # type: ignore

    words_inside_rect = []
    words_excluded: list[ExcludedWord] = []

    for word in words:
        word_rect = Rect(word[0:4])
        intersect = word_rect.intersect(rect)
        word_text = word[4]
        if intersect.is_empty:
            words_excluded.append(ExcludedWord(word_text, 0.0))
        else:
            vertical_coverage = intersect.height / rect.height
            if 0.5 <= vertical_coverage:
                words_inside_rect.append(word)
                smart_log(
                    "info",
                    f"矩形に占める高さ比率{str(vertical_coverage)[:5]}のテキストを抽出しました",
                    target_str=word_text,
                )
            else:
                words_excluded.append(ExcludedWord(word_text, vertical_coverage))

    words_inside_rect.sort(key=lambda w: w[0])

    return "".join([w[4] for w in words_inside_rect]), words_excluded


# https://github.com/pymupdf/PyMuPDF/issues/318
def to_minimal_rects(annots: list[Annot]) -> list[Rect]:
    rects = []
    for annot in annots:
        t = annot.get_text()
        vertices = annot.vertices
        if not vertices:
            smart_log("info", "注釈の頂点情報を検出できません", target_str=t, skip=True)
            continue
        vertices_count = len(vertices)
        if vertices_count % 4 != 0:
            smart_log(
                "warning",
                "注釈の頂点数が4の倍数ではありません",
                target_str=t,
                skip=True,
            )
            continue
        quad_count = int(vertices_count / 4)
        for i in range(quad_count):
            q = vertices[i * 4 : i * 4 + 4]
            rects.append(Quad(*q).rect)
    return rects


def is_side_by_side(previous: Rect, current: Rect) -> bool:
    return (
        previous.top_right.distance_to(current.top_left, "mm") < 0.5
        and previous.bottom_right.distance_to(current.bottom_left, "mm") < 0.5
    )


# `rects` が左上を起点としてソートされているものとして、隣り合う物同士を1つにまとめる
def merge_rects(rects: list[Rect]) -> list[Rect]:
    merged: list[Rect] = []
    for rect in rects:
        if len(merged) < 1:
            merged.append(rect)
            continue
        last = merged[-1]
        if is_side_by_side(last, rect):
            merged.pop()
            merged_rect = Rect(last.top_left, rect.bottom_right)
            merged.append(merged_rect)
        else:
            merged.append(rect)
    return merged


def random_name(length=3):
    return "".join(random.choices(string.ascii_lowercase, k=length))


def is_semantic_end(s: str) -> bool:
    s = re.sub(r"[）〕。、，]+$", "", s)
    if s.endswith("頁"):
        return True
    if s.endswith("号"):
        return True
    if s.endswith("データベース"):
        return True
    if s.endswith("DB"):
        return True
    if re.search(r"[0-9]{8}$", s):
        return True
    return False


def sort_multicolumned_rects(page: Page, rects: list[Rect]) -> list[Rect]:
    page_rect = page.bound()
    page_center = (page_rect.x0 + page_rect.x1) / 2

    def _sortkey(rect: Rect) -> tuple:
        return (
            page_center <= rect.top_left.x,
            ((rect.y0 + rect.y1) / 2),
            ((rect.x0 + rect.x1) / 2),
        )

    return sorted(rects, key=_sortkey)


class ChecklistEntry(NamedTuple):
    entry: HighlightEntry
    excluded: list[ExcludedWord]


def extract_annots(pdf_path: str, single_columned: bool) -> None:
    smart_log("debug", "処理開始", target_path=pdf_path)

    out_csv_path = stepped_outpath(pdf_path, 1, ".csv")
    if out_csv_path.exists():
        smart_log(
            "warning",
            "出力先のCSVファイルが既に存在しています",
            target_path=out_csv_path,
        )
        return

    pdf = pymupdf.Document(pdf_path)

    checklist_entries: list[ChecklistEntry] = []
    csv_entries: list[HighlightEntry] = []
    entry_idx = 0

    for i in range(pdf.page_count):
        page = pdf[i]
        highlight_annots = [a for a in page.annots() if a.type[1] == "Highlight"]
        highlight_rects = to_minimal_rects(highlight_annots)
        if single_columned:
            highlight_rects.sort(key=lambda a: ((a.y0 + a.y1) / 2, (a.x0 + a.x1) / 2))
        else:
            highlight_rects = sort_multicolumned_rects(page, highlight_rects)

        name = random_name()

        for r in merge_rects(highlight_rects):
            entry_idx += 1
            target, excluded = text_by_rect(page, r)

            h = HighlightEntry(
                Id=f"id{entry_idx:04d}",
                PageIndex=i,
                Nombre=page.get_label(),
                Name=name,
                Text=target,
                X0=r.x0,
                Y0=r.y0,
                X1=r.x1,
                Y1=r.y1,
            )
            csv_entries.append(h)

            if 0 < len(excluded):
                checklist_entries.append(ChecklistEntry(h, excluded))

            if is_semantic_end(target):
                name = random_name()

    pdf.close()

    header = tuple(f.name for f in fields(HighlightEntry))
    with open(out_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for x in csv_entries:
            writer.writerow(astuple(x))

    if 0 < len(checklist_entries):
        checklist_path = stepped_outpath(pdf_path, 1, ".txt", "_checklist")
        smart_log(
            "info",
            "マーカーの矩形が上下の行と重なっている箇所が検出されました。チェックリストを出力します",
            target_path=checklist_path,
        )

        lines: list[str] = []
        for ent in checklist_entries:
            lines.append(f"ページインデックス：{ent.entry.PageIndex}")
            lines.append(f"ノンブル：{ent.entry.Nombre}")
            lines.append(f"抽出テキスト：{ent.entry.Text}")
            lines.append("除外テキスト：")
            for ex in ent.excluded:
                lines.append(f"- coverage {str(ex.coverage)[:5]}: {ex.text}")
            lines.append("")
        checklist_path.write_text("\n".join(lines), encoding="utf-8")


def main(args: list[str]) -> None:
    if len(args) < 2:
        print(
            f"使用方法: `uv run .\\{os.path.basename(__file__)} target\\directory\\path` もしくは、対象PDFが一段組の場合は `uv run .\\extract.py target\\directory\\path 1`"
        )
        return
    d = Path(args[1])
    if not d.exists():
        smart_log("error", "存在しないパスです", target_path=d)
        return
    is_single_column = 2 < len(args) and args[2] == "1"
    if d.is_file():
        if d.suffix == ".pdf":
            extract_annots(str(d), is_single_column)
        else:
            smart_log("error", "PDFファイルを指定してください")
    else:
        for p in d.glob("*.pdf"):
            extract_annots(str(p), is_single_column)


if __name__ == "__main__":
    main(sys.argv)
