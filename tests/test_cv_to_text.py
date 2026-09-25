import os
import shutil

import pytest

from src.cv_to_text import latex_to_text, main, pdf_to_text


def test_strips_latex_commands():
    out = latex_to_text(r"\textbf{Jane Doe} \section{SKILLS} PyTorch")
    assert "Jane Doe" in out
    assert "PyTorch" in out
    assert "\\" not in out


def test_main_writes_cv(tmp_path):
    tex = tmp_path / "cv.tex"
    tex.write_text(r"\textbf{Jane Doe} " + "machine learning " * 60, encoding="utf-8")
    out = tmp_path / "cv.txt"
    main(["--tex", str(tex), "--out", str(out)])
    text = out.read_text(encoding="utf-8")
    assert "Jane Doe" in text
    assert len(text) > 500


@pytest.mark.skipif(
    shutil.which("pdftotext") is None or not os.path.exists("cv.pdf"),
    reason="pdftotext not installed or cv.pdf not present",
)
def test_pdf_to_text():
    text = pdf_to_text("cv.pdf")
    assert len(text) > 200
