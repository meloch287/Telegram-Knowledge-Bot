from typing import Optional

from src.models import ParseResult, ExtractionMethod, ErrorScenario
from src.parsers.base import DocumentParser

class PDFParser(DocumentParser):

    OCR_THRESHOLD = 50

    def supports(self, file_extension: str) -> bool:
        return self._normalize_extension(file_extension) == "pdf"

    def parse(self, file_path: str) -> ParseResult:
        try:
            import pdfplumber
        except ImportError:
            return ParseResult(
                text="",
                char_count=0,
                success=False,
                extraction_method=ExtractionMethod.PDFPLUMBER,
                error_message="pdfplumber library not installed",
                error_scenario=ErrorScenario.CORRUPTED_FILE,
            )

        try:
            text_parts: list[str] = []

            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)

            full_text = "\n\n".join(text_parts)
            char_count = len(full_text)

            if char_count == 0:
                return ParseResult(
                    text="",
                    char_count=0,
                    success=False,
                    extraction_method=ExtractionMethod.PDFPLUMBER,
                    error_message="Document appears empty or contains only images",
                    error_scenario=ErrorScenario.EMPTY_DOCUMENT,
                )

            return ParseResult(
                text=full_text,
                char_count=char_count,
                success=True,
                extraction_method=ExtractionMethod.PDFPLUMBER,
            )

        except Exception as e:
            error_msg = str(e).lower()

            if "password" in error_msg or "encrypted" in error_msg:
                return ParseResult(
                    text="",
                    char_count=0,
                    success=False,
                    extraction_method=ExtractionMethod.PDFPLUMBER,
                    error_message="PDF is password protected",
                    error_scenario=ErrorScenario.PASSWORD_PROTECTED,
                )

            return ParseResult(
                text="",
                char_count=0,
                success=False,
                extraction_method=ExtractionMethod.PDFPLUMBER,
                error_message=f"Failed to parse PDF: {e}",
                error_scenario=ErrorScenario.CORRUPTED_FILE,
            )

    def needs_ocr(self, text: str) -> bool:
        return len(text.strip()) < self.OCR_THRESHOLD
