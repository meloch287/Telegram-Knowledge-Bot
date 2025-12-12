import re
from typing import Optional
from urllib.parse import urlparse

from src.models.enums import ErrorScenario, FileType
from src.models.results import ValidationResult

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024

SUPPORTED_EXTENSIONS = FileType.supported_extensions()

def validate_file_format(file_name: str) -> ValidationResult:
    if not file_name:
        return ValidationResult(
            is_valid=False,
            error_message="Имя файла не указано",
            error_scenario=ErrorScenario.UNSUPPORTED_FORMAT,
        )

    extension = _extract_extension(file_name)

    if not extension:
        return ValidationResult(
            is_valid=False,
            error_message=f"Формат файла не поддерживается. Поддерживаемые форматы: {', '.join(SUPPORTED_EXTENSIONS).upper()}",
            error_scenario=ErrorScenario.UNSUPPORTED_FORMAT,
        )

    file_type = FileType.from_extension(extension)

    if file_type is None:
        return ValidationResult(
            is_valid=False,
            error_message=f"Формат файла не поддерживается. Поддерживаемые форматы: {', '.join(SUPPORTED_EXTENSIONS).upper()}",
            error_scenario=ErrorScenario.UNSUPPORTED_FORMAT,
        )

    return ValidationResult(is_valid=True)

def validate_file_size(file_size: int, max_size_bytes: int = MAX_FILE_SIZE_BYTES) -> ValidationResult:
    if file_size < 0:
        return ValidationResult(
            is_valid=False,
            error_message="Размер файла не может быть отрицательным",
            error_scenario=ErrorScenario.FILE_TOO_LARGE,
        )

    if file_size > max_size_bytes:
        max_size_mb = max_size_bytes / (1024 * 1024)
        return ValidationResult(
            is_valid=False,
            error_message=f"Файл слишком большой. Максимальный размер: {max_size_mb:.0f}MB",
            error_scenario=ErrorScenario.FILE_TOO_LARGE,
        )

    return ValidationResult(is_valid=True)

def validate_url(url: str) -> ValidationResult:
    if not url:
        return ValidationResult(
            is_valid=False,
            error_message="URL не указан",
            error_scenario=ErrorScenario.URL_INVALID,
        )

    url = url.strip()

    try:
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            return ValidationResult(
                is_valid=False,
                error_message="URL должен начинаться с http:// или https://",
                error_scenario=ErrorScenario.URL_INVALID,
            )

        if not parsed.netloc:
            return ValidationResult(
                is_valid=False,
                error_message="URL не содержит доменного имени",
                error_scenario=ErrorScenario.URL_INVALID,
            )

        if not _is_valid_domain(parsed.netloc):
            return ValidationResult(
                is_valid=False,
                error_message="Некорректное доменное имя в URL",
                error_scenario=ErrorScenario.URL_INVALID,
            )

        return ValidationResult(is_valid=True)

    except Exception:
        return ValidationResult(
            is_valid=False,
            error_message="Некорректный формат URL",
            error_scenario=ErrorScenario.URL_INVALID,
        )

def validate_file(file_name: str, file_size: int) -> ValidationResult:
    format_result = validate_file_format(file_name)
    if not format_result.is_valid:
        return format_result

    size_result = validate_file_size(file_size)
    if not size_result.is_valid:
        return size_result

    return ValidationResult(is_valid=True)

def _extract_extension(file_name: str) -> Optional[str]:
    if not file_name or "." not in file_name:
        return None

    extension = file_name.rsplit(".", 1)[-1].lower()

    return extension if extension else None

def _is_valid_domain(domain: str) -> bool:
    if ":" in domain:
        domain = domain.split(":")[0]

    if not domain:
        return False

    if domain == "localhost":
        return True

    domain_pattern = re.compile(
        r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
    )

    return bool(domain_pattern.match(domain))
