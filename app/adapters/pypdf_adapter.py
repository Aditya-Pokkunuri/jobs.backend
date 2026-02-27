"""
Concrete implementation of PdfPort using pypdf.
"""

import io

from pypdf import PdfReader

from app.ports.pdf_port import PdfPort


class PyPdfAdapter(PdfPort):
    """Extracts text from PDF files using pypdf."""

    async def extract_text(self, file_bytes: bytes) -> str:
        """Read all pages and concatenate text."""

        reader = PdfReader(io.BytesIO(file_bytes))
        pages_text: list[str] = []

        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text.strip())

        return "\n\n".join(pages_text)
