from dataclasses import dataclass

@dataclass
class HighlightInfo:
    Id: str
    Page: int
    Name: str
    Text: str
    X0: float
    Y0: float
    X1: float
    Y1: float

@dataclass
class YamlEntry:
    Id: str
    Page: int
    Text: str
    Href: str
    Rects: list[float]
