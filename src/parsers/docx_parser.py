from src.models import ParseResult, ExtractionMethod, ErrorScenario
from src.parsers.base import DocumentParser

class DOCXParser(DocumentParser):

    def supports(self, file_extension: str) -> bool:
        return self._normalize_extension(file_extension) == "docx"

    def parse(self, file_path: str) -> ParseResult:
        try:
            from docx import Document
        except ImportError:
            return ParseResult(
                text="",
                char_count=0,
                success=False,
                extraction_method=ExtractionMethod.PYTHON_DOCX,
                error_message="python-docx library not installed",
                error_scenario=ErrorScenario.CORRUPTED_FILE,
            )

        try:
            doc = Document(file_path)

            paragraphs: list[str] = []
            for para in doc.paragraphs:
                text = para.text.strip()
                if text:
                    paragraphs.append(text)

            full_text = "\n\n".join(paragraphs)
            char_count = len(full_text)

            if char_count == 0:
                return ParseResult(
                    text="",
                    char_count=0,
                    success=False,
                    extraction_method=ExtractionMethod.PYTHON_DOCX,
                    error_message="Document appears empty",
                    error_scenario=ErrorScenario.EMPTY_DOCUMENT,
                )

            return ParseResult(
                text=full_text,
                char_count=char_count,
                success=True,
                extraction_method=ExtractionMethod.PYTHON_DOCX,
            )

        except Exception as e:
            error_msg = str(e).lower()

            if "not a valid" in error_msg or "corrupt" in error_msg:
                return ParseResult(
                    text="",
                    char_count=0,
                    success=False,
                    extraction_method=ExtractionMethod.PYTHON_DOCX,
                    error_message="File is corrupted or not a valid DOCX",
                    error_scenario=ErrorScenario.CORRUPTED_FILE,
                )

            return ParseResult(
                text="",
                char_count=0,
                success=False,
                extraction_method=ExtractionMethod.PYTHON_DOCX,
                error_message=f"Failed to parse DOCX: {e}",
                error_scenario=ErrorScenario.CORRUPTED_FILE,
            )
