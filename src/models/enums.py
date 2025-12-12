from enum import Enum

class FileType(Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MD = "md"

    @classmethod
    def from_extension(cls, extension: str) -> "FileType | None":
        ext = extension.lower().lstrip(".")
        for file_type in cls:
            if file_type.value == ext:
                return file_type
        return None

    @classmethod
    def supported_extensions(cls) -> list[str]:
        return [ft.value for ft in cls]

class ProcessingStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ErrorScenario(Enum):
    FILE_TOO_LARGE = "file_too_large"
    UNSUPPORTED_FORMAT = "unsupported_format"
    CORRUPTED_FILE = "corrupted_file"
    PASSWORD_PROTECTED = "password_protected"
    EMPTY_DOCUMENT = "empty_document"
    OCR_FAILED = "ocr_failed"
    API_RATE_LIMIT = "api_rate_limit"
    API_TIMEOUT = "api_timeout"
    API_ERROR = "api_error"
    SHEETS_AUTH_ERROR = "sheets_auth_error"
    SHEETS_WRITE_ERROR = "sheets_write_error"
    URL_INVALID = "url_invalid"

class ExtractionMethod(Enum):
    PYPDF2 = "pypdf2"
    PDFPLUMBER = "pdfplumber"
    PYTHON_DOCX = "python_docx"
    PLAIN_READ = "plain_read"
    TESSERACT_OCR = "tesseract_ocr"
    GOOGLE_VISION_OCR = "google_vision_ocr"

class AIModel(Enum):
    OPENAI_GPT4 = "openai_gpt4"
    OPENAI_GPT35 = "openai_gpt35"
    YANDEX_GPT = "yandex_gpt"
    CLAUDE_3 = "claude_3"
    CLAUDE_2 = "claude_2"
