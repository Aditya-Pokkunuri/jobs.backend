"""
Abstract interface for PDF text extraction.
"""

from abc import ABC, abstractmethod


class PdfPort(ABC):
    """Port for extracting text content from PDF files."""

    @abstractmethod
    async def extract_text(self, file_bytes: bytes) -> str:
        """
        Extract all text from a PDF given its raw bytes.
        Returns concatenated text from all pages.
        """
        ...
