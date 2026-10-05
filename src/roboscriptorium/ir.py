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
class Document:
    title: str
    author: str
    language: str
    blocks: list[Paragraph] = field(default_factory=list)
