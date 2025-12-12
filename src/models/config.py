import json
import random
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any

@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True

    def get_delay(self, attempt: int) -> float:
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        if self.jitter:
            delay = delay * (0.5 + random.random())
        return delay

@dataclass
class NotificationMessage:
    chat_id: int
    text: str
    parse_mode: str = "HTML"
    reply_to_message_id: Optional[int] = None
    disable_notification: bool = False

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

@dataclass
class WorkflowConfig:
    telegram_bot_token: str
    telegram_webhook_secret: str

    google_sheet_id: str
    google_credentials_path: str
    google_sheet_name: str = "Documents"

    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"
    yandex_api_key: Optional[str] = None
    yandex_folder_id: Optional[str] = None
    claude_api_key: Optional[str] = None
    claude_model: str = "claude-3-sonnet-20240229"
    ai_provider: str = "openai"

    ocr_engine: str = "tesseract"
    google_vision_credentials: Optional[str] = None
    tesseract_path: Optional[str] = None
    ocr_language: str = "rus+eng"

    max_file_size_mb: int = 20
    max_text_length: int = 100000
    min_text_for_summary: int = 100
    summary_min_sentences: int = 3
    summary_max_sentences: int = 7
    keywords_min_count: int = 5
    keywords_max_count: int = 10

    max_retries: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 30.0

    log_level: str = "INFO"
    log_file_path: str = "logs/processing.log"
    log_retention_days: int = 30

    webhook_url: str = ""
    webhook_timeout: int = 30

    enable_ocr: bool = True
    enable_url_download: bool = True
    enable_language_detection: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowConfig':
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> 'WorkflowConfig':
        data = json.loads(json_str)
        return cls.from_dict(data)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WorkflowConfig):
            return False
        return self.to_dict() == other.to_dict()
