import json
import logging
import os
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from src.models.enums import ErrorScenario
from src.models.metadata import Metadata
from src.models.storage import LogEntry

class ProcessingLogger:

    EVENT_UPLOAD = "file_upload"
    EVENT_EXTRACTION = "text_extraction"
    EVENT_API_CALL = "api_call"
    EVENT_KEYWORDS = "keyword_extraction"
    EVENT_SHEETS_WRITE = "sheets_write"
    EVENT_ERROR = "error"

    def __init__(self, log_file: str = "logs/processing.log"):
        self.log_file = log_file
        self._ensure_log_directory()
        self._setup_logger()

    def _ensure_log_directory(self) -> None:
        log_dir = Path(self.log_file).parent
        if log_dir and not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)

    def _setup_logger(self) -> None:
        self.logger = logging.getLogger("processing_logger")
        self.logger.setLevel(logging.INFO)

        self.logger.handlers.clear()

        file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)

        formatter = logging.Formatter("%(message)s")
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)

    def _create_log_entry(
        self,
        event_type: str,
        details: Dict[str, Any],
        error: Optional[str] = None,
        error_scenario: Optional[ErrorScenario] = None,
    ) -> LogEntry:
        return LogEntry(
            timestamp=datetime.now(),
            event_type=event_type,
            details=details,
            error=error,
            error_scenario=error_scenario,
        )

    def _write_log(self, entry: LogEntry) -> None:
        json_str = json.dumps(entry.to_dict(), ensure_ascii=False)
        self.logger.info(json_str)

    def log_upload(self, metadata: Metadata) -> LogEntry:
        details = {
            "file_name": metadata.file_name,
            "file_size": metadata.file_size,
            "file_type": metadata.file_type.value,
            "uploader_id": metadata.uploader_id,
            "uploader_username": metadata.uploader_username,
        }

        if metadata.source_url:
            details["source_url"] = metadata.source_url

        if metadata.telegram_file_id:
            details["telegram_file_id"] = metadata.telegram_file_id

        entry = self._create_log_entry(self.EVENT_UPLOAD, details)
        self._write_log(entry)
        return entry

    def log_extraction(
        self,
        status: str,
        char_count: int,
        extraction_method: Optional[str] = None,
        used_ocr: bool = False,
        file_name: Optional[str] = None,
    ) -> LogEntry:
        details = {
            "status": status,
            "char_count": char_count,
            "used_ocr": used_ocr,
        }

        if extraction_method:
            details["extraction_method"] = extraction_method

        if file_name:
            details["file_name"] = file_name

        entry = self._create_log_entry(self.EVENT_EXTRACTION, details)
        self._write_log(entry)
        return entry

    def log_api_call(
        self,
        service: str,
        status: str,
        model: Optional[str] = None,
        tokens_used: Optional[int] = None,
        response_time: Optional[float] = None,
    ) -> LogEntry:
        details = {
            "service": service,
            "status": status,
        }

        if model:
            details["model"] = model

        if tokens_used is not None:
            details["tokens_used"] = tokens_used

        if response_time is not None:
            details["response_time"] = response_time

        entry = self._create_log_entry(self.EVENT_API_CALL, details)
        self._write_log(entry)
        return entry

    def log_keywords(
        self,
        extraction_method: str,
        keyword_count: int,
        status: str = "success",
        language: Optional[str] = None,
    ) -> LogEntry:
        details = {
            "extraction_method": extraction_method,
            "keyword_count": keyword_count,
            "status": status,
        }

        if language:
            details["language"] = language

        entry = self._create_log_entry(self.EVENT_KEYWORDS, details)
        self._write_log(entry)
        return entry

    def log_sheets_write(
        self,
        status: str,
        row_number: Optional[int] = None,
        spreadsheet_id: Optional[str] = None,
        sheet_name: Optional[str] = None,
    ) -> LogEntry:
        details = {
            "status": status,
        }

        if row_number is not None:
            details["row_number"] = row_number

        if spreadsheet_id:
            details["spreadsheet_id"] = spreadsheet_id

        if sheet_name:
            details["sheet_name"] = sheet_name

        entry = self._create_log_entry(self.EVENT_SHEETS_WRITE, details)
        self._write_log(entry)
        return entry

    def log_error(
        self,
        error_type: str,
        message: str,
        trace: Optional[str] = None,
        error_scenario: Optional[ErrorScenario] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> LogEntry:
        details = {
            "error_type": error_type,
            "message": message,
        }

        if trace is None:
            trace = traceback.format_exc()
            if trace.strip() == "NoneType: None":
                trace = None

        if trace:
            details["stack_trace"] = trace

        if context:
            details["context"] = context

        entry = self._create_log_entry(
            self.EVENT_ERROR,
            details,
            error=message,
            error_scenario=error_scenario,
        )
        self._write_log(entry)
        return entry

    def get_log_entries(self, limit: Optional[int] = None) -> list[LogEntry]:
        entries = []

        if not os.path.exists(self.log_file):
            return entries

        with open(self.log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                entry = LogEntry(
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    event_type=data["event_type"],
                    details=data["details"],
                    error=data.get("error"),
                    error_scenario=(
                        ErrorScenario(data["error_scenario"])
                        if data.get("error_scenario")
                        else None
                    ),
                )
                entries.append(entry)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

        if limit:
            entries = entries[-limit:]

        return entries
