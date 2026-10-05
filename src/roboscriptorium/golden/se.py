"""Derive a reference text faithful to the print edition from a Standard Ebooks repo.

Standard Ebooks commits every editorial change (modernised spelling, hyphenation,
punctuation moves) separately, with a subject starting "[Editorial]". Undoing
those commits, newest first, on top of the latest text keeps all later
transcription fixes while restoring the spelling of the scan they proofread
against.

A commit can't simply be reverted, because each paragraph is one line and
later commits touch the same lines. Instead each change is replayed in reverse:
it is located in the current text by the tokens on either side of it.
"""

import difflib
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

TEXT_DIR = "src/epub/text"
EDITORIAL = "[Editorial]"
# Tokens (words and the whitespace between them) on each side that locate a change.
CONTEXT = 6
_TOKEN = re.compile(r"\s+|[^\s]+")
_TAG = re.compile(r"<[^>]+>")
# Early commits hold a bare "&c."; it must be escaped to stay well-formed XHTML.
_BARE_AMP = re.compile(r"&(?!#?\w+;)")


def _fold(token: str) -> str:
    """A token without markup or word joiners, which later commits add freely."""
    return _TAG.sub("", token).replace("\u2060", "")


@dataclass(frozen=True)
class Edit:
    file: str
    before: tuple[str, ...]
    new: tuple[str, ...]
    old: tuple[str, ...]
    after: tuple[str, ...]


@dataclass
class Report:
    commits: list[str] = field(default_factory=list)
    applied: int = 0
    unmatched: list[Edit] = field(default_factory=list)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout


def _show(repo: Path, rev: str, path: str) -> list[str]:
    try:
        return _git(repo, "show", f"{rev}:{path}").splitlines()
    except subprocess.CalledProcessError:
        return []


def editorial_commits(repo: Path) -> list[tuple[str, str]]:
    """(sha, subject) of every editorial commit, newest first."""
    log = _git(repo, "log", "--format=%H %s", "--", TEXT_DIR)
    return [
        (sha, subject)
        for sha, subject in (line.split(" ", 1) for line in log.splitlines())
        if subject.startswith(EDITORIAL)
    ]


def commit_edits(repo: Path, sha: str) -> list[Edit]:
    files = _git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", sha, "--", TEXT_DIR)
    edits = []
    for path in files.split():
        before_lines, after_lines = _show(repo, f"{sha}^", path), _show(repo, sha, path)
        lines = difflib.SequenceMatcher(None, before_lines, after_lines, autojunk=False)
        for op, i1, i2, j1, j2 in lines.get_opcodes():
            if op != "replace" or i2 - i1 != j2 - j1:
                continue
            for old_line, new_line in zip(before_lines[i1:i2], after_lines[j1:j2], strict=True):
                a, b = _TOKEN.findall(old_line), _TOKEN.findall(new_line)
                words = difflib.SequenceMatcher(None, a, b, autojunk=False)
                # Undone right to left, so text right of each change is already
                # back in its old form and text left of it is still new.
                for wop, a1, a2, b1, b2 in reversed(words.get_opcodes()):
                    if wop == "equal":
                        continue
                    edits.append(
                        Edit(
                            file=Path(path).name,
                            before=tuple(b[max(0, b1 - CONTEXT) : b1]),
                            new=tuple(b[b1:b2]),
                            old=tuple(a[a1:a2]),
                            after=tuple(a[a2 : a2 + CONTEXT]),
                        )
                    )
    return edits


# Context to try, as (tokens before, tokens after), when later commits changed
# the words around an edit. Each attempt must match exactly once per chapter.
_ATTEMPTS = ((CONTEXT, CONTEXT), (2, 2), (CONTEXT, 0), (0, CONTEXT))


def _find(lines: list[list[str]], edit: Edit, before: int, after: int) -> tuple[int, int] | None:
    ctx_before = edit.before[len(edit.before) - before :] if before else ()
    needle = [_fold(t) for t in (*ctx_before, *edit.new, *edit.after[:after])]
    n = len(needle)
    hits = []
    for li, tokens in enumerate(lines):
        folded = [_fold(t) for t in tokens]
        hits += [
            (li, i + len(ctx_before))
            for i in range(len(folded) - n + 1)
            if folded[i : i + n] == needle
        ]
    return hits[0] if len(hits) == 1 else None


def _undo(lines: list[list[str]], edit: Edit) -> bool:
    for before, after in _ATTEMPTS:
        hit = _find(lines, edit, before, after)
        if hit:
            break
    else:
        return False
    li, start = hit
    tokens = lines[li]
    span = tokens[start : start + len(edit.new)]
    if span == list(edit.new):
        tokens[start : start + len(edit.new)] = [_BARE_AMP.sub("&amp;", t) for t in edit.old]
        return True
    # Markup was added around the changed word later: swap the text inside it.
    new, old = _fold("".join(edit.new)), _BARE_AMP.sub("&amp;", _fold("".join(edit.old)))
    if len(span) == 1 and span[0].count(new) == 1:
        tokens[start] = span[0].replace(new, old)
        return True
    return False


def derive(repo: Path) -> tuple[dict[str, str], Report]:
    """Chapter file name → faithful XHTML, plus what was undone."""
    text_dir = repo / TEXT_DIR
    chapters = {
        p.name: [_TOKEN.findall(line) for line in p.read_text().splitlines()]
        for p in sorted(text_dir.glob("chapter-*.xhtml"))
    }
    report = Report()
    for sha, subject in editorial_commits(repo):
        report.commits.append(f"{sha[:8]} {subject}")
        for edit in commit_edits(repo, sha):
            lines = chapters.get(edit.file)
            if lines is not None and _undo(lines, edit):
                report.applied += 1
            else:
                report.unmatched.append(edit)
    out = {name: "\n".join("".join(t) for t in lines) + "\n" for name, lines in chapters.items()}
    return out, report


def checkout(repo_url: str, commit: str, cache: Path) -> Path:
    """A clone of the repo at the pinned commit, reused between runs."""
    if not (cache / ".git").exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--quiet", repo_url, str(cache)], check=True)
    _git(cache, "checkout", "--quiet", commit)
    return cache


def write_reference(repo: Path, repo_url: str, commit: str, out: Path) -> Report:
    chapters, report = derive(repo)
    text_dir = out / "text"
    text_dir.mkdir(parents=True, exist_ok=True)
    for name, xhtml in chapters.items():
        (text_dir / name).write_text(xhtml)

    unmatched = "\n".join(
        f"- `{e.file}`: “{''.join(e.new)}” was “{''.join(e.old)}” in the scan"
        for e in report.unmatched
    )
    commits = "\n".join(f"- {c}" for c in report.commits)
    (out / "PROVENANCE.md").write_text(f"""\
# Provenance

Generated by `roboscriptorium golden derive`; don't edit by hand.

The chapters in `text/` are from [{repo_url}]({repo_url}) at `{commit}`,
dedicated to the public domain by Standard Ebooks under CC0 1.0. Its
`[Editorial]` commits are undone so that spelling and hyphenation match the
scan they proofread against. All other Standard Ebooks fixes are kept.

{report.applied} editorial changes undone; {len(report.unmatched)} could not be located
because later commits rewrote the text around them. These keep Standard Ebooks'
modern form:

{unmatched}

Editorial commits undone, newest first:

{commits}
""")
    return report
