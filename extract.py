import csv
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


def is_adjacent_rects(previous: Rect, current: Rect) -> bool:
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
        if last.contains(rect.top_left) or is_adjacent_rects(last, rect):
            merged.pop()
            merged_rect = Rect(last.top_left, rect.bottom_right)
            merged.append(merged_rect)
        else:
            merged.append(rect)
    return merged


def extract_annots(path: str) -> None:
    pdf = pymupdf.Document(path)

    csv_records: list[CSVRecord] = []

    for i in range(pdf.page_count):
        page = pdf[i]
        highlight_annots = [a for a in page.annots() if a.type[1] == "Highlight"]
        highlight_rects = to_minimal_rects(highlight_annots)
        highlight_rects.sort(key=lambda a: (a.top_left.y, a.top_left.x))

        for r in merge_rects(highlight_rects):
            marked = text_by_rect(page, r)
            if "\n" in marked:
                marked = marked.replace("\n", "__br__")
                print("[WARNING] Linebreak included:", marked)
            record = CSVRecord(
                i + 1,  # "page"
                marked,  # "text"
                "",  # "href"
                r.x0,  # "x0"
                r.y0,  # "y0"
                r.x1,  # "x1"
                r.y1,  # "y1"
            )
            csv_records.append(record)

    timestamp = datetime.today().strftime("%Y%m%d_%H%M%S")
    out_csv_path = Path(path).with_name(f"{Path(path).stem}_{timestamp}.csv")

    with open(out_csv_path, "w", newline="") as f:
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
            extract_annots(p)
