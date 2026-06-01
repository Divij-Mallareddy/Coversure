import pdfplumber
import re
from fastapi import UploadFile

def extract_text_from_pdf(file: UploadFile) -> str:
    text_parts = []
    with pdfplumber.open(file.file) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(f"[Page {page_number}]\n{_clean_page_text(page_text)}")

    return "\n\n".join(text_parts).strip()


def _clean_page_text(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
