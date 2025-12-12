import sys
import os
import tempfile
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from hypothesis import given, strategies as st, settings, assume

from src.utils.logger import ProcessingLogger
from src.models.enums import FileType, ErrorScenario
from src.models.metadata import Metadata
from src.models.storage import LogEntry

@st.composite
def valid_metadata_strategy(draw):
    file_name = draw(st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-_'),
        min_size=1,
        max_size=50
    ).filter(lambda x: x.strip() and not x.endswith('.')))

    extension = draw(st.sampled_from(['pdf', 'docx', 'txt', 'md']))
    full_file_name = f"{file_name}.{extension}"

    file_size = draw(st.integers(min_value=1, max_value=20 * 1024 * 1024))
    file_type = FileType.from_extension(extension)
    uploader_id = draw(st.integers(min_value=1, max_value=10**12))

    has_username = draw(st.booleans())
    username = None
    if has_username:
        username = draw(st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_'),
            min_size=5,
            max_size=32
        ).filter(lambda x: x.strip()))

    return Metadata(
        file_name=full_file_name,
        file_size=file_size,
        file_type=file_type,
        uploader_id=uploader_id,
        uploader_username=username,
    )

@st.composite
def extraction_status_strategy(draw):
    status = draw(st.sampled_from(["success", "error"]))
    char_count = draw(st.integers(min_value=0, max_value=1000000))
    extraction_method = draw(st.sampled_from([
        "pypdf2", "pdfplumber", "python_docx", "plain_read", 
        "tesseract_ocr", "google_vision_ocr", None
    ]))
    used_ocr = draw(st.booleans())
    file_name = draw(st.text(min_size=1, max_size=50).filter(lambda x: x.strip()) | st.none())

    return {
        "status": status,
        "char_count": char_count,
        "extraction_method": extraction_method,
        "used_ocr": used_ocr,
        "file_name": file_name,
    }

@st.composite
def api_call_strategy(draw):
    service = draw(st.sampled_from(["openai", "yandex", "claude"]))
    status = draw(st.sampled_from(["success", "error"]))
    model = draw(st.sampled_from([
        "gpt-4", "gpt-3.5-turbo", "yandexgpt-lite", "claude-3-sonnet", None
    ]))
    tokens_used = draw(st.integers(min_value=0, max_value=10000) | st.none())
    response_time = draw(st.floats(min_value=0.0, max_value=60.0) | st.none())

    return {
        "service": service,
        "status": status,
        "model": model,
        "tokens_used": tokens_used,
        "response_time": response_time,
    }

@st.composite
def keyword_extraction_strategy(draw):
    extraction_method = draw(st.sampled_from(["yake", "tfidf", "ai"]))
    keyword_count = draw(st.integers(min_value=0, max_value=20))
    status = draw(st.sampled_from(["success", "error"]))
    language = draw(st.sampled_from(["ru", "en", None]))

    return {
        "extraction_method": extraction_method,
        "keyword_count": keyword_count,
        "status": status,
        "language": language,
    }

@st.composite
def sheets_write_strategy(draw):
    status = draw(st.sampled_from(["success", "error"]))
    row_number = draw(st.integers(min_value=1, max_value=100000) | st.none())
    spreadsheet_id = draw(st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-_'),
        min_size=10,
        max_size=50
    ).filter(lambda x: x.strip()) | st.none())
    sheet_name = draw(st.text(min_size=1, max_size=30).filter(lambda x: x.strip()) | st.none())

    return {
        "status": status,
        "row_number": row_number,
        "spreadsheet_id": spreadsheet_id,
        "sheet_name": sheet_name,
    }

@st.composite
def error_strategy(draw):
    error_type = draw(st.sampled_from([
        "ValidationError", "ParseError", "APIError", "StorageError", "NetworkError"
    ]))
    message = draw(st.text(min_size=1, max_size=200).filter(lambda x: x.strip()))
    trace = draw(st.text(min_size=0, max_size=500) | st.none())
    error_scenario = draw(st.sampled_from(list(ErrorScenario)) | st.none())

    return {
        "error_type": error_type,
        "message": message,
        "trace": trace,
        "error_scenario": error_scenario,
    }

def create_temp_logger():
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False)
    temp_file.close()
    return ProcessingLogger(log_file=temp_file.name), temp_file.name

def cleanup_temp_file(file_path):
    try:
        os.unlink(file_path)
    except OSError:
        pass

