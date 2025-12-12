from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .enums import FileType

@dataclass
class Metadata:
    file_name: str
    file_size: int
    file_type: FileType
    uploader_id: int
    timestamp: datetime = field(default_factory=datetime.now)
    uploader_username: Optional[str] = None
    language: Optional[str] = None
    source_url: Optional[str] = None
    telegram_file_id: Optional[str] = None

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not self.file_name or not self.file_name.strip():
            raise ValueError("file_name cannot be empty")

        if self.file_size < 0:
            raise ValueError("file_size cannot be negative")

        if not isinstance(self.file_type, FileType):
            raise ValueError(f"file_type must be a FileType enum, got {type(self.file_type)}")

        if not isinstance(self.uploader_id, int) or self.uploader_id <= 0:
            raise ValueError("uploader_id must be a positive integer")

    def is_complete(self) -> bool:
        return bool(
            self.file_name and 
            self.file_name.strip() and
            self.file_size >= 0 and
            isinstance(self.file_type, FileType) and
            isinstance(self.uploader_id, int) and
            self.uploader_id > 0
        )
