"""
Abstract interface for document text extraction (PDF, DOCX, etc.).
Replaces the original PdfPort with broader document support.
"""

from abc import ABC, abstractmethod


class DocumentPort(ABC):
    """Port for extracting text content from document files."""

    @abstractmethod
    async def extract_text(self, file_bytes: bytes, file_extension: str) -> str:
        """
        Extract all text from a document given its raw bytes.

        Args:
            file_bytes: Raw file content
            file_extension: Lowercase extension without dot (e.g., 'pdf', 'docx')

        Returns:
            Concatenated text from the document.
        """
        ...

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions (without dots)."""
        ...
