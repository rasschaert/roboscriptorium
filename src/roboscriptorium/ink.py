"""Ink against paper on a scan: the grey level between them, by Otsu's method."""

import numpy as np


def threshold(gray: np.ndarray) -> int:
    """The grey level that best splits `gray` into ink and paper (Otsu): the level that
    maximises the variance between the two classes. A crop of one grey gives 0."""
    hist = np.bincount(gray.ravel(), minlength=256).astype(float)
    levels = np.arange(256)
    w0 = np.cumsum(hist)
    w1 = gray.size - w0
    m0 = np.cumsum(hist * levels) / np.maximum(w0, 1)
    m1 = ((hist * levels).sum() - np.cumsum(hist * levels)) / np.maximum(w1, 1)
    return int(np.argmax(w0 * w1 * (m0 - m1) ** 2))
