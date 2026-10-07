"""The intermediate representation every input format is turned into.

The EPUB builder reads only from this. Each block keeps references to the source
lines it came from, so review can show the matching scan region.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourceRef:
    page: int  # 1-based
    line: int  # index into that page's visual lines


@dataclass
class Paragraph:
    text: str
    sources: list[SourceRef] = field(default_factory=list)
    # True for the first paragraph of a section, which typesets without indent.
    opening: bool = False
    # Its first letter is a decorated initial, set as a drop cap.
    initial: bool = False
    # Indices of its italic words in `text.split()`, ascending.
    italic: tuple[int, ...] = ()


@dataclass
class Heading:
    text: str
    sources: list[SourceRef] = field(default_factory=list)
    # The heading's lines as set: a label and a title ("THE FIRST CHAPTER",
    # "PUDDLEBY") are two; a title wrapped over two lines is one.
    parts: list[str] = field(default_factory=list)


@dataclass
class Figure:
    """A picture cut from the scan, upright, with its caption."""

    image: str  # file name of the JPEG among the book's figures
    page: int
    box: tuple[float, float, float, float]  # where it sits on the page, in PDF points
    caption: str = ""


Block = Paragraph | Heading | Figure


@dataclass
class Document:
    title: str
    author: str
    language: str
    blocks: list[Block] = field(default_factory=list)

    @property
    def paragraphs(self) -> list[Paragraph]:
        return [b for b in self.blocks if isinstance(b, Paragraph)]

    @property
    def headings(self) -> list[Heading]:
        return [b for b in self.blocks if isinstance(b, Heading)]

    @property
    def figures(self) -> list[Figure]:
        return [b for b in self.blocks if isinstance(b, Figure)]