def validate_iso_timestamp(timestamp_str: str) -> bool:
    try:
        datetime.fromisoformat(timestamp_str)
        return True
    except (ValueError, TypeError):
        return False

@settings(max_examples=100)
@given(metadata=valid_metadata_strategy())
def test_log_upload_has_iso_timestamp_and_required_details(metadata: Metadata):
    logger, temp_file = create_temp_logger()

    try:
        entry = logger.log_upload(metadata)

        assert entry.timestamp is not None, "timestamp should not be None"
        assert isinstance(entry.timestamp, datetime), "timestamp should be datetime"

        assert entry.event_type == ProcessingLogger.EVENT_UPLOAD, (
            f"event_type should be {ProcessingLogger.EVENT_UPLOAD}, got {entry.event_type}"
        )

        assert "file_name" in entry.details, "file_name should be in details"
        assert "file_size" in entry.details, "file_size should be in details"
        assert "file_type" in entry.details, "file_type should be in details"
        assert "uploader_id" in entry.details, "uploader_id should be in details"

        assert entry.details["file_name"] == metadata.file_name
        assert entry.details["file_size"] == metadata.file_size
        assert entry.details["file_type"] == metadata.file_type.value
        assert entry.details["uploader_id"] == metadata.uploader_id

        entry_dict = entry.to_dict()
        assert validate_iso_timestamp(entry_dict["timestamp"]), (
            f"timestamp should be ISO format, got {entry_dict['timestamp']}"
        )
    finally:
        cleanup_temp_file(temp_file)

@settings(max_examples=100)
@given(params=extraction_status_strategy())
def test_log_extraction_has_iso_timestamp_and_required_details(params: dict):
    logger, temp_file = create_temp_logger()

    try:
        entry = logger.log_extraction(
            status=params["status"],
            char_count=params["char_count"],
            extraction_method=params["extraction_method"],
            used_ocr=params["used_ocr"],
            file_name=params["file_name"],
        )

        assert entry.timestamp is not None, "timestamp should not be None"
        assert isinstance(entry.timestamp, datetime), "timestamp should be datetime"

        assert entry.event_type == ProcessingLogger.EVENT_EXTRACTION

        assert "status" in entry.details, "status should be in details"
        assert "char_count" in entry.details, "char_count should be in details"
        assert entry.details["status"] == params["status"]
        assert entry.details["char_count"] == params["char_count"]

        entry_dict = entry.to_dict()
        assert validate_iso_timestamp(entry_dict["timestamp"])
    finally:
        cleanup_temp_file(temp_file)

@settings(max_examples=100)
@given(params=api_call_strategy())
def test_log_api_call_has_iso_timestamp_and_required_details(params: dict):
    logger, temp_file = create_temp_logger()

    try:
        entry = logger.log_api_call(
            service=params["service"],
            status=params["status"],
            model=params["model"],
            tokens_used=params["tokens_used"],
            response_time=params["response_time"],
        )

        assert entry.timestamp is not None, "timestamp should not be None"
        assert isinstance(entry.timestamp, datetime), "timestamp should be datetime"

        assert entry.event_type == ProcessingLogger.EVENT_API_CALL

        assert "service" in entry.details, "service should be in details"
        assert "status" in entry.details, "status should be in details"
        assert entry.details["service"] == params["service"]
        assert entry.details["status"] == params["status"]

        entry_dict = entry.to_dict()
        assert validate_iso_timestamp(entry_dict["timestamp"])
    finally:
        cleanup_temp_file(temp_file)

@settings(max_examples=100)
@given(params=keyword_extraction_strategy())
def test_log_keywords_has_iso_timestamp_and_required_details(params: dict):
    logger, temp_file = create_temp_logger()

    try:
        entry = logger.log_keywords(
            extraction_method=params["extraction_method"],
            keyword_count=params["keyword_count"],
            status=params["status"],
            language=params["language"],
        )

        assert entry.timestamp is not None, "timestamp should not be None"
        assert isinstance(entry.timestamp, datetime), "timestamp should be datetime"

        assert entry.event_type == ProcessingLogger.EVENT_KEYWORDS

        assert "extraction_method" in entry.details, "extraction_method should be in details"
        assert "keyword_count" in entry.details, "keyword_count should be in details"
        assert entry.details["extraction_method"] == params["extraction_method"]
        assert entry.details["keyword_count"] == params["keyword_count"]

        entry_dict = entry.to_dict()
        assert validate_iso_timestamp(entry_dict["timestamp"])
    finally:
        cleanup_temp_file(temp_file)

