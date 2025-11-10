import csv
import sys

from pathlib import Path

import pymupdf
from pymupdf import Rect

from records import CSVRecord, as_record
from extract import text_by_rect


def apply(pdf_path: str, csv_path: str) -> None:
    csv_records: list[CSVRecord] = []

    with open(csv_path) as f:
        reader = csv.reader(f)
        for i, r in enumerate(reader):
            if i == 0:
                continue
            rec = as_record(tuple(r))
            csv_records.append(rec)

    if len(csv_records) < 1:
        return

    pdf = pymupdf.Document(pdf_path)
    for rec in csv_records:
        page = pdf[rec.page - 1]
        target_rect = Rect(rec.x0, rec.y0, rec.x1, rec.y1)
        t = text_by_rect(page, target_rect)
        if t != rec.text:
            print("Text in specified rect is not equal to CSV:", t)
            continue
        if len(rec.href) < 1:
            print("href not specified:", t)
            continue
        page.insert_link(
            {
                "kind": pymupdf.LINK_URI,
                "from": target_rect,
                "uri": rec.href,
            }
        )

    p = Path(pdf_path)
    out_path = p.with_stem(p.stem + "_out")
    pdf.save(str(out_path), garbage=3, clean=True, pretty=True)
    pdf.close()


if __name__ == "__main__":
    args = sys.argv
    if 2 < len(args):
        params = args[1:3]
        if any([not Path(p).exists() for p in params]):
            print("invalid path found.")
        else:
            apply(*params)
