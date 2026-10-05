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


@dataclass
class Heading:
    text: str
    sources: list[SourceRef] = field(default_factory=list)


Block = Paragraph | Heading


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
