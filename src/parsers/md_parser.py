from src.models import ParseResult, ExtractionMethod, ErrorScenario
from src.parsers.base import DocumentParser

class MDParser(DocumentParser):

    FALLBACK_ENCODINGS = ["utf-8", "cp1251", "latin-1", "cp1252"]

    def supports(self, file_extension: str) -> bool:
        return self._normalize_extension(file_extension) == "md"

    def parse(self, file_path: str) -> ParseResult:
        last_error = None
        for encoding in self.FALLBACK_ENCODINGS:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    text = f.read()

                char_count = len(text)

                if char_count == 0:
                    return ParseResult(
                        text="",
                        char_count=0,
                        success=False,
                        extraction_method=ExtractionMethod.PLAIN_READ,
                        error_message="Document is empty",
                        error_scenario=ErrorScenario.EMPTY_DOCUMENT,
                    )

                return ParseResult(
                    text=text,
                    char_count=char_count,
                    success=True,
                    extraction_method=ExtractionMethod.PLAIN_READ,
                )

            except (UnicodeDecodeError, LookupError) as e:
                last_error = e
                continue
            except Exception as e:
                return ParseResult(
                    text="",
                    char_count=0,
                    success=False,
                    extraction_method=ExtractionMethod.PLAIN_READ,
                    error_message=f"Failed to read MD file: {e}",
                    error_scenario=ErrorScenario.CORRUPTED_FILE,
                )

        return ParseResult(
            text="",
            char_count=0,
            success=False,
            extraction_method=ExtractionMethod.PLAIN_READ,
            error_message=f"Failed to decode file with any encoding: {last_error}",
            error_scenario=ErrorScenario.CORRUPTED_FILE,
        )
