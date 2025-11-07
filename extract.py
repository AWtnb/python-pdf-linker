import csv
import sys
from datetime import datetime
from pathlib import Path

import pymupdf
from pymupdf import Annot, Page, Rect, Quad


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
    x_delta = previous.top_right.distance_to(current.top_left, "mm")
    return x_delta < 0.5


def unify_rects(rects: list[Rect]) -> list[Rect]:
    unified: list[Rect] = []
    for rect in rects:
        if len(unified) < 1:
            unified.append(rect)
            continue
        last = unified[-1]
        if is_adjacent_rects(last, rect) or rect.intersects(last):
            unified.pop()
            unified_rect = Rect(last.top_left, rect.bottom_right)
            unified.append(unified_rect)
        else:
            unified.append(rect)
    return unified


def extract_annots(path: str) -> None:
    pdf = pymupdf.Document(path)

    csv_records = []

    for i in range(pdf.page_count):
        page = pdf[i]
        highlight_annots = [a for a in page.annots() if a.type[1] == "Highlight"]
        highlight_rects = to_minimal_rects(highlight_annots)
        highlight_rects.sort(key=lambda a: (a.top_left.y, a.top_left.x))

        for r in unify_rects(highlight_rects):
            marked = text_by_rect(page, r)
            if "\n" in marked:
                marked = marked.replace("\n", "__br__")
                print("[WARNING] Linebreak included:", marked)
            csv_records.append(
                {
                    "page": i + 1,
                    "text": marked,
                    "href": "",
                    "x0": r.x0,
                    "y0": r.y0,
                    "x1": r.x1,
                    "y1": r.y1,
                }
            )

    timestamp = datetime.today().strftime("%Y%m%d_%H%M%S")
    out_csv_path = Path(path).with_name(f"{Path(path).stem}_{timestamp}.csv")

    with open(out_csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, ["page", "text", "href", "x0", "y0", "x1", "y1"])
        writer.writeheader()
        for rec in csv_records:
            writer.writerow(rec)

    pdf.close()


if __name__ == "__main__":
    args = sys.argv
    if 1 < len(args):
        p = args[1]
        if Path(p).exists():
            extract_annots(p)
