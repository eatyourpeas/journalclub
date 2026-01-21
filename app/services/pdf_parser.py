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
        try:
            reader = PdfReader(file_path)
            
            metadata = {
                "pages": len(reader.pages),
                "title": reader.metadata.title if reader.metadata else None,
                "author": reader.metadata.author if reader.metadata else None,
                "subject": reader.metadata.subject if reader.metadata else None,
            }
            
            return metadata
        
        except Exception as e:
            raise Exception(f"Failed to extract metadata from PDF: {str(e)}")