from roboscriptorium.disagreements import Disagreement, Verdicts, _spans, garbled, patch
from roboscriptorium.golden.reference import Chapter


def test_close_differences_merge_into_one():
    out = "the family had been long settled in Sussex".split()
    ref = "the family had long been settled in Sussex".split()
    assert len(_spans(out, ref)) == 1


def test_garbled_output_needs_no_review():
    vocab = {"nothing", "and", "their", "every", "thing"}
    assert garbled("nQthiri£,\\and", vocab)
    assert garbled("tlfat", vocab)
    assert not garbled("every thing", vocab)


def test_patch_puts_the_scan_reading_into_the_reference(tmp_path):
    reference = [Chapter("I", ["She was eager in everything: her sorrows.", "Next."])]
    verdicts = Verdicts(tmp_path / "v.jsonl")
    d = Disagreement(
        "k", "every thing:", "everything:", "She was eager in", "her sorrows.", 7, (1, 1)
    )
    verdicts.record(d, "every thing:", "edition")
    patched, applied = patch(reference, verdicts)
    assert applied == 1
    assert patched[0].paragraphs == ["She was eager in every thing: her sorrows.", "Next."]
    # Verdicts persist and reload.
    assert Verdicts(tmp_path / "v.jsonl").by_key["k"].truth == "every thing:"


def test_patch_keeps_italic_words(tmp_path):
    reference = [Chapter("I", ["She was eager in everything: her sorrows."], [frozenset({4, 6})])]
    verdicts = Verdicts(tmp_path / "v.jsonl")
    d = Disagreement(
        "k", "every thing:", "everything:", "She was eager in", "her sorrows.", 7, (1, 1)
    )
    verdicts.record(d, "every thing:", "edition")
    patched, _ = patch(reference, verdicts)
    assert patched[0].italic == [frozenset({4, 5, 7})]


def test_patch_keeps_the_printed_glyphs(tmp_path):
    reference = [Chapter("I", ["‘Wacht…’ zei ze. ‘Ik kom.’"])]
    verdicts = Verdicts(tmp_path / "v.jsonl")
    d = Disagreement("k", "kom.'", "kom.'", "'Wacht...' zei ze. 'Ik", "", 7, (1, 1))
    verdicts.record(d, "kwam.'", "edition")
    patched, applied = patch(reference, verdicts)
    assert applied == 1
    assert patched[0].paragraphs == ["‘Wacht…’ zei ze. ‘Ik kwam.'"]


def test_patch_applies_verdicts_within_each_others_context(tmp_path):
    reference = [Chapter("I", ["a b c d e f g h i j k l m n o"])]
    verdicts = Verdicts(tmp_path / "v.jsonl")
    verdicts.record(Disagreement("1", "E", "e", "a b c d", "f g h i", 7, (1, 1)), "E", "edition")
    verdicts.record(Disagreement("2", "G", "g", "c d e f", "h i j k", 7, (1, 1)), "G", "edition")
    patched, applied = patch(reference, verdicts)
    assert applied == 2
    assert patched[0].paragraphs == ["a b c d E f G h i j k l m n o"]