@settings(max_examples=100)
@given(params=sheets_write_strategy())
def test_log_sheets_write_has_iso_timestamp_and_required_details(params: dict):
    logger, temp_file = create_temp_logger()

    try:
        entry = logger.log_sheets_write(
            status=params["status"],
            row_number=params["row_number"],
            spreadsheet_id=params["spreadsheet_id"],
            sheet_name=params["sheet_name"],
        )

        assert entry.timestamp is not None, "timestamp should not be None"
        assert isinstance(entry.timestamp, datetime), "timestamp should be datetime"

        assert entry.event_type == ProcessingLogger.EVENT_SHEETS_WRITE

        assert "status" in entry.details, "status should be in details"
        assert entry.details["status"] == params["status"]

        if params["row_number"] is not None:
            assert "row_number" in entry.details
            assert entry.details["row_number"] == params["row_number"]

        entry_dict = entry.to_dict()
        assert validate_iso_timestamp(entry_dict["timestamp"])
    finally:
        cleanup_temp_file(temp_file)

@settings(max_examples=100)
@given(params=error_strategy())
def test_log_error_has_iso_timestamp_and_required_details(params: dict):
    logger, temp_file = create_temp_logger()

    try:
        entry = logger.log_error(
            error_type=params["error_type"],
            message=params["message"],
            trace=params["trace"],
            error_scenario=params["error_scenario"],
        )

        assert entry.timestamp is not None, "timestamp should not be None"
        assert isinstance(entry.timestamp, datetime), "timestamp should be datetime"

        assert entry.event_type == ProcessingLogger.EVENT_ERROR

        assert "error_type" in entry.details, "error_type should be in details"
        assert "message" in entry.details, "message should be in details"
        assert entry.details["error_type"] == params["error_type"]
        assert entry.details["message"] == params["message"]

        assert entry.error == params["message"]

        if params["error_scenario"] is not None:
            assert entry.error_scenario == params["error_scenario"]

        entry_dict = entry.to_dict()
        assert validate_iso_timestamp(entry_dict["timestamp"])
    finally:
        cleanup_temp_file(temp_file)

@settings(max_examples=100)
@given(metadata=valid_metadata_strategy())
def test_log_entries_are_written_to_file_in_json_format(metadata: Metadata):
    logger, temp_file = create_temp_logger()

    try:
        logger.log_upload(metadata)

        with open(temp_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()

        assert content, "Log file should not be empty"

        log_data = json.loads(content)

        assert "timestamp" in log_data, "JSON should have timestamp"
        assert "event_type" in log_data, "JSON should have event_type"
        assert "details" in log_data, "JSON should have details"

        assert validate_iso_timestamp(log_data["timestamp"]), (
            f"timestamp should be ISO format, got {log_data['timestamp']}"
        )

        assert log_data["details"]["file_name"] == metadata.file_name
        assert log_data["details"]["file_size"] == metadata.file_size
    finally:
        cleanup_temp_file(temp_file)

@settings(max_examples=50)
@given(
    metadata=valid_metadata_strategy(),
    extraction_params=extraction_status_strategy(),
    api_params=api_call_strategy(),
)
def test_multiple_log_entries_all_have_timestamps(
    metadata: Metadata,
    extraction_params: dict,
    api_params: dict,
):
    logger, temp_file = create_temp_logger()

    try:
        entry1 = logger.log_upload(metadata)
        entry2 = logger.log_extraction(
            status=extraction_params["status"],
            char_count=extraction_params["char_count"],
        )
        entry3 = logger.log_api_call(
            service=api_params["service"],
            status=api_params["status"],
        )

        for entry in [entry1, entry2, entry3]:
            assert entry.timestamp is not None
            assert isinstance(entry.timestamp, datetime)

            entry_dict = entry.to_dict()
            assert validate_iso_timestamp(entry_dict["timestamp"])

        entries = logger.get_log_entries()
        assert len(entries) == 3, f"Should have 3 entries, got {len(entries)}"

        for entry in entries:
            assert entry.timestamp is not None
            assert isinstance(entry.timestamp, datetime)
    finally:
        cleanup_temp_file(temp_file)
