import re
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlparse

from src.models.enums import ErrorScenario, FileType
from src.models.metadata import Metadata
from src.models.results import ValidationResult
from src.utils.validators import (
    MAX_FILE_SIZE_BYTES,
    SUPPORTED_EXTENSIONS,
    validate_file,
    validate_url,
)

class TelegramBotHandler:

    def __init__(
        self,
        token: str,
        webhook_url: str,
        max_file_size: int = MAX_FILE_SIZE_BYTES,
    ) -> None:
        self.token = token
        self.webhook_url = webhook_url
        self.max_file_size = max_file_size

    def validate_file(self, file_info: dict[str, Any]) -> ValidationResult:
        file_name = file_info.get("file_name", "")
        file_size = file_info.get("file_size", 0)

        return validate_file(file_name, file_size)

    def validate_url_input(self, url: str) -> ValidationResult:
        return validate_url(url)

    def extract_metadata(
        self,
        file_info: dict[str, Any],
        user_info: dict[str, Any],
        source_url: Optional[str] = None,
    ) -> Metadata:
        file_name = file_info.get("file_name", "")
        if not file_name:
            raise ValueError("file_name is required")

        file_size = file_info.get("file_size", 0)
        if not isinstance(file_size, int) or file_size < 0:
            raise ValueError("file_size must be a non-negative integer")

        file_type = self._get_file_type(file_name)
        if file_type is None:
            raise ValueError(f"Unsupported file format: {file_name}")

        uploader_id = user_info.get("id")
        if not uploader_id or not isinstance(uploader_id, int):
            raise ValueError("user id is required and must be an integer")

        uploader_username = user_info.get("username")
        telegram_file_id = file_info.get("file_id")

        return Metadata(
            file_name=file_name,
            file_size=file_size,
            file_type=file_type,
            uploader_id=uploader_id,
            uploader_username=uploader_username,
            timestamp=datetime.now(),
            source_url=source_url,
            telegram_file_id=telegram_file_id,
        )

    def extract_url_from_message(self, message_text: str) -> Optional[str]:
        if not message_text:
            return None

        url_pattern = re.compile(
            r'https?://[^\s<>"{}|\\^`\[\]]+'
        )

        match = url_pattern.search(message_text)
        return match.group(0) if match else None

    def get_file_name_from_url(self, url: str) -> Optional[str]:
        if not url:
            return None

        try:
            parsed = urlparse(url)
            path = parsed.path

            if not path or path == "/":
                return None

            file_name = path.rsplit("/", 1)[-1]

            if "?" in file_name:
                file_name = file_name.split("?")[0]

            return file_name if file_name else None

        except Exception:
            return None

    def is_document_message(self, message: dict[str, Any]) -> bool:
        return "document" in message and message["document"] is not None

    def is_url_message(self, message: dict[str, Any]) -> bool:
        text = message.get("text", "")
        if not text:
            return False

        url = self.extract_url_from_message(text)
        return url is not None

    def get_message_type(self, message: dict[str, Any]) -> str:
        if self.is_document_message(message):
            return "document"

        if self.is_url_message(message):
            return "url"

        if message.get("text"):
            return "text"

        return "unknown"

    def _get_file_type(self, file_name: str) -> Optional[FileType]:
        if not file_name or "." not in file_name:
            return None

        extension = file_name.rsplit(".", 1)[-1].lower()
        return FileType.from_extension(extension)

    def get_supported_formats_message(self) -> str:
        formats = ", ".join(ext.upper() for ext in SUPPORTED_EXTENSIONS)
        return f"Поддерживаемые форматы: {formats}"
