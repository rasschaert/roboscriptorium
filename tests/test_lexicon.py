from roboscriptorium.lexicon import Lexicon

WORDS = Lexicon(
    {"mij", "haar", "hygiëne", "naai", "je", "Iemand", "si", "de", "drijfhout", "dood"}
    | {"martel", "kamers", "rjg", "rijen"}
)


def test_no_verdict_where_the_list_cannot_tell():
    # Stress accents on a known word: both versions are words.
    assert WORDS.vouches(["mij", "míj"]) is None
    # Words too short to trust ("Si" for a printed "Sjjj.").
    assert WORDS.vouches(["Sipt-", "Sjjj.", "Si"]) is None
    # A word cut at the line's end, or the cut word's rest at the next line's start.
    assert WORDS.vouches(["de eni-", "deeni-"]) is None
    assert WORDS.vouches(["derig. haar", "haar"], continues=True) is None
    # Where words break: a compound the list lacks splits into words it has.
    assert WORDS.vouches(["martelkamers", "martel kamers"]) is None
    assert WORDS.vouches(["naaije", "naai je"]) is None
    assert WORDS.vouches(["ik's", "ik ’s"]) is None
    # Junk in the list and interjections it lacks: a word without a vowel isn't judged.
    assert WORDS.vouches(["rijg", "rjg"]) is None
    assert Lexicon({"shi"}).vouches(['"Shi', '"Sh!']) is None
    # A hyphen is a cut only at the end: "pushmi-pullyu--the" has no cut word.
    assert Lexicon({"the"}).vouches(["pushmi-pullyu--the", "pushmi-pullyu—the"]) is None
    # Names the list lacks, either way.
    assert WORDS.vouches(["Quinns er", "Quinnser"]) is None


def test_the_one_version_whose_words_are_known():
    assert WORDS.vouches(["hygiéne", "hygiëne"]) == 1
    assert WORDS.vouches(["rjen", "rijen"]) == 1
    assert WORDS.vouches(["lemand", "Iemand"]) == 1
    assert WORDS.vouches(["drijfhout.", "drijthout."]) == 0


def test_curly_apostrophes_are_looked_up_as_the_list_writes_them():
    english = Lexicon({"she'd", "shed", "gone", "home"})
    assert english.knows("She’d")
    assert english.vouches(["She’d gone home.", "Shed gone home."]) is None
    assert Lexicon({"m'n", "moeder"}).knows("m’n")
    # An unknown word stays unknown, apostrophe or not.
    assert not english.knows("he’d")
    assert english.vouches(["She’d gone home.", "Sh’ed gone home."]) == 0
