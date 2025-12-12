import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from hypothesis import given, strategies as st, settings, assume

from src.bot.handlers import TelegramBotHandler
from src.models.enums import FileType
from src.utils.validators import SUPPORTED_EXTENSIONS

@st.composite
def valid_file_name_strategy(draw):
    base_name = draw(st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='-_'),
        min_size=1,
        max_size=50
    ).filter(lambda x: x.strip() and not x.endswith('.')))

    extension = draw(st.sampled_from(SUPPORTED_EXTENSIONS))

    return f"{base_name}.{extension}"

@st.composite
def valid_file_info_strategy(draw):
    file_name = draw(valid_file_name_strategy())
    file_size = draw(st.integers(min_value=1, max_value=20 * 1024 * 1024))
    file_id = draw(st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N')),
        min_size=10,
        max_size=100
    ).filter(lambda x: x.strip()))

    return {
        "file_name": file_name,
        "file_size": file_size,
        "file_id": file_id,
    }

@st.composite
def valid_user_info_strategy(draw):
    user_id = draw(st.integers(min_value=1, max_value=10**12))

    has_username = draw(st.booleans())
    username = None
    if has_username:
        username = draw(st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_'),
            min_size=5,
            max_size=32
        ).filter(lambda x: x.strip()))

    return {
        "id": user_id,
        "username": username,
    }

@settings(max_examples=100)
@given(
    file_info=valid_file_info_strategy(),
    user_info=valid_user_info_strategy(),
)
def test_metadata_extraction_completeness(
    file_info: dict,
    user_info: dict,
):
    handler = TelegramBotHandler(
        token="test_token",
        webhook_url="https://example.com/webhook",
    )

    metadata = handler.extract_metadata(file_info, user_info)

    assert metadata.file_name, "file_name should not be empty"
    assert metadata.file_name.strip(), "file_name should not be whitespace only"

    assert metadata.file_size >= 0, "file_size should be non-negative"

    assert metadata.file_type is not None, "file_type should not be None"
    assert isinstance(metadata.file_type, FileType), "file_type should be a FileType enum"

    assert metadata.uploader_id is not None, "uploader_id should not be None"
    assert isinstance(metadata.uploader_id, int), "uploader_id should be an integer"
    assert metadata.uploader_id > 0, "uploader_id should be positive"

    assert metadata.is_complete(), (
        f"Metadata should be complete: file_name={metadata.file_name}, "
        f"file_size={metadata.file_size}, file_type={metadata.file_type}, "
        f"uploader_id={metadata.uploader_id}"
    )

@settings(max_examples=100)
@given(
    file_info=valid_file_info_strategy(),
    user_info=valid_user_info_strategy(),
)
def test_metadata_preserves_original_values(
    file_info: dict,
    user_info: dict,
):
    handler = TelegramBotHandler(
        token="test_token",
        webhook_url="https://example.com/webhook",
    )

    metadata = handler.extract_metadata(file_info, user_info)

    assert metadata.file_name == file_info["file_name"], (
        f"file_name should be preserved: expected {file_info['file_name']}, "
        f"got {metadata.file_name}"
    )

    assert metadata.file_size == file_info["file_size"], (
        f"file_size should be preserved: expected {file_info['file_size']}, "
        f"got {metadata.file_size}"
    )

    assert metadata.uploader_id == user_info["id"], (
        f"uploader_id should be preserved: expected {user_info['id']}, "
        f"got {metadata.uploader_id}"
    )

    if user_info.get("username"):
        assert metadata.uploader_username == user_info["username"], (
            f"uploader_username should be preserved: expected {user_info['username']}, "
            f"got {metadata.uploader_username}"
        )

@settings(max_examples=100)
@given(
    file_info=valid_file_info_strategy(),
    user_info=valid_user_info_strategy(),
)
def test_metadata_file_type_matches_extension(
    file_info: dict,
    user_info: dict,
):
    handler = TelegramBotHandler(
        token="test_token",
        webhook_url="https://example.com/webhook",
    )

    metadata = handler.extract_metadata(file_info, user_info)

    file_name = file_info["file_name"]
    extension = file_name.rsplit(".", 1)[-1].lower()

    assert metadata.file_type.value == extension, (
        f"file_type should match extension: expected {extension}, "
        f"got {metadata.file_type.value}"
    )

@settings(max_examples=100)
@given(
    file_info=valid_file_info_strategy(),
    user_info=valid_user_info_strategy(),
)
def test_metadata_has_timestamp(
    file_info: dict,
    user_info: dict,
):
    handler = TelegramBotHandler(
        token="test_token",
        webhook_url="https://example.com/webhook",
    )

    metadata = handler.extract_metadata(file_info, user_info)

    assert metadata.timestamp is not None, "timestamp should not be None"
