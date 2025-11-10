from typing import TypedDict


class CSVRecord(TypedDict):
    page: int
    text: str
    href: str
    x0: float
    y0: float
    x1: float
    y1: float


dummy: CSVRecord = {
    "page": 0,
    "text": "",
    "href": "",
    "x0": 0.0,
    "y0": 0.0,
    "x1": 0.0,
    "y1": 0.0,
}

CSVColumns = list(dummy.keys())
