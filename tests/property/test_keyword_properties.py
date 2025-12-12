import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from hypothesis import given, strategies as st, settings, assume

from src.ai.keyword_extractor import KeywordExtractor
from src.ai.language_detector import LanguageDetector

@st.composite
def russian_text_strategy(draw):
    russian_words = [
        'документ', 'система', 'данные', 'информация', 'процесс',
        'результат', 'анализ', 'метод', 'функция', 'объект',
        'пользователь', 'файл', 'текст', 'программа', 'модуль',
        'описывает', 'содержит', 'включает', 'определяет', 'использует',
        'основные', 'важные', 'ключевые', 'главные', 'новые',
        'работает', 'выполняет', 'обрабатывает', 'создаёт', 'проверяет',
        'технология', 'разработка', 'приложение', 'интерфейс', 'компонент',
        'архитектура', 'структура', 'алгоритм', 'операция', 'сервис',
    ]

    num_sentences = draw(st.integers(min_value=5, max_value=15))
    sentences = []

    used_words = set()

    for _ in range(num_sentences):
        num_words = draw(st.integers(min_value=8, max_value=20))
        words = []
        for _ in range(num_words):
            available = [w for w in russian_words if w not in used_words]
            if available and len(used_words) < 15:
                word = draw(st.sampled_from(available))
            else:
                word = draw(st.sampled_from(russian_words))
            words.append(word)
            used_words.add(word)
        sentence = ' '.join(words).capitalize() + '.'
        sentences.append(sentence)

    return ' '.join(sentences)

@st.composite
def english_text_strategy(draw):
    content_words = [
        'document', 'system', 'data', 'information', 'process',
        'result', 'analysis', 'method', 'function', 'object',
        'user', 'file', 'text', 'program', 'module',
        'describes', 'contains', 'includes', 'defines', 'uses',
        'main', 'important', 'key', 'primary', 'new',
        'works', 'executes', 'processes', 'creates', 'validates',
        'technology', 'development', 'application', 'interface', 'component',
        'architecture', 'structure', 'algorithm', 'operation', 'service',
    ]

    function_words = ['the', 'a', 'an', 'is', 'are', 'was', 'were', 'be',
                      'have', 'has', 'had', 'do', 'does', 'did', 'will']

    num_sentences = draw(st.integers(min_value=5, max_value=15))
    sentences = []

    used_content_words = set()

    for _ in range(num_sentences):
        num_words = draw(st.integers(min_value=8, max_value=20))
        words = []
        for i in range(num_words):
            if i % 3 == 0:
                word = draw(st.sampled_from(function_words))
            else:
                available = [w for w in content_words if w not in used_content_words]
                if available and len(used_content_words) < 15:
                    word = draw(st.sampled_from(available))
                else:
                    word = draw(st.sampled_from(content_words))
                used_content_words.add(word)
            words.append(word)
        sentence = ' '.join(words).capitalize() + '.'
        sentences.append(sentence)

    return ' '.join(sentences)

@settings(max_examples=100)
@given(text=english_text_strategy())
def test_keyword_count_bounds_english(text: str):
    extractor = KeywordExtractor()
    result = extractor.extract(text)

    if result.success:
        assert 5 <= result.count <= 10, (
            f"Keyword count should be between 5 and 10, got {result.count}"
        )
        assert len(result.keywords) == result.count, (
            f"Keywords list length ({len(result.keywords)}) should match count ({result.count})"
        )

@settings(max_examples=100)
@given(text=russian_text_strategy())
def test_keyword_count_bounds_russian(text: str):
    extractor = KeywordExtractor()
    result = extractor.extract(text, language="ru")

    if result.success:
        assert 5 <= result.count <= 10, (
            f"Keyword count should be between 5 and 10, got {result.count}"
        )
        assert len(result.keywords) == result.count, (
            f"Keywords list length ({len(result.keywords)}) should match count ({result.count})"
        )

@settings(max_examples=100)
@given(text=english_text_strategy())
def test_keywords_format_english(text: str):
    extractor = KeywordExtractor()
    result = extractor.extract(text)

    if result.success and result.keywords:
        expected_formatted = ", ".join(result.keywords)
        assert result.formatted == expected_formatted, (
            f"Formatted string should be '{expected_formatted}', got '{result.formatted}'"
        )

        split_keywords = [kw.strip() for kw in result.formatted.split(",")]
        assert split_keywords == result.keywords, (
            f"Split keywords should match original: {result.keywords} vs {split_keywords}"
        )

@settings(max_examples=100)
@given(text=russian_text_strategy())
def test_keywords_format_russian(text: str):
    extractor = KeywordExtractor()
    result = extractor.extract(text, language="ru")

    if result.success and result.keywords:
        expected_formatted = ", ".join(result.keywords)
        assert result.formatted == expected_formatted, (
            f"Formatted string should be '{expected_formatted}', got '{result.formatted}'"
        )

        split_keywords = [kw.strip() for kw in result.formatted.split(",")]
        assert split_keywords == result.keywords, (
            f"Split keywords should match original: {result.keywords} vs {split_keywords}"
        )

@settings(max_examples=100)
@given(text=russian_text_strategy())
def test_keywords_language_preservation_russian(text: str):
    detector = LanguageDetector()
    detected_lang = detector.detect(text)

    assume(detected_lang == "ru")

    extractor = KeywordExtractor()
    result = extractor.extract(text, language="ru")

    if result.success and result.keywords:
        for keyword in result.keywords:
            has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in keyword)
            assert has_cyrillic, (
                f"Keyword '{keyword}' should contain Cyrillic characters for Russian text"
            )

@settings(max_examples=100)
@given(text=english_text_strategy())
def test_keywords_language_preservation_english(text: str):
    detector = LanguageDetector()
    detected_lang = detector.detect(text)

    assume(detected_lang == "en")

    extractor = KeywordExtractor()
    result = extractor.extract(text, language="en")

    if result.success and result.keywords:
        for keyword in result.keywords:
            has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in keyword)
            assert not has_cyrillic, (
                f"Keyword '{keyword}' should not contain Cyrillic characters for English text"
            )
