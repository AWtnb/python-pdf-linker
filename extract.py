import sys
from pathlib import Path

import pymupdf
from pymupdf import Page, Rect


def text_by_rect(page: Page, rect: Rect) -> str:
    clip = page.get_text(clip=rect)
    if isinstance(clip, str):
        return clip.strip()
    return ""


def is_adjacent_rects(previous: Rect, current: Rect) -> bool:
    x_delta = previous.top_right.distance_to(current.top_left, "mm")
    return (
        (x_delta < 0.5)
        and (previous.top_right.y == current.top_left.y)
        and (previous.bottom_right.y == current.bottom_left.y)
    )


def extract_annots(path: str) -> None:
    pdf = pymupdf.Document(path)

    for i in range(pdf.page_count):
        page = pdf[i]
        highlight_annots = [a for a in page.annots() if a.type[1] == "Highlight"]
        highlight_annots.sort(
            key=lambda a: (
                a.rect.top_left.y,
                a.rect.top_left.x,
                -1 * a.rect.height,
                -1 * a.rect.width,
            )
        )

        unified_rects = []
        for annot in highlight_annots:
            rect = annot.rect
            if len(unified_rects) < 1:
                unified_rects.append(rect)
                continue
            last = unified_rects[-1]
            if is_adjacent_rects(last, rect):
                print("Unifing two adjacent rects:")
                print("- ", text_by_rect(page, last), last)
                print("- ", text_by_rect(page, rect), rect)
                unified_rects.pop()
                unified_rect = Rect(last.top_left, rect.bottom_right)
                unified_rects.append(unified_rect)
            else:
                unified_rects.append(rect)

        for r in unified_rects:
            print("Page", i + 1)
            marked = text_by_rect(page, r)
            print(marked)


if __name__ == "__main__":
    args = sys.argv
    if 1 < len(args):
        p = args[1]
        if Path(p).exists():
            extract_annots(p)
