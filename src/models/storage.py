from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .enums import ErrorScenario

@dataclass
class GoogleSheetsRow:
    timestamp: str
    uploader_id: str
    uploader_username: str
    file_name: str
    file_type: str
    file_size: int
    char_count: int
    language: str
    summary: str
    keywords: str
    status: str
    error_message: str
    ai_model_used: str
    extraction_method: str
    ocr_used: bool
    processing_time: float

    def to_list(self) -> List[Any]:
        return [
            self.timestamp,
            self.uploader_id,
            self.uploader_username,
            self.file_name,
            self.file_type,
            self.file_size,
            self.char_count,
            self.language,
            self.summary,
            self.keywords,
            self.status,
            self.error_message,
            self.ai_model_used,
            self.extraction_method,
            str(self.ocr_used),
            self.processing_time,
        ]

    def has_required_fields(self) -> bool:
        return bool(
            self.timestamp and
            (self.uploader_id or self.uploader_username) and
            self.file_name and
            self.summary and
            self.keywords
        )

@dataclass
class RowInfo:
    row_number: int
    timestamp: datetime
    success: bool

@dataclass
class LogEntry:
    timestamp: datetime
    event_type: str
    details: Dict[str, Any]
    error: Optional[str] = None
    error_scenario: Optional[ErrorScenario] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "details": self.details,
        }
        if self.error:
            result["error"] = self.error
        if self.error_scenario:
            result["error_scenario"] = self.error_scenario.value
        return result
