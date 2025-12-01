import csv
import random
import re
import string
import sys
from datetime import datetime
from pathlib import Path

import pymupdf
from pymupdf import Annot, Page, Rect, Quad

from records import CSVRecord, CSVHeaders


def text_by_rect(page: Page, rect: Rect) -> str:
    clip = page.get_text(clip=rect)
    if isinstance(clip, str):
        return clip.strip()
    return ""


# https://github.com/pymupdf/PyMuPDF/issues/318
def to_minimal_rects(annots: list[Annot]) -> list[Rect]:
    rects = []
    for annot in annots:
        t = annot.get_text()
        try:
            vertices = annot.vertices
            if not vertices:
                print(f"Annotation has no vertices: {t}")
                continue
            vertices_count = len(vertices)
            if vertices_count % 4 != 0:
                raise ValueError(f"Annotation has non-4-multipled vertices: {t}")
            quad_count = int(vertices_count / 4)
            for i in range(quad_count):
                q = vertices[i * 4 : i * 4 + 4]
                rects.append(Quad(*q).rect)
        except ValueError as e:
            print(e)
    return rects


def is_horizontally_adjacent(previous: Rect, current: Rect) -> bool:
    return (
        previous.top_right.distance_to(current.top_left, "mm") < 0.5
        and previous.bottom_right.distance_to(current.bottom_left, "mm") < 0.5
    )


def merge_rects(rects: list[Rect]) -> list[Rect]:
    # Assuming `rects` are sorted by position (top-left-first), unify adjacent rects.
    merged: list[Rect] = []
    for rect in rects:
        if len(merged) < 1:
            merged.append(rect)
            continue
        last = merged[-1]
        if is_horizontally_adjacent(last, rect):
            merged.pop()
            merged_rect = Rect(last.top_left, rect.bottom_right)
            merged.append(merged_rect)
        else:
            merged.append(rect)
    return merged


def random_name(length=3):
    return "".join(random.choices(string.ascii_uppercase, k=length))


def remove_spaces(s: str) -> str:
    def _replacer(m: re.Match) -> str:
        t = str(m.group(0))
        if t[0].isascii() and t[2].isascii():
            return t
        return t[0] + t[2]

    s = re.sub(r" +", " ", s.strip())
    return re.sub(r". .", _replacer, s)


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
            rect.top_left.y,
            rect.top_left.x,
        )

    return sorted(rects, key=_sortkey)


def extract_annots(path: str, multicol: bool) -> None:
    pdf = pymupdf.Document(path)

    csv_records: list[CSVRecord] = []
    idx = 1

    for i in range(pdf.page_count):
        page = pdf[i]
        highlight_annots = [a for a in page.annots() if a.type[1] == "Highlight"]
        highlight_rects = to_minimal_rects(highlight_annots)
        if multicol:
            highlight_rects = sort_multicolumned_rects(page, highlight_rects)
        else:
            highlight_rects.sort(key=lambda a: (a.top_left.y, a.top_left.x))

        name = random_name()

        for r in merge_rects(highlight_rects):
            marked = text_by_rect(page, r)
            marked = remove_spaces(marked)
            if "\n" in marked:
                marked = marked.replace("\n", "__br__")
                print("[WARNING] Linebreak included:", marked)

            record = CSVRecord(
                f"{idx:04d}",  # "id"
                i + 1,  # "page"
                name,  # "name"
                marked,  # "text"
                "",  # "href"
                r.x0,  # "x0"
                r.y0,  # "y0"
                r.x1,  # "x1"
                r.y1,  # "y1"
            )
            csv_records.append(record)
            idx += 1

            if is_semantic_end(marked):
                name = random_name()

    timestamp = datetime.today().strftime("%Y%m%d_%H%M%S")
    out_csv_path = Path(path).with_name(f"{Path(path).stem}_{timestamp}.csv")

    with open(out_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSVHeaders)
        for rec in csv_records:
            writer.writerow(rec)

    pdf.close()


if __name__ == "__main__":
    args = sys.argv
    if 1 < len(args):
        p = args[1]
        if Path(p).exists():
            extract_annots(p, True)
