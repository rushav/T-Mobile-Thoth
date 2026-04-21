from pathlib import Path
from PyPDF2 import PdfReader
from docx import Document


def extract_text(filepath: str, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return _pdf_text(filepath)
    if ext == ".docx":
        return _docx_text(filepath)
    if ext in (".txt", ".md"):
        return Path(filepath).read_text(encoding="utf-8", errors="ignore")
    # Fallback: try as text
    try:
        return Path(filepath).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _pdf_text(filepath: str) -> str:
    try:
        reader = PdfReader(filepath)
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return "\n\n".join(pages).strip()
    except Exception as e:
        return f"[PDF parse error: {e}]"


def _docx_text(filepath: str) -> str:
    try:
        doc = Document(filepath)
        return "\n".join(p.text for p in doc.paragraphs).strip()
    except Exception as e:
        return f"[DOCX parse error: {e}]"
