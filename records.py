from typing import NamedTuple


class CSVRecord(NamedTuple):
    page: int
    text: str
    href: str
    x0: float
    y0: float
    x1: float
    y1: float


def as_record(ss: tuple[str, ...]) -> CSVRecord:
    return CSVRecord(
        int(ss[0]),
        ss[1],
        ss[2],
        float(ss[3]),
        float(ss[4]),
        float(ss[5]),
        float(ss[6]),
    )


CSVHeaders: tuple[str, ...] = CSVRecord._fields
