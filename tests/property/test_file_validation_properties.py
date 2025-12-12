import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from hypothesis import given, strategies as st, settings, assume

from src.utils.validators import (
    validate_file_format,
    validate_file_size,
    MAX_FILE_SIZE_BYTES,
    SUPPORTED_EXTENSIONS,
)
from src.models.enums import ErrorScenario

@st.composite
def supported_file_name_strategy(draw):
    base_name = draw(st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-_'),
        min_size=1,
        max_size=50
    ).filter(lambda x: x.strip() and not x.endswith('.')))

    extension = draw(st.sampled_from(SUPPORTED_EXTENSIONS))

    return f"{base_name}.{extension}"

UNSUPPORTED_EXTENSIONS = [
    "exe", "dll", "bat", "sh", "py", "js", "html", "css", "json", "xml",
    "jpg", "jpeg", "png", "gif", "bmp", "svg", "mp3", "mp4", "avi", "mov",
    "zip", "rar", "7z", "tar", "gz", "iso", "bin", "dat", "log", "csv",
    "xls", "xlsx", "ppt", "pptx", "odt", "rtf", "epub", "mobi"
]

@st.composite
def unsupported_file_name_strategy(draw):
    base_name = draw(st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-_'),
        min_size=1,
        max_size=50
    ).filter(lambda x: x.strip() and not x.endswith('.')))

    extension = draw(st.sampled_from(UNSUPPORTED_EXTENSIONS))

    return f"{base_name}.{extension}"

valid_file_size_strategy = st.integers(min_value=0, max_value=MAX_FILE_SIZE_BYTES)

invalid_file_size_strategy = st.integers(min_value=MAX_FILE_SIZE_BYTES + 1, max_value=100 * 1024 * 1024)

@settings(max_examples=100)
@given(file_name=supported_file_name_strategy())
def test_supported_file_formats_acceptance(file_name: str):
    result = validate_file_format(file_name)

    assert result.is_valid, (
        f"File with supported format should be accepted: {file_name}, "
        f"error: {result.error_message}"
    )
    assert result.error_message is None
    assert result.error_scenario is None

@settings(max_examples=100)
@given(file_name=supported_file_name_strategy())
def test_supported_formats_case_insensitive(file_name: str):
    result_upper = validate_file_format(file_name.upper())
    assert result_upper.is_valid, f"Uppercase extension should be accepted: {file_name.upper()}"

    result_lower = validate_file_format(file_name.lower())
    assert result_lower.is_valid, f"Lowercase extension should be accepted: {file_name.lower()}"

@settings(max_examples=100)
@given(file_name=unsupported_file_name_strategy())
def test_unsupported_file_format_rejection(file_name: str):
    result = validate_file_format(file_name)

    assert not result.is_valid, (
        f"File with unsupported format should be rejected: {file_name}"
    )
    assert result.error_scenario == ErrorScenario.UNSUPPORTED_FORMAT
    assert result.error_message is not None

    error_msg_upper = result.error_message.upper()
    for ext in SUPPORTED_EXTENSIONS:
        assert ext.upper() in error_msg_upper, (
            f"Error message should list supported format '{ext}': {result.error_message}"
        )

@settings(max_examples=100)
@given(base_name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip() and '.' not in x))
def test_file_without_extension_rejected(base_name: str):
    result = validate_file_format(base_name)

    assert not result.is_valid, (
        f"File without extension should be rejected: {base_name}"
    )
    assert result.error_scenario == ErrorScenario.UNSUPPORTED_FORMAT

@settings(max_examples=100)
@given(file_size=valid_file_size_strategy)
def test_valid_file_size_acceptance(file_size: int):
    result = validate_file_size(file_size)

    assert result.is_valid, (
        f"File with valid size should be accepted: {file_size} bytes, "
        f"error: {result.error_message}"
    )
    assert result.error_message is None
    assert result.error_scenario is None

@settings(max_examples=100)
@given(file_size=invalid_file_size_strategy)
def test_oversized_file_rejection(file_size: int):
    result = validate_file_size(file_size)

    assert not result.is_valid, (
        f"File exceeding size limit should be rejected: {file_size} bytes"
    )
    assert result.error_scenario == ErrorScenario.FILE_TOO_LARGE
    assert result.error_message is not None
    assert "20" in result.error_message, (
        f"Error message should mention 20MB limit: {result.error_message}"
    )

@settings(max_examples=100)
@given(file_size=st.integers(min_value=-1000, max_value=-1))
def test_negative_file_size_rejection(file_size: int):
    result = validate_file_size(file_size)

    assert not result.is_valid, (
        f"Negative file size should be rejected: {file_size}"
    )
