from hypothesis import given, strategies as st, settings

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.models.storage import GoogleSheetsRow

@st.composite
def google_sheets_row_strategy(draw):
    timestamp = draw(st.datetimes().map(lambda dt: dt.isoformat()))
    uploader_id = draw(st.text(min_size=1, max_size=20).filter(lambda x: x.strip()))
    uploader_username = draw(st.text(min_size=0, max_size=50))
    file_name = draw(st.text(min_size=1, max_size=255).filter(lambda x: x.strip()))
    file_type = draw(st.sampled_from(["pdf", "docx", "txt", "md"]))
    file_size = draw(st.integers(min_value=0, max_value=20 * 1024 * 1024))
    char_count = draw(st.integers(min_value=0, max_value=1000000))
    language = draw(st.sampled_from(["ru", "en", ""]))
    summary = draw(st.text(min_size=1, max_size=2000).filter(lambda x: x.strip()))
    keywords = draw(st.text(min_size=1, max_size=500).filter(lambda x: x.strip()))
    status = draw(st.sampled_from(["completed", "failed"]))
    error_message = draw(st.text(min_size=0, max_size=500))
    ai_model_used = draw(st.sampled_from(["openai_gpt4", "openai_gpt35", "yandex_gpt", "claude_3", ""]))
    extraction_method = draw(st.sampled_from(["pdfplumber", "python_docx", "plain_read", "tesseract_ocr", ""]))
    ocr_used = draw(st.booleans())
    processing_time = draw(st.floats(min_value=0.0, max_value=300.0, allow_nan=False, allow_infinity=False))

    return GoogleSheetsRow(
        timestamp=timestamp,
        uploader_id=uploader_id,
        uploader_username=uploader_username,
        file_name=file_name,
        file_type=file_type,
        file_size=file_size,
        char_count=char_count,
        language=language,
        summary=summary,
        keywords=keywords,
        status=status,
        error_message=error_message,
        ai_model_used=ai_model_used,
        extraction_method=extraction_method,
        ocr_used=ocr_used,
        processing_time=processing_time,
    )

@settings(max_examples=100)
@given(row=google_sheets_row_strategy())
def test_google_sheets_row_completeness(row: GoogleSheetsRow):
    assert row.has_required_fields(), (
        f"Row missing required fields: "
        f"timestamp={bool(row.timestamp)}, "
        f"uploader_id={bool(row.uploader_id)}, "
        f"uploader_username={bool(row.uploader_username)}, "
        f"file_name={bool(row.file_name)}, "
        f"summary={bool(row.summary)}, "
        f"keywords={bool(row.keywords)}"
    )

@settings(max_examples=100)
@given(row=google_sheets_row_strategy())
def test_google_sheets_row_to_list_contains_all_fields(row: GoogleSheetsRow):
    row_list = row.to_list()

    assert len(row_list) == 16, f"Expected 16 columns, got {len(row_list)}"

    assert row_list[0] == row.timestamp, "timestamp mismatch"

    assert row_list[1] == row.uploader_id, "uploader_id mismatch"

    assert row_list[3] == row.file_name, "file_name mismatch"

    assert row_list[8] == row.summary, "summary mismatch"

    assert row_list[9] == row.keywords, "keywords mismatch"

@settings(max_examples=100)
@given(row=google_sheets_row_strategy())
def test_google_sheets_row_to_list_preserves_all_values(row: GoogleSheetsRow):
    row_list = row.to_list()

    assert row_list[0] == row.timestamp
    assert row_list[1] == row.uploader_id
    assert row_list[2] == row.uploader_username
    assert row_list[3] == row.file_name
    assert row_list[4] == row.file_type
    assert row_list[5] == row.file_size
    assert row_list[6] == row.char_count
    assert row_list[7] == row.language
    assert row_list[8] == row.summary
    assert row_list[9] == row.keywords
    assert row_list[10] == row.status
    assert row_list[11] == row.error_message
    assert row_list[12] == row.ai_model_used
    assert row_list[13] == row.extraction_method
    assert row_list[14] == str(row.ocr_used)
    assert row_list[15] == row.processing_time
