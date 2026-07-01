"""PDF text extraction using PyPDF2 with fallback options."""

import logging
from typing import Optional, List, Tuple
from pathlib import Path

try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except (ImportError, pytesseract.TesseractNotFoundError):
    OCR_AVAILABLE = False

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extract text from PDF files with multiple fallback strategies."""

    @staticmethod
    def extract_text(pdf_path: str) -> Tuple[str, str]:
        """
        Extract text from PDF file.

        Returns:
            Tuple[str, str]: (extracted_text, extraction_method)
            extraction_method: "pypdf2", "ocr", or "unsupported"
        """
        try:
            # Try PyPDF2 first (fast, for text-based PDFs)
            if PYPDF2_AVAILABLE:
                text = PDFExtractor._extract_with_pypdf2(pdf_path)
                if text and len(text.strip()) > 100:  # At least 100 chars
                    return text, "pypdf2"
                else:
                    logger.warning(f"PyPDF2 extracted minimal text from {pdf_path}, trying OCR")

            # Try OCR as fallback (slower, for scanned PDFs)
            if OCR_AVAILABLE:
                text = PDFExtractor._extract_with_ocr(pdf_path)
                if text and len(text.strip()) > 100:
                    return text, "ocr"
                else:
                    logger.warning(f"OCR extracted minimal text from {pdf_path}")

            # No extraction method available
            logger.error(f"No PDF extraction method available for {pdf_path}")
            return "[PDF extraction unavailable - install PyPDF2 or Tesseract OCR]", "unsupported"

        except Exception as e:
            logger.error(f"Error extracting PDF {pdf_path}: {str(e)}")
            return f"[Error: {str(e)}]", "unsupported"

    @staticmethod
    def _extract_with_pypdf2(pdf_path: str) -> str:
        """Extract text from PDF using PyPDF2."""
        try:
            text_parts = []

            with open(pdf_path, 'rb') as file:
                reader = PdfReader(file)

                # Get total pages for logging
                num_pages = len(reader.pages)
                logger.info(f"Extracting from {num_pages} pages using PyPDF2")

                # Extract text from each page
                for page_num, page in enumerate(reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                            logger.debug(f"Extracted {len(page_text)} chars from page {page_num + 1}")
                    except Exception as e:
                        logger.warning(f"Error extracting page {page_num + 1}: {str(e)}")
                        continue

            full_text = "\n".join(text_parts)
            logger.info(f"PyPDF2 successfully extracted {len(full_text)} characters")
            return full_text

        except Exception as e:
            logger.error(f"PyPDF2 extraction failed: {str(e)}")
            raise

    @staticmethod
    def _extract_with_ocr(pdf_path: str) -> str:
        """Extract text from PDF using OCR (fallback for scanned PDFs)."""
        try:
            logger.info("Starting OCR extraction (slower, for scanned PDFs)")

            # Convert PDF to images and OCR
            text_parts = []

            # For MVP: Simple OCR approach
            # Production: Use pdf2image to convert pages to images first
            logger.warning("OCR extraction requires pdf2image. Install: pip install pdf2image")

            return ""

        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}")
            return ""

    @staticmethod
    def get_pdf_info(pdf_path: str) -> dict:
        """Get PDF metadata and information."""
        try:
            if not PYPDF2_AVAILABLE:
                return {"error": "PyPDF2 not available"}

            with open(pdf_path, 'rb') as file:
                reader = PdfReader(file)

                return {
                    "num_pages": len(reader.pages),
                    "is_encrypted": reader.is_encrypted,
                    "metadata": reader.metadata if reader.metadata else {},
                    "extraction_support": "text_based"
                }

        except Exception as e:
            return {"error": str(e)}


class DocumentTextExtractor:
    """Universal document text extractor for multiple formats."""

    @staticmethod
    def extract(file_path: str) -> Tuple[str, str]:
        """
        Extract text from document (PDF, TXT, or other).

        Returns:
            Tuple[str, str]: (extracted_text, file_type)
        """
        path = Path(file_path)

        if not path.exists():
            return f"[File not found: {file_path}]", "unsupported"

        extension = path.suffix.lower()

        # PDF handling
        if extension == '.pdf':
            text, method = PDFExtractor.extract_text(file_path)
            return text, f"pdf_{method}"

        # TXT handling
        elif extension == '.txt':
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                logger.info(f"Extracted {len(text)} chars from TXT file")
                return text, "txt"
            except Exception as e:
                logger.error(f"TXT extraction failed: {str(e)}")
                return f"[Error reading TXT: {str(e)}]", "unsupported"

        # Excel handling (basic)
        elif extension in ['.xlsx', '.xls']:
            return "[Excel format detected - requires openpyxl for extraction]", "excel"

        # Unsupported format
        else:
            return f"[Unsupported file format: {extension}]", "unsupported"

    @staticmethod
    def get_extraction_capabilities() -> dict:
        """Get information about available extraction methods."""
        return {
            "text": True,
            "pdf_pypdf2": PYPDF2_AVAILABLE,
            "pdf_ocr": OCR_AVAILABLE,
            "excel": False,  # openpyxl not added yet
            "image": False,   # PIL available but OCR not fully setup
        }
