from roboscriptorium import readers


def test_a_crop_stops_where_the_line_above_ends_its_descenders():
    # Text-layer boxes that end on the baseline, set tight (Andere levens, PDF p. 178):
    # the line above's descenders hang below its box, into this line's padding.
    above, line, below = (
        (100, 261.2, 300, 271.9),
        (100, 274.7, 300, 285.4),
        (100, 288.3, 300, 299.0),
    )
    top, bottom = readers.own_span([above, line, below], 1, 4, 0.27)
    assert top == 274.7  # the line above's descenders end below its box, at 274.8
    assert top <= 274.7 and 285.4 < bottom <= 288.3
    # Set with room between the lines, the crop is the box and its pad, as before.
    loose = [(100, 240.0, 300, 250.0), (100, 260.0, 300, 270.0), (100, 280.0, 300, 290.0)]
    assert readers.own_span(loose, 1, 4, 0.27) == (256.0, 274.0)
    # A line alone, or one in another column, leaves the pad whole.
    assert readers.own_span([line], 0, 4, 0.27) == (270.7, 289.4)
    assert readers.own_span([(400, 261.2, 500, 271.9), line], 1, 4, 0.27) == (270.7, 289.4)
