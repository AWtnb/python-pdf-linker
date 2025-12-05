from dataclasses import dataclass


@dataclass
class HighlightEntry:
    """
    PDFに引かれたマーカーのエントリを表すデータクラス。

    - Id: id0000から開始する文字列（`id` は数値型に変換されないためのプレフィックス）
    - Page: ページ番号
        - 紙面のノンブルではなくPDFファイル上での位置
    - Name: ランダムに生成した3つのアルファベット小文字
        - マーカーが複数行にわたる場合、行ごとに矩形を分割して考える。そうして生まれた矩形をグループ化するための便宜的な名前を割り振る
        - 同じ名前を持つエントリ同士で `Text` をつなげると意味のあるまとまりになる、という想定。
        - 機械的に判定できないケースもあるので、人間はここが正しく割り振られているかをチェックする
            - 人間の作業は、「本来異なる文字列を割り振られるためのエントリが同じ Name になってしまっているときに、別の Name を割り振る」に絞る
                - 「同じ Name を持つ連続するエントリ」を1つのまとまりとして考えるようにしているため、新たな Name を考える際に全体を見て重複チェックする必要はない
                - もし、yamlへの変換時に残したくない場合は、 Name を空文字にする
    - Text: マーカー対象の文字列
        - 数字の前後のスペースなども含め、PDFからコピーしたままの状態
    - Multilined: 矩形でテキストを抽出したときに複数行になってしまうかの判定
        - `Page.get_text(clip=rect)` は、行間が詰まっていて上の行のフォントbboxの一部でも `Y0` にかかるとテキストを抽出する仕様
        - 機械的にフィルタリングしているとはいえ例外的なのでこのフラグによって記録しておく
    - X0: 矩形の座標（左上x）
    - Y0: 矩形の座標（左上y）
    - X1: 矩形の座標（右下x）
    - Y1: 矩形の座標（右下y）
    """

    Id: str
    Page: int
    Name: str
    Text: str
    Multilined: bool
    X0: float
    Y0: float
    X1: float
    Y1: float


@dataclass
class YamlEntry:
    """
    YAMLエントリを表すデータクラス。

    - Id: id0000から開始する文字列（`id` は数値型に変換されないためのプレフィックス）
    - Page: ページ番号
        - 紙面のノンブルではなくPDFファイル上での位置
    - Text: 文字列本文
        - 不要なスペースは機械的に削除済み
    - Href: リンク先
    - AutoFlag: 機械的に処理できるかの判定
        - 0：処理不可＝人間が判別する必要あり
        - 1：処理可＝ツールに投入して処理
    - Rects: 座標情報
        - [x0, y0, x1, y1, ...]の配列
        - [PyMuPDFの `Annot.vertices`](https://pymupdf.readthedocs.io/en/latest/annot.html#Annot.vertices) と同じ考え方で、マーカーの矩形が複数行にわたる場合は先頭から順に4要素ずつが矩形のx0, y0, x1, y1に対応する
        - そのため、要素数は必ず4の倍数となる
    """

    Id: str
    Page: int
    Text: str
    Href: str
    AutoFlag: int
    Rects: list[float]
