from dataclasses import dataclass
from typing import Optional

from src.models.enums import ErrorScenario

@dataclass
class NotificationTemplates:

    PROCESSING_STARTED: str = "⏳ Обработка документа..."

    PROCESSING_COMPLETE: str = (
        "✅ Документ обработан!\n\n"
        "<b>Суммаризация:</b>\n{summary}\n\n"
        "<b>Ключевые слова:</b>\n{keywords}"
    )

    ERROR_UNSUPPORTED_FORMAT: str = (
        "❌ Формат файла не поддерживается.\n"
        "Поддерживаемые форматы: PDF, DOCX, TXT, MD"
    )

    ERROR_FILE_TOO_LARGE: str = (
        "❌ Файл слишком большой.\n"
        "Максимальный размер: {max_size}MB"
    )

    ERROR_CORRUPTED: str = "❌ Не удалось прочитать файл. Возможно, файл повреждён"

    ERROR_PASSWORD: str = "❌ Файл защищён паролем. Пожалуйста, снимите защиту"

    ERROR_EMPTY: str = "❌ Документ пуст или не содержит текста"

    ERROR_OCR: str = "❌ Не удалось распознать текст. Качество документа недостаточное"

    ERROR_API: str = "❌ Ошибка при обработке текста. Попробуйте позже"

    ERROR_STORAGE: str = "❌ Ошибка сохранения результатов. Попробуйте позже"

    ERROR_URL: str = "❌ Не удалось загрузить файл по ссылке. Проверьте URL"

    INSTRUCTIONS: str = "📄 Отправьте мне документ (PDF, DOCX, TXT, MD) или ссылку на файл"

DEFAULT_MAX_FILE_SIZE_MB = 20

class NotificationService:

    def __init__(
        self,
        templates: Optional[NotificationTemplates] = None,
        max_file_size_mb: int = DEFAULT_MAX_FILE_SIZE_MB,
    ) -> None:
        self.templates = templates or NotificationTemplates()
        self.max_file_size_mb = max_file_size_mb

    def get_processing_started_message(self) -> str:
        return self.templates.PROCESSING_STARTED

    def get_processing_complete_message(
        self,
        summary: str,
        keywords: str,
    ) -> str:
        return self.templates.PROCESSING_COMPLETE.format(
            summary=summary,
            keywords=keywords,
        )

    def get_instructions_message(self) -> str:
        return self.templates.INSTRUCTIONS

    def get_error_message(self, error_scenario: ErrorScenario) -> str:
        error_messages = {
            ErrorScenario.FILE_TOO_LARGE: self.templates.ERROR_FILE_TOO_LARGE.format(
                max_size=self.max_file_size_mb
            ),
            ErrorScenario.UNSUPPORTED_FORMAT: self.templates.ERROR_UNSUPPORTED_FORMAT,
            ErrorScenario.CORRUPTED_FILE: self.templates.ERROR_CORRUPTED,
            ErrorScenario.PASSWORD_PROTECTED: self.templates.ERROR_PASSWORD,
            ErrorScenario.EMPTY_DOCUMENT: self.templates.ERROR_EMPTY,
            ErrorScenario.OCR_FAILED: self.templates.ERROR_OCR,
            ErrorScenario.API_RATE_LIMIT: self.templates.ERROR_API,
            ErrorScenario.API_TIMEOUT: self.templates.ERROR_API,
            ErrorScenario.API_ERROR: self.templates.ERROR_API,
            ErrorScenario.SHEETS_AUTH_ERROR: self.templates.ERROR_STORAGE,
            ErrorScenario.SHEETS_WRITE_ERROR: self.templates.ERROR_STORAGE,
            ErrorScenario.URL_INVALID: self.templates.ERROR_URL,
        }

        return error_messages.get(
            error_scenario,
            "❌ Произошла неизвестная ошибка. Попробуйте позже"
        )

    def get_error_message_from_validation(
        self,
        error_scenario: Optional[ErrorScenario],
        error_message: Optional[str] = None,
    ) -> str:
        if error_scenario:
            return self.get_error_message(error_scenario)

        if error_message:
            return f"❌ {error_message}"

        return "❌ Произошла ошибка валидации. Попробуйте позже"
