from typing import Any, Optional

from src.models.enums import ErrorScenario
from src.models.results import ValidationResult
from src.utils.validators import (
    MAX_FILE_SIZE_BYTES,
    SUPPORTED_EXTENSIONS,
    validate_file,
    validate_file_format,
    validate_file_size,
    validate_url,
)

class BotValidator:

    def __init__(
        self,
        max_file_size: int = MAX_FILE_SIZE_BYTES,
        supported_extensions: Optional[list[str]] = None,
    ) -> None:
        self.max_file_size = max_file_size
        self.supported_extensions = supported_extensions or SUPPORTED_EXTENSIONS

    def validate_document(self, document: dict[str, Any]) -> ValidationResult:
        if not document:
            return ValidationResult(
                is_valid=False,
                error_message="Документ не найден",
                error_scenario=ErrorScenario.UNSUPPORTED_FORMAT,
            )

        file_name = document.get("file_name", "")
        file_size = document.get("file_size", 0)

        format_result = validate_file_format(file_name)
        if not format_result.is_valid:
            return format_result

        size_result = validate_file_size(file_size, self.max_file_size)
        if not size_result.is_valid:
            return size_result

        return ValidationResult(is_valid=True)

    def validate_url_message(self, url: str) -> ValidationResult:
        return validate_url(url)

    def validate_message(self, message: dict[str, Any]) -> ValidationResult:
        if "document" in message and message["document"]:
            return self.validate_document(message["document"])

        text = message.get("text", "")
        if text:
            import re
            url_pattern = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')
            match = url_pattern.search(text)

            if match:
                return self.validate_url_message(match.group(0))

        return ValidationResult(
            is_valid=False,
            error_message="Отправьте документ или ссылку на файл",
            error_scenario=None,
        )

    def is_supported_format(self, file_name: str) -> bool:
        result = validate_file_format(file_name)
        return result.is_valid

    def is_within_size_limit(self, file_size: int) -> bool:
        result = validate_file_size(file_size, self.max_file_size)
        return result.is_valid

    def get_validation_error_scenario(
        self,
        file_name: str,
        file_size: int,
    ) -> Optional[ErrorScenario]:
        result = validate_file(file_name, file_size)
        return result.error_scenario
