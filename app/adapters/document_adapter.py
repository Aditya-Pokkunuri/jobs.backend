"""
Concrete implementation of DocumentPort supporting PDF and DOCX extraction.
Replaces the original PyPdfAdapter with broader format support.

Production hardening:
  - CPU-bound parsing offloaded to threadpool via asyncio.to_thread()
    to avoid blocking the asyncio event loop during large file processing.
"""

import asyncio
import io

from pypdf import PdfReader

from app.ports.document_port import DocumentPort


class DocumentAdapter(DocumentPort):
    """Extracts text from PDF and DOCX files."""

    _SUPPORTED = ["pdf", "docx"]

    # Minimum characters for a valid document.
    # Scanned PDFs and image-only files typically yield < 50 chars.
    _MIN_TEXT_LENGTH = 50

    async def extract_text(self, file_bytes: bytes, file_extension: str) -> str:
        """
        Route to the correct parser based on file extension.

        Uses asyncio.to_thread() to run synchronous parsing in a
        threadpool worker — prevents blocking the event loop while
        PyPDF2 or python-docx iterates over pages/paragraphs.

        Raises ValueError if:
        - The file type is unsupported
        - The extracted text is too short (likely a scanned/image-only document)
        """
        ext = file_extension.lower().strip(".")

        if ext == "pdf":
            # Offload CPU-bound PDF parsing to threadpool (stdlib, Python 3.9+)
            text = await asyncio.to_thread(self._extract_pdf, file_bytes)
        elif ext == "docx":
            # Offload CPU-bound DOCX parsing to threadpool
            text = await asyncio.to_thread(self._extract_docx, file_bytes)
        else:
            raise ValueError(
                f"Unsupported file type: .{ext}. "
                f"Supported: {', '.join(self._SUPPORTED)}"
            )

        if len(text.strip()) < self._MIN_TEXT_LENGTH:
            raise ValueError(
                "The uploaded document appears to be scanned or image-based. "
                "Please upload a text-based PDF or DOCX file instead."
            )

        return text

    def supported_extensions(self) -> list[str]:
        return self._SUPPORTED.copy()

    @staticmethod
    def _extract_pdf(file_bytes: bytes) -> str:
        """Extract text from all pages of a PDF."""
        reader = PdfReader(io.BytesIO(file_bytes))
        pages: list[str] = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text.strip())
        return "\n\n".join(pages)

    @staticmethod
    def _extract_docx(file_bytes: bytes) -> str:
        """Extract text from all paragraphs of a DOCX."""
        from docx import Document

        doc = Document(io.BytesIO(file_bytes))
        paragraphs: list[str] = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)
        return "\n\n".join(paragraphs)
