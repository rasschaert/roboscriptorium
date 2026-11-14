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
