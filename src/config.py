import os
from typing import Optional

from dotenv import load_dotenv

from src.models.config import WorkflowConfig, RetryConfig

class ConfigurationError(Exception):
    pass

def _get_env(key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    value = os.getenv(key, default)
    if required and not value:
        raise ConfigurationError(f"Required environment variable '{key}' is not set")
    return value

def _get_env_bool(key: str, default: bool = False) -> bool:
    value = os.getenv(key, str(default)).lower()
    return value in ('true', '1', 'yes', 'on')

def _get_env_int(key: str, default: int) -> int:
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        raise ConfigurationError(f"Environment variable '{key}' must be an integer, got '{value}'")

def _get_env_float(key: str, default: float) -> float:
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        raise ConfigurationError(f"Environment variable '{key}' must be a number, got '{value}'")

def load_config(env_path: Optional[str] = None) -> WorkflowConfig:
    if env_path:
        load_dotenv(env_path)
    else:
        load_dotenv()

    ai_provider = _get_env('AI_PROVIDER', 'openai')
    if ai_provider not in ('openai', 'openrouter', 'yandex', 'claude'):
        raise ConfigurationError(
            f"AI_PROVIDER must be 'openai', 'openrouter', 'yandex', or 'claude', got '{ai_provider}'"
        )

    ocr_engine = _get_env('OCR_ENGINE', 'tesseract')
    if ocr_engine not in ('tesseract', 'google_vision'):
        raise ConfigurationError(
            f"OCR_ENGINE must be 'tesseract' or 'google_vision', got '{ocr_engine}'"
        )

    log_level = _get_env('LOG_LEVEL', 'INFO')
    valid_log_levels = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
    if log_level.upper() not in valid_log_levels:
        raise ConfigurationError(
            f"LOG_LEVEL must be one of {valid_log_levels}, got '{log_level}'"
        )

    return WorkflowConfig(
        telegram_bot_token=_get_env('TELEGRAM_BOT_TOKEN', required=True),
        telegram_webhook_secret=_get_env('TELEGRAM_WEBHOOK_SECRET', required=True),

        google_sheet_id=_get_env('GOOGLE_SHEET_ID', required=True),
        google_credentials_path=_get_env(
            'GOOGLE_CREDENTIALS_PATH',
            './credentials/google_service_account.json'
        ),
        google_sheet_name=_get_env('GOOGLE_SHEET_NAME', 'Documents'),

        openai_api_key=_get_env('OPENAI_API_KEY'),
        openai_model=_get_env('OPENAI_MODEL', 'gpt-4'),
        yandex_api_key=_get_env('YANDEX_API_KEY'),
        yandex_folder_id=_get_env('YANDEX_FOLDER_ID'),
        claude_api_key=_get_env('CLAUDE_API_KEY'),
        claude_model=_get_env('CLAUDE_MODEL', 'claude-3-sonnet-20240229'),
        ai_provider=ai_provider,

        ocr_engine=ocr_engine,
        google_vision_credentials=_get_env('GOOGLE_VISION_CREDENTIALS'),
        tesseract_path=_get_env('TESSERACT_PATH'),
        ocr_language=_get_env('TESSERACT_LANG', 'rus+eng'),

        max_file_size_mb=_get_env_int('MAX_FILE_SIZE_MB', 20),
        max_text_length=_get_env_int('MAX_TEXT_LENGTH', 100000),
        min_text_for_summary=_get_env_int('MIN_TEXT_FOR_SUMMARY', 100),
        summary_min_sentences=_get_env_int('SUMMARY_MIN_SENTENCES', 3),
        summary_max_sentences=_get_env_int('SUMMARY_MAX_SENTENCES', 7),
        keywords_min_count=_get_env_int('KEYWORDS_MIN_COUNT', 5),
        keywords_max_count=_get_env_int('KEYWORDS_MAX_COUNT', 10),

        max_retries=_get_env_int('MAX_RETRIES', 3),
        retry_base_delay=_get_env_float('RETRY_BASE_DELAY', 1.0),
        retry_max_delay=_get_env_float('RETRY_MAX_DELAY', 30.0),

        log_level=log_level.upper(),
        log_file_path=_get_env('LOG_FILE_PATH', './logs/processing.log'),
        log_retention_days=_get_env_int('LOG_RETENTION_DAYS', 30),

        webhook_url=_get_env('WEBHOOK_URL', ''),
        webhook_timeout=_get_env_int('WEBHOOK_TIMEOUT', 30),

        enable_ocr=_get_env_bool('ENABLE_OCR', True),
        enable_url_download=_get_env_bool('ENABLE_URL_DOWNLOAD', True),
        enable_language_detection=_get_env_bool('ENABLE_LANGUAGE_DETECTION', True),
    )

def get_retry_config(workflow_config: WorkflowConfig) -> RetryConfig:
    return RetryConfig(
        max_retries=workflow_config.max_retries,
        base_delay=workflow_config.retry_base_delay,
        max_delay=workflow_config.retry_max_delay,
        exponential_base=_get_env_float('RETRY_EXPONENTIAL_BASE', 2.0),
        jitter=_get_env_bool('RETRY_JITTER', True),
    )
