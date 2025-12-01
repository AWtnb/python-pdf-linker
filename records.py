from typing import NamedTuple


class CSVRecord(NamedTuple):
    id: str
    page: int
    name: str
    text: str
    href: str
    x0: float
    y0: float
    x1: float
    y1: float


def as_record(ss: tuple[str, ...]) -> CSVRecord:
    return CSVRecord(
        ss[0],
        int(ss[1]),
        ss[2],
        ss[3],
        ss[4],
        float(ss[5]),
        float(ss[6]),
        float(ss[7]),
        float(ss[8]),
    )


CSVHeaders: tuple[str, ...] = CSVRecord._fields
