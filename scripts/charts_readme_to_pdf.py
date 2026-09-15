"""
Converte charts/README.md (o guia dos gráficos, com as imagens embutidas) em
um PDF, para quem preferir ler/compartilhar sem abrir o repositório.

Uso:
    .venv/bin/python scripts/charts_readme_to_pdf.py

Requer o pacote "markdown" (veja requirements.txt) e o Google Chrome
instalado (usa o modo --headless dele para imprimir o HTML em PDF - não
precisa de wkhtmltopdf/weasyprint/pandoc).
"""

import shutil
import subprocess
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
CHARTS_DIR = ROOT / "charts"
MD_FILE = CHARTS_DIR / "README.md"
HTML_FILE = CHARTS_DIR / "_README_pdf_build.html"
PDF_FILE = CHARTS_DIR / "README.pdf"

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome",
    "chromium",
    "chromium-browser",
]

CSS = """
@page { size: A4; margin: 20mm 18mm; }
* { box-sizing: border-box; }
body {
    font-family: -apple-system, "Segoe UI", system-ui, sans-serif;
    color: #0b0b0b;
    line-height: 1.5;
    font-size: 13px;
    max-width: 780px;
    margin: 0 auto;
}
h1 { font-size: 24px; margin: 0 0 14px; }
h2 { font-size: 17px; margin: 30px 0 10px; padding-top: 8px; border-top: 1px solid #e1e0d9; page-break-after: avoid; }
h3 { font-size: 14px; margin: 20px 0 6px; color: #0b0b0b; page-break-after: avoid; }
p { color: #26251f; margin: 6px 0 12px; }
strong { color: #0b0b0b; }
img { max-width: 100%; display: block; margin: 8px 0 4px; border: 1px solid #e1e0d9; border-radius: 4px; page-break-inside: avoid; }
h3, img, h3 + img { page-break-inside: avoid; }
hr { border: none; border-top: 1px solid #e1e0d9; margin: 22px 0; }
table { border-collapse: collapse; width: 100%; margin: 10px 0 16px; font-size: 12px; }
th, td { border: 1px solid #e1e0d9; padding: 6px 8px; text-align: left; }
th { background: #f4f3f0; }
code { background: #f4f3f0; padding: 1px 4px; border-radius: 3px; font-size: 12px; }
a { color: #2a78d6; text-decoration: none; }
"""


def find_chrome():
    for candidate in CHROME_CANDIDATES:
        path = shutil.which(candidate) or (candidate if Path(candidate).exists() else None)
        if path:
            return path
    return None


def main():
    if not MD_FILE.exists():
        sys.exit(f"Não encontrei {MD_FILE}")

    chrome = find_chrome()
    if not chrome:
        sys.exit("Não encontrei o Google Chrome/Chromium instalado - necessário para gerar o PDF.")

    md_text = MD_FILE.read_text(encoding="utf-8")
    body_html = markdown.markdown(md_text, extensions=["tables", "sane_lists"])

    html = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Guia dos gráficos - LogiBot RAG Benchmark</title>
<style>{CSS}</style>
</head>
<body>
{body_html}
</body>
</html>
"""
    HTML_FILE.write_text(html, encoding="utf-8")
    print(f"HTML intermediário: {HTML_FILE.relative_to(ROOT)}")

    cmd = [
        chrome,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",
        f"--print-to-pdf={PDF_FILE}",
        "--print-to-pdf-no-header",
        HTML_FILE.resolve().as_uri(),
    ]
    print("Rodando Chrome headless para gerar o PDF...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    HTML_FILE.unlink(missing_ok=True)

    if result.returncode != 0 or not PDF_FILE.exists():
        print(result.stdout)
        print(result.stderr)
        sys.exit("Falha ao gerar o PDF.")

    print(f"Escrito: {PDF_FILE.relative_to(ROOT)} ({PDF_FILE.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
