import json
from hypothesis import given, strategies as st, settings, assume

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.models.config import WorkflowConfig

def non_empty_string(min_size: int = 1, max_size: int = 100):
    return st.text(
        min_size=min_size, 
        max_size=max_size,
        alphabet=st.characters(blacklist_categories=('Cs',), blacklist_characters='\x00')
    ).filter(lambda x: x.strip())

def optional_string(max_size: int = 100):
    return st.one_of(
        st.none(),
        st.text(
            min_size=1, 
            max_size=max_size,
            alphabet=st.characters(blacklist_categories=('Cs',), blacklist_characters='\x00')
        ).filter(lambda x: x.strip())
    )

@st.composite
def workflow_config_strategy(draw):
    telegram_bot_token = draw(non_empty_string(10, 50))
    telegram_webhook_secret = draw(non_empty_string(10, 50))
    google_sheet_id = draw(non_empty_string(10, 50))
    google_credentials_path = draw(non_empty_string(5, 100))

    google_sheet_name = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(blacklist_categories=('Cs',), blacklist_characters='\x00')).filter(lambda x: x.strip()))

    openai_api_key = draw(optional_string(50))
    openai_model = draw(st.sampled_from(["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"]))
    yandex_api_key = draw(optional_string(50))
    yandex_folder_id = draw(optional_string(30))
    claude_api_key = draw(optional_string(50))
    claude_model = draw(st.sampled_from(["claude-3-sonnet-20240229", "claude-3-opus-20240229", "claude-2.1"]))
    ai_provider = draw(st.sampled_from(["openai", "yandex", "claude"]))

    ocr_engine = draw(st.sampled_from(["tesseract", "google_vision"]))
    google_vision_credentials = draw(optional_string(100))
    tesseract_path = draw(optional_string(100))
    ocr_language = draw(st.sampled_from(["rus+eng", "eng", "rus", "deu+eng"]))

    max_file_size_mb = draw(st.integers(min_value=1, max_value=100))
    max_text_length = draw(st.integers(min_value=1000, max_value=500000))
    min_text_for_summary = draw(st.integers(min_value=10, max_value=500))
    summary_min_sentences = draw(st.integers(min_value=1, max_value=5))
    summary_max_sentences = draw(st.integers(min_value=5, max_value=15))
    keywords_min_count = draw(st.integers(min_value=1, max_value=10))
    keywords_max_count = draw(st.integers(min_value=5, max_value=20))

    max_retries = draw(st.integers(min_value=1, max_value=10))
    retry_base_delay = draw(st.floats(min_value=0.1, max_value=5.0, allow_nan=False, allow_infinity=False))
    retry_max_delay = draw(st.floats(min_value=5.0, max_value=120.0, allow_nan=False, allow_infinity=False))

    log_level = draw(st.sampled_from(["DEBUG", "INFO", "WARNING", "ERROR"]))
    log_file_path = draw(non_empty_string(5, 100))
    log_retention_days = draw(st.integers(min_value=1, max_value=365))

    webhook_url = draw(st.text(min_size=0, max_size=200, alphabet=st.characters(blacklist_categories=('Cs',), blacklist_characters='\x00')))
    webhook_timeout = draw(st.integers(min_value=5, max_value=120))

    enable_ocr = draw(st.booleans())
    enable_url_download = draw(st.booleans())
    enable_language_detection = draw(st.booleans())

    return WorkflowConfig(
        telegram_bot_token=telegram_bot_token,
        telegram_webhook_secret=telegram_webhook_secret,
        google_sheet_id=google_sheet_id,
        google_credentials_path=google_credentials_path,
        google_sheet_name=google_sheet_name,
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        yandex_api_key=yandex_api_key,
        yandex_folder_id=yandex_folder_id,
        claude_api_key=claude_api_key,
        claude_model=claude_model,
        ai_provider=ai_provider,
        ocr_engine=ocr_engine,
        google_vision_credentials=google_vision_credentials,
        tesseract_path=tesseract_path,
        ocr_language=ocr_language,
        max_file_size_mb=max_file_size_mb,
        max_text_length=max_text_length,
        min_text_for_summary=min_text_for_summary,
        summary_min_sentences=summary_min_sentences,
        summary_max_sentences=summary_max_sentences,
        keywords_min_count=keywords_min_count,
        keywords_max_count=keywords_max_count,
        max_retries=max_retries,
        retry_base_delay=retry_base_delay,
        retry_max_delay=retry_max_delay,
        log_level=log_level,
        log_file_path=log_file_path,
        log_retention_days=log_retention_days,
        webhook_url=webhook_url,
        webhook_timeout=webhook_timeout,
        enable_ocr=enable_ocr,
        enable_url_download=enable_url_download,
        enable_language_detection=enable_language_detection,
    )

@settings(max_examples=100)
@given(config=workflow_config_strategy())
def test_workflow_config_json_round_trip(config: WorkflowConfig):
    json_str = config.to_json()

    parsed = json.loads(json_str)
    assert isinstance(parsed, dict), "JSON should parse to a dictionary"

    restored_config = WorkflowConfig.from_json(json_str)

    assert config == restored_config, (
        f"Round-trip failed:\n"
        f"Original: {config.to_dict()}\n"
        f"Restored: {restored_config.to_dict()}"
    )

@settings(max_examples=100)
@given(config=workflow_config_strategy())
def test_workflow_config_dict_round_trip(config: WorkflowConfig):
    config_dict = config.to_dict()

    assert 'telegram_bot_token' in config_dict
    assert 'google_sheet_id' in config_dict
    assert 'ai_provider' in config_dict
    assert 'enable_ocr' in config_dict

    restored_config = WorkflowConfig.from_dict(config_dict)

    assert config == restored_config

@settings(max_examples=100)
@given(config=workflow_config_strategy())
def test_workflow_config_json_is_valid_json(config: WorkflowConfig):
    json_str = config.to_json()

    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Invalid JSON produced: {e}")

    assert isinstance(parsed, dict), "JSON should represent a dictionary"

    required_fields = [
        'telegram_bot_token',
        'telegram_webhook_secret', 
        'google_sheet_id',
        'google_credentials_path',
    ]
    for field in required_fields:
        assert field in parsed, f"Missing required field: {field}"

@settings(max_examples=100)
@given(config=workflow_config_strategy())
def test_workflow_config_double_round_trip(config: WorkflowConfig):
    json_str_1 = config.to_json()
    restored_1 = WorkflowConfig.from_json(json_str_1)

    json_str_2 = restored_1.to_json()
    restored_2 = WorkflowConfig.from_json(json_str_2)

    assert restored_1 == restored_2, "Double round-trip should be idempotent"

    assert json_str_1 == json_str_2, "JSON output should be deterministic"
