from src.models import ParseResult, ExtractionMethod, ErrorScenario
from src.parsers.base import DocumentParser

class TXTParser(DocumentParser):

    FALLBACK_ENCODINGS = ["utf-8", "cp1251", "latin-1", "cp1252"]

    def supports(self, file_extension: str) -> bool:
        return self._normalize_extension(file_extension) == "txt"

    def parse(self, file_path: str) -> ParseResult:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
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
        except UnicodeDecodeError:
            pass

        encoding = self._detect_encoding(file_path)

        encodings_to_try = [encoding] if encoding and encoding.lower() != "utf-8" else []
        encodings_to_try.extend(
            e for e in self.FALLBACK_ENCODINGS if e != encoding and e != "utf-8"
        )

        last_error = None
        for enc in encodings_to_try:
            try:
                with open(file_path, "r", encoding=enc) as f:
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
                    error_message=f"Failed to read TXT file: {e}",
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

    def _detect_encoding(self, file_path: str) -> str | None:
        try:
            import chardet

            with open(file_path, "rb") as f:
                raw_data = f.read()

            result = chardet.detect(raw_data)
            if result and result.get("encoding"):
                return result["encoding"]
        except ImportError:
            pass
        except Exception:
            pass

        return None
