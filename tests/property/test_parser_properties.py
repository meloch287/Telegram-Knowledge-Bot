import sys
import os
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from hypothesis import given, strategies as st, settings, assume

from src.parsers.txt_parser import TXTParser
from src.parsers.md_parser import MDParser
from src.parsers.factory import ParserFactory
from src.models import ExtractionMethod

text_content_strategy = st.text(
    alphabet=st.characters(
        blacklist_categories=('Cs',),
        blacklist_characters='\x00\r',
    ),
    min_size=1,
    max_size=10000
).filter(lambda x: x.strip())

@st.composite
def markdown_content_strategy(draw):
    elements = []

    if draw(st.booleans()):
        level = draw(st.integers(min_value=1, max_value=6))
        heading_text = draw(st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs')),
            min_size=1,
            max_size=50
        ).filter(lambda x: x.strip()))
        elements.append(f"{'#' * level} {heading_text}")

    num_paragraphs = draw(st.integers(min_value=1, max_value=5))
    for _ in range(num_paragraphs):
        para = draw(st.text(
            alphabet=st.characters(
                whitelist_categories=('L', 'N', 'Zs', 'P'),
                blacklist_characters='\x00'
            ),
            min_size=1,
            max_size=200
        ).filter(lambda x: x.strip()))
        elements.append(para)

    if draw(st.booleans()):
        num_items = draw(st.integers(min_value=1, max_value=5))
        for i in range(num_items):
            item = draw(st.text(
                alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs')),
                min_size=1,
                max_size=50
            ).filter(lambda x: x.strip()))
            elements.append(f"- {item}")

    return "\n\n".join(elements)

@settings(max_examples=100)
@given(content=text_content_strategy)
def test_txt_round_trip(content: str):
    parser = TXTParser()

    with tempfile.NamedTemporaryFile(
        mode='w', 
        suffix='.txt', 
        encoding='utf-8',
        delete=False
    ) as f:
        f.write(content)
        temp_path = f.name

    try:
        result = parser.parse(temp_path)

        assert result.success, f"Parsing should succeed: {result.error_message}"
        assert result.text == content, (
            f"Round-trip should preserve content.\n"
            f"Original length: {len(content)}\n"
            f"Parsed length: {len(result.text)}"
        )
        assert result.char_count == len(content), (
            f"Character count should match: expected {len(content)}, got {result.char_count}"
        )
        assert result.extraction_method == ExtractionMethod.PLAIN_READ
    finally:
        os.unlink(temp_path)

@settings(max_examples=100)
@given(content=markdown_content_strategy())
def test_md_round_trip(content: str):
    parser = MDParser()

    with tempfile.NamedTemporaryFile(
        mode='w', 
        suffix='.md', 
        encoding='utf-8',
        delete=False
    ) as f:
        f.write(content)
        temp_path = f.name

    try:
        result = parser.parse(temp_path)

        assert result.success, f"Parsing should succeed: {result.error_message}"
        assert result.text == content, (
            f"Round-trip should preserve markdown structure.\n"
            f"Original: {content[:100]}...\n"
            f"Parsed: {result.text[:100]}..."
        )
        assert result.char_count == len(content), (
            f"Character count should match: expected {len(content)}, got {result.char_count}"
        )

        if content.startswith('#'):
            assert result.text.startswith('#'), "Heading structure should be preserved"
        if '- ' in content:
            assert '- ' in result.text, "List structure should be preserved"
    finally:
        os.unlink(temp_path)

@settings(max_examples=100)
@given(content=text_content_strategy)
def test_parse_result_completeness_txt(content: str):
    parser = TXTParser()

    with tempfile.NamedTemporaryFile(
        mode='w', 
        suffix='.txt', 
        encoding='utf-8',
        delete=False
    ) as f:
        f.write(content)
        temp_path = f.name

    try:
        result = parser.parse(temp_path)

        assert result.success, f"Parsing should succeed: {result.error_message}"
        assert result.text is not None, "Text should not be None"
        assert len(result.text) > 0, "Text should not be empty"
        assert result.char_count == len(result.text), (
            f"char_count should equal len(text): {result.char_count} != {len(result.text)}"
        )
        assert result.extraction_method is not None, "extraction_method should be set"
    finally:
        os.unlink(temp_path)

@settings(max_examples=100)
@given(content=markdown_content_strategy())
def test_parse_result_completeness_md(content: str):
    parser = MDParser()

    with tempfile.NamedTemporaryFile(
        mode='w', 
        suffix='.md', 
        encoding='utf-8',
        delete=False
    ) as f:
        f.write(content)
        temp_path = f.name

    try:
        result = parser.parse(temp_path)

        assert result.success, f"Parsing should succeed: {result.error_message}"
        assert result.text is not None, "Text should not be None"
        assert len(result.text) > 0, "Text should not be empty"
        assert result.char_count == len(result.text), (
            f"char_count should equal len(text): {result.char_count} != {len(result.text)}"
        )
        assert result.extraction_method is not None, "extraction_method should be set"
    finally:
        os.unlink(temp_path)

@settings(max_examples=50)
@given(
    content=text_content_strategy,
    extension=st.sampled_from(['txt', 'md'])
)
def test_parse_result_completeness_via_factory(content: str, extension: str):
    factory = ParserFactory()

    with tempfile.NamedTemporaryFile(
        mode='w', 
        suffix=f'.{extension}', 
        encoding='utf-8',
        delete=False
    ) as f:
        f.write(content)
        temp_path = f.name

    try:
        parser = factory.get_parser(temp_path)
        assert parser is not None, f"Factory should return parser for .{extension}"

        result = parser.parse(temp_path)

        assert result.success, f"Parsing should succeed: {result.error_message}"
        assert result.text is not None, "Text should not be None"
        assert len(result.text) > 0, "Text should not be empty"
        assert result.char_count == len(result.text), (
            f"char_count should equal len(text): {result.char_count} != {len(result.text)}"
        )
        assert result.extraction_method is not None, "extraction_method should be set"
    finally:
        os.unlink(temp_path)
