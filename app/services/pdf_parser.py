from pypdf import PdfReader
from pathlib import Path


class PDFParser:
    """Service for parsing PDF documents"""

    def extract_text(self, file_path: str) -> str:
        """
        Extract all text from a PDF file

        Args:
            file_path: Path to the PDF file

        Returns:
            Extracted text as a string
        """
        try:
            reader = PdfReader(file_path)
            text = ""

            for page in reader.pages:
                text += page.extract_text() + "\n\n"

            return text.strip()

        except Exception as e:
            raise Exception(f"Failed to extract text from PDF: {str(e)}")

    def extract_metadata(self, file_path: str) -> dict:
        """
        Extract metadata from a PDF file

        Args:
            file_path: Path to the PDF file

        Returns:
            Dictionary containing metadata
        """
        reader = PdfReader(file_path)

        # Page count is the most reliable field — get it first before touching metadata
        try:
            pages = len(reader.pages)
        except Exception:
            pages = 0

        try:
            pdf_meta = reader.metadata or {}
            title = getattr(pdf_meta, "title", None) or pdf_meta.get("/Title")
            author = getattr(pdf_meta, "author", None) or pdf_meta.get("/Author")
            subject = getattr(pdf_meta, "subject", None) or pdf_meta.get("/Subject")
        except Exception:
            title = author = subject = None

        return {
            "pages": pages,
            "title": title or None,
            "author": author or None,
            "subject": subject or None,
        }
