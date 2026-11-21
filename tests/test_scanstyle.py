from roboscriptorium import scanstyle


def test_the_descent_below_baseline_ending_boxes_is_measured_on_the_scan(tmp_path):
    import pymupdf

    from roboscriptorium.pdf import Line, PageText

    doc = pymupdf.open()
    page = doc.new_page(width=400, height=600)
    lines = []
    for i in range(14):
        base = 80 + 14 * i
        page.insert_text((40, base), "gjpqy jumping quickly by the grey jetty, gp", fontsize=11)
        # A box as the scans' layers give it: from the cap height to the baseline.
        lines.append(Line("gjpqy jumping quickly by the grey jetty, gp", 40, base - 8, 260, base))
    doc.save(tmp_path / "s.pdf")
    pages = [PageText(1, 400, 600, lines), PageText(2, 400, 600, [])]  # a blank page too
    descent = scanstyle.measure_descent(tmp_path / "s.pdf", pages, tmp_path / "descent.json")
    # Helvetica's descenders reach about a fifth of the point size below the baseline.
    assert 0.2 <= descent <= 0.45
    assert (
        scanstyle.measure_descent(tmp_path / "s.pdf", pages, tmp_path / "descent.json") == descent
    )


def test_a_measure_cached_by_other_code_or_left_unreadable_is_made_again(tmp_path):
    import json

    import pymupdf

    from roboscriptorium.pdf import Line, PageText

    doc = pymupdf.open()
    page = doc.new_page(width=400, height=600)
    lines = []
    for i in range(14):
        base = 80 + 14 * i
        page.insert_text((40, base), "gjpqy jumping quickly by the grey jetty, gp", fontsize=11)
        lines.append(Line("gjpqy jumping quickly by the grey jetty, gp", 40, base - 8, 260, base))
    doc.save(tmp_path / "s.pdf")
    pages = [PageText(1, 400, 600, lines)]
    cache = tmp_path / "descent.json"
    descent = scanstyle.measure_descent(tmp_path / "s.pdf", pages, cache)
    # The same version and pages, but measured by code since changed or reverted.
    stale = json.loads(cache.read_text()) | {"descent": 0.99, "code": "not this code"}
    cache.write_text(json.dumps(stale))
    assert scanstyle.measure_descent(tmp_path / "s.pdf", pages, cache) == descent
    # Emptied by a crash after its rename.
    cache.write_text("")
    assert scanstyle.measure_descent(tmp_path / "s.pdf", pages, cache) == descent
    # Kept when nothing changed: a planted value is served.
    planted = json.loads(cache.read_text()) | {"descent": 0.5}
    cache.write_text(json.dumps(planted))
    assert scanstyle.measure_descent(tmp_path / "s.pdf", pages, cache) == 0.5
