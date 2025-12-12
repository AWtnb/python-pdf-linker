import csv
from pathlib import Path
from dataclasses import dataclass


@dataclass
class HighlightEntry:
    """
    PDFに引かれたマーカーのエントリを表すデータクラス。

    - Id: id0001から開始する文字列
    - PageIndex: PDFの先頭を0としたときのインデックス。紙面のノンブル（`Nombre`）とは一致しない。
    - Nombre: 紙面のノンブル。
    - Name: ランダムに生成した3つのアルファベット小文字
        - ページが切り替わるとき、もしくはマーカーの対象が変わる（対象文字列で判定）タイミングで更新
        - 同じ名前を持つエントリ同士で `Text` をつなげると意味のある文字列の最小単位になる
    - Text: マーカー対象の文字列
        - 数字の前後のスペースなども含め、PDFからコピーしたままの状態
    - X0: 矩形の座標（左上x）
    - Y0: 矩形の座標（左上y）
    - X1: 矩形の座標（右下x）
    - Y1: 矩形の座標（右下y）
    """

    Id: str
    PageIndex: int
    Nombre: str
    Name: str
    Text: str
    X0: float
    Y0: float
    X1: float
    Y1: float


@dataclass
class Location:
    """
    矩形の座標情報とページ情報を表すデータクラス。
    理論上、これらの情報がわかっていればPDF上で一意に定位できる。

    - PageIndex: PDFの先頭を0としたときのインデックス。紙面のノンブル（`Nombre`）とは一致しない。
    - Rect: マーカーの矩形座標情報
        - `(x0, y0, x1, y1)`
    """

    PageIndex: int
    Rect: tuple[float, float, float, float]

    @classmethod
    def from_dict(cls, data: dict) -> Location:
        return cls(PageIndex=data["PageIndex"], Rect=tuple(data["Rect"]))


@dataclass
class JsonEntry:
    """
    Jsonエントリを表すデータクラス。

    - Id: id0001から開始する文字列
    - PageIndex: PDFの先頭を0としたときのインデックス。紙面のノンブル（`Nombre`）とは一致しない。
    - Nombre: 紙面のノンブル。
    - Text: 文字列本文
        - 不要なスペースは機械的に削除済み
    - Href: リンク先
    - AutoFlag: 機械的に処理できるかの判定
        - 0：処理不可＝人間が判別する必要あり
            - `Rects.Page` が1種類ではない＝泣き別れ状態
        - 1：処理可＝ツールに投入して処理
    - Locations: `Location` データクラスの配列
    """

    Id: str
    PageIndex: int
    Nombre: str
    Text: str
    Href: str
    AutoFlag: int
    Locations: list[Location]


class KiriCSV:
    header = (
        "頁",
        "不要フラグ",
        "本文・注の区別",
        "本文の出現ブロック_①横組の場合、右・左_②縦組3段の場合：上・中・下_③縦組4段の場合：1・2・3・4_④表題",
        "抜き出し内容",
        "コメント",
        "目次レベル１",
        "目次レベル２",
        "目次レベル３",
        "目次レベル４",
        "解説名",
        "項目番号",
        "対象判例枝番号",
        "登載誌",
        "事件名",
        "肩書き",
        "筆者",
        "筆者読み",
        "No",
        "号",
        "件数",
    )
    entries: list[tuple] = []

    def __init__(self) -> None:
        self.entries = []

    @classmethod
    def to_entry(cls, nombre: str, text: str) -> tuple:
        fields = ["" for _ in cls.header]
        fields[0] = nombre
        fields[4] = text
        return tuple(fields)

    def register(self, entry: JsonEntry) -> None:
        self.entries.append(self.to_entry(entry.Nombre, entry.Text))

    def write_csv(self, path: Path) -> None:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(self.header)
            writer.writerows(self.entries)
