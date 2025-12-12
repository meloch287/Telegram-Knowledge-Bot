import logging
from datetime import datetime
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

from src.models.config import RetryConfig
from src.models.enums import ErrorScenario
from src.models.results import ProcessingResult
from src.models.storage import GoogleSheetsRow, RowInfo
from src.utils.retry_handler import RetryHandler

logger = logging.getLogger(__name__)

class GoogleSheetsStorageError(Exception):

    def __init__(self, message: str, error_scenario: Optional[ErrorScenario] = None):
        super().__init__(message)
        self.error_scenario = error_scenario

class GoogleSheetsStorage:

    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive',
    ]

    def __init__(
        self,
        credentials_path: str,
        spreadsheet_id: str,
        sheet_name: str = "Documents",
        retry_config: Optional[RetryConfig] = None,
    ):
        self.credentials_path = credentials_path
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name
        self.retry_config = retry_config or RetryConfig()
        self.retry_handler = RetryHandler(self.retry_config)

        self._client: Optional[gspread.Client] = None
        self._spreadsheet: Optional[gspread.Spreadsheet] = None
        self._worksheet: Optional[gspread.Worksheet] = None
        self._authenticated = False

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated and self._client is not None

    def authenticate(self) -> bool:
        try:
            credentials = Credentials.from_service_account_file(
                self.credentials_path,
                scopes=self.SCOPES,
            )
            self._client = gspread.authorize(credentials)
            self._spreadsheet = self._client.open_by_key(self.spreadsheet_id)

            try:
                self._worksheet = self._spreadsheet.worksheet(self.sheet_name)
            except gspread.WorksheetNotFound:
                self._worksheet = self._spreadsheet.add_worksheet(
                    title=self.sheet_name,
                    rows=1000,
                    cols=16,
                )
                self._setup_headers()

            self._authenticated = True
            logger.info(
                f"Successfully authenticated with Google Sheets: {self.spreadsheet_id}"
            )
            return True

        except FileNotFoundError as e:
            logger.error(f"Credentials file not found: {self.credentials_path}")
            raise GoogleSheetsStorageError(
                f"Credentials file not found: {self.credentials_path}",
                ErrorScenario.SHEETS_AUTH_ERROR,
            ) from e
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise GoogleSheetsStorageError(
                f"Authentication failed: {e}",
                ErrorScenario.SHEETS_AUTH_ERROR,
            ) from e

    def _setup_headers(self) -> None:
        headers = [
            "Timestamp",
            "Uploader ID",
            "Uploader Username",
            "File Name",
            "File Type",
            "File Size (bytes)",
            "Character Count",
            "Language",
            "Summary",
            "Keywords",
            "Status",
            "Error Message",
            "AI Model Used",
            "Extraction Method",
            "OCR Used",
            "Processing Time (s)",
        ]
        if self._worksheet:
            self._worksheet.update('A1:P1', [headers])

    def _ensure_authenticated(self) -> None:
        if not self.is_authenticated:
            self.authenticate()

    def save_result(self, result: ProcessingResult) -> RowInfo:
        self._ensure_authenticated()

        row = self._result_to_row(result)

        if not row.has_required_fields():
            raise GoogleSheetsStorageError(
                "Row missing required fields",
                ErrorScenario.SHEETS_WRITE_ERROR,
            )

        return self._retry_write(row)

    def _result_to_row(self, result: ProcessingResult) -> GoogleSheetsRow:
        return GoogleSheetsRow(
            timestamp=result.metadata.timestamp.isoformat(),
            uploader_id=str(result.metadata.uploader_id),
            uploader_username=result.metadata.uploader_username or "",
            file_name=result.metadata.file_name,
            file_type=result.metadata.file_type.value,
            file_size=result.metadata.file_size,
            char_count=result.parse_result.char_count,
            language=result.summary_result.language,
            summary=result.summary_result.summary,
            keywords=result.keywords_result.formatted,
            status=result.status.value,
            error_message=result.summary_result.error_message or "",
            ai_model_used=result.summary_result.ai_model_used.value,
            extraction_method=result.parse_result.extraction_method.value,
            ocr_used=result.parse_result.used_ocr,
            processing_time=result.processing_time,
        )

    def _retry_write(self, row: GoogleSheetsRow) -> RowInfo:
        def write_operation() -> RowInfo:
            if not self._worksheet:
                raise GoogleSheetsStorageError(
                    "Worksheet not initialized",
                    ErrorScenario.SHEETS_WRITE_ERROR,
                )

            row_data = row.to_list()
            self._worksheet.append_row(row_data)

            row_count = len(self._worksheet.get_all_values())

            return RowInfo(
                row_number=row_count,
                timestamp=datetime.now(),
                success=True,
            )

        try:
            return self.retry_handler.execute_with_retry(
                write_operation,
                retryable_errors=(gspread.exceptions.APIError, Exception),
            )
        except Exception as e:
            logger.error(f"Failed to write to Google Sheets after retries: {e}")
            raise GoogleSheetsStorageError(
                f"Failed to write to Google Sheets: {e}",
                ErrorScenario.SHEETS_WRITE_ERROR,
            ) from e

    def save_row(self, row: GoogleSheetsRow) -> RowInfo:
        self._ensure_authenticated()

        if not row.has_required_fields():
            raise GoogleSheetsStorageError(
                "Row missing required fields",
                ErrorScenario.SHEETS_WRITE_ERROR,
            )

        return self._retry_write(row)

    def get_row_count(self) -> int:
        self._ensure_authenticated()

        if not self._worksheet:
            return 0

        return len(self._worksheet.get_all_values())

    def close(self) -> None:
        self._client = None
        self._spreadsheet = None
        self._worksheet = None
        self._authenticated = False
