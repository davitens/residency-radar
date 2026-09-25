from __future__ import annotations

import argparse
import re
import subprocess
import sys

DEFAULT_TEX = "cv.tex"
DEFAULT_OUT = "data/cv.txt"

_PREAMBLE = re.compile(
    r"\\(documentclass|usepackage|newcommand|renewcommand|providecommand|definecolor|"
    r"setlength|addtolength|titleformat|pagestyle|fancyhf|urlstyle|hypersetup|"
    r"color|geometry|setmainfont|usepackage)(\[[^\]]*\])?(\{[^{}]*\})*"
)
_COMMAND_ARG = re.compile(r"\\[a-zA-Z@]+\*?(\[[^\]]*\])?\{([^{}]*)\}")
_BARE_COMMAND = re.compile(r"\\[a-zA-Z@]+\*?(\[[^\]]*\])?")


def _document_body(tex: str) -> str:
    start = tex.find(r"\begin{document}")
    end = tex.find(r"\end{document}")
    if start != -1 and end != -1 and end > start:
        return tex[start + len(r"\begin{document}") : end]
    return tex


def latex_to_text(tex: str) -> str:
    tex = _document_body(tex)
    tex = re.sub(r"(?<!\\)%.*", "", tex)
    tex = re.sub(r"\\(begin|end)\{[^}]*\}", " ", tex)
    tex = _PREAMBLE.sub(" ", tex)
    for _ in range(4):
        tex, n = _COMMAND_ARG.subn(r"\2", tex)
        if n == 0:
            break
    tex = _BARE_COMMAND.sub(" ", tex)
    tex = tex.replace("\\", " ").replace("&", " ").replace("~", " ").replace("$", " ")
    tex = re.sub(r"[ \t]+", " ", tex)
    tex = re.sub(r"\n\s*\n+", "\n", tex)
    return tex.strip()


def pdf_to_text(path: str) -> str:
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", path, "-"], capture_output=True, text=True, check=True
        )
        if result.stdout.strip():
            return result.stdout
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    from pypdf import PdfReader

    return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Convert a LaTeX or PDF CV to plain text.")
    parser.add_argument("--tex", "--input", dest="source", default=DEFAULT_TEX)
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    if args.source.lower().endswith(".pdf"):
        text = pdf_to_text(args.source)
    else:
        text = latex_to_text(open(args.source, encoding="utf-8").read())
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"wrote {args.out} ({len(text)} chars)")


if __name__ == "__main__":
    sys.exit(main())
