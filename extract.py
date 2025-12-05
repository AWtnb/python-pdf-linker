import csv
import random
import re
import string
import sys
from pathlib import Path
from dataclasses import astuple, fields


import pymupdf
from pymupdf import Annot, Page, Rect, Quad

from entry import HighlightEntry
from logger import logfy


def text_by_rect(page: Page, rect: Rect) -> tuple[str, bool]:
    c = page.get_text(clip=rect)
    s = c.strip() if isinstance(c, str) else ""
    if "\n" not in s:
        return s, False
    print(
        logfy(
            "warning",
            f"p.{page.number + 1} 複数行にわたるマーカーが検出されました",  # type: ignore
            target_str=s.split("\n"),
        )
    )

    words = page.get_text("words", clip=rect)
    words_inside_rect = []
    for word in words:
        word_rect = Rect(word[0:4])
        intersect = word_rect.intersect(rect)
        if not intersect.is_empty:
            coverage = intersect.get_area() / rect.get_area()
            if 0.75 <= coverage:
                text = word[4]
                words_inside_rect.append(text)
                print(
                    logfy(
                        "processing",
                        f"矩形範囲占有率{str(coverage)[:5]}のテキストを抽出しました",
                        target_str=text,
                    )
                )

    if 1 < len(words_inside_rect):
        print(logfy("warning", "矩形内に収まるテキストが複数ありました"))
    return "".join(words_inside_rect), True


# https://github.com/pymupdf/PyMuPDF/issues/318
def to_minimal_rects(annots: list[Annot]) -> list[Rect]:
    rects = []
    for annot in annots:
        t = annot.get_text()
        try:
            vertices = annot.vertices
            if not vertices:
                print(
                    logfy(
                        "skip",
                        "アノテーションに存在するはずの vertices が存在しません",
                        target_str=t,
                    )
                )
                continue
            vertices_count = len(vertices)
            if vertices_count % 4 != 0:
                raise ValueError(
                    logfy(
                        "error",
                        "アノテーションの vertices 数が4の倍数ではありません",
                        target_str=t,
                    )
                )
            quad_count = int(vertices_count / 4)
            for i in range(quad_count):
                q = vertices[i * 4 : i * 4 + 4]
                rects.append(Quad(*q).rect)
        except ValueError as e:
            print(e)
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
    s = re.sub(r"[）〕]+$", "", s)
    if s.endswith("頁"):
        return True
    if s.endswith("号"):
        return True
    if s.endswith("データベース"):
        return True
    if re.search(r"[0-9]{8}$", s):
        return True
    return False


def sort_multicolumned_rects(page: Page, rects: list[Rect]) -> list[Rect]:
    page_rect = page.bound()
    page_center = page_rect.top_left.x + (page_rect.width / 2)

    def _sortkey(rect: Rect) -> tuple:
        return (
            page_center <= rect.top_left.x,
            ((rect.y0 + rect.y1) / 2),
            ((rect.x0 + rect.x1) / 2),
        )

    return sorted(rects, key=_sortkey)


def extract_annots(path: str, single_columned: bool) -> None:

    out_csv_path = Path(path).with_suffix(".csv")
    if out_csv_path.exists():
        print(
            logfy(
                "skip",
                "出力先のCSVファイルが既に存在しています",
                target_path=out_csv_path,
            )
        )
        return

    print(logfy("processing", path))
    pdf = pymupdf.Document(path)

    contents: list[HighlightEntry] = []
    idx = 1

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
            target, multilined = text_by_rect(page, r)

            h = HighlightEntry(
                Id=f"id{idx:04d}",
                Page=i + 1,
                Name=name,
                Text=target,
                Multilined=multilined,
                X0=r.x0,
                Y0=r.y0,
                X1=r.x1,
                Y1=r.y1,
            )
            contents.append(h)
            idx += 1

            if is_semantic_end(target):
                name = random_name()

    header = tuple(f.name for f in fields(HighlightEntry))

    with open(out_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for x in contents:
            writer.writerow(astuple(x))

    pdf.close()


def main(args: list[str]) -> None:
    if len(args) < 2:
        print(
            "使用方法: `uv run .\\extract.py target\\directory\\path` もしくは、対象PDFが一段組の場合は `uv run .\\extract.py target\\directory\\path 1`"
        )
        return
    d = Path(args[1])
    if not d.exists():
        print(logfy("error", "存在しないパスです", target_path=d))
        return
    is_single_column = 2 < len(args) and args[2] == "1"
    if d.is_file():
        extract_annots(str(d), is_single_column)
    else:
        for p in d.glob("*.pdf"):
            extract_annots(str(p), is_single_column)


if __name__ == "__main__":
    main(sys.argv)
