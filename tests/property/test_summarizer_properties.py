import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, patch

from src.ai.openai_summarizer import OpenAISummarizer
from src.ai.language_detector import LanguageDetector
from src.utils.retry_handler import RetryHandler
from src.models.config import RetryConfig
from src.models.enums import ErrorScenario

@st.composite
def russian_text_strategy(draw):
    russian_words = [
        'документ', 'система', 'данные', 'информация', 'процесс',
        'результат', 'анализ', 'метод', 'функция', 'объект',
        'пользователь', 'файл', 'текст', 'программа', 'модуль',
        'описывает', 'содержит', 'включает', 'определяет', 'использует',
        'основные', 'важные', 'ключевые', 'главные', 'новые',
        'работает', 'выполняет', 'обрабатывает', 'создаёт', 'проверяет',
    ]

    num_sentences = draw(st.integers(min_value=5, max_value=15))
    sentences = []

    for _ in range(num_sentences):
        num_words = draw(st.integers(min_value=5, max_value=15))
        words = [draw(st.sampled_from(russian_words)) for _ in range(num_words)]
        sentence = ' '.join(words).capitalize() + '.'
        sentences.append(sentence)

    return ' '.join(sentences)

@st.composite
def english_text_strategy(draw):
    english_words = [
        'document', 'system', 'data', 'information', 'process',
        'result', 'analysis', 'method', 'function', 'object',
        'user', 'file', 'text', 'program', 'module',
        'describes', 'contains', 'includes', 'defines', 'uses',
        'main', 'important', 'key', 'primary', 'new',
        'works', 'executes', 'processes', 'creates', 'validates',
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be',
        'have', 'has', 'had', 'do', 'does', 'did', 'will',
    ]

    num_sentences = draw(st.integers(min_value=5, max_value=15))
    sentences = []

    for _ in range(num_sentences):
        num_words = draw(st.integers(min_value=5, max_value=15))
        words = [draw(st.sampled_from(english_words)) for _ in range(num_words)]
        sentence = ' '.join(words).capitalize() + '.'
        sentences.append(sentence)

    return ' '.join(sentences)

@st.composite
def summary_with_sentences_strategy(draw, min_sentences=3, max_sentences=7):
    num_sentences = draw(st.integers(min_value=min_sentences, max_value=max_sentences))
    sentences = []

    for _ in range(num_sentences):
        words = ['This', 'is', 'a', 'test', 'sentence', 'about', 'the', 'document']
        num_extra = draw(st.integers(min_value=0, max_value=5))
        extra_words = ['important', 'key', 'main', 'primary', 'significant']
        for _ in range(num_extra):
            words.append(draw(st.sampled_from(extra_words)))
        sentence = ' '.join(words) + '.'
        sentences.append(sentence)

    return ' '.join(sentences)

def create_mock_openai_response(summary_text: str, tokens: int = 100):
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = summary_text
    mock_response.usage = Mock()
    mock_response.usage.total_tokens = tokens
    return mock_response

@settings(max_examples=100)
@given(
    input_text=english_text_strategy(),
    summary_sentences=st.integers(min_value=3, max_value=7)
)
def test_summary_sentence_count_bounds(input_text: str, summary_sentences: int):
    summary_parts = []
    for i in range(summary_sentences):
        summary_parts.append(f"This is sentence number {i + 1} of the summary.")
    mock_summary = ' '.join(summary_parts)

    summarizer = OpenAISummarizer(api_key="test-key")

    with patch.object(summarizer, '_call_api_with_tokens', return_value=(mock_summary, 100)):
        result = summarizer.summarize(input_text, "en")

        assert result.success, f"Summarization should succeed: {result.error_message}"
        assert 3 <= result.sentence_count <= 7, (
            f"Sentence count should be between 3 and 7, got {result.sentence_count}"
        )

@settings(max_examples=50)
@given(
    input_text=russian_text_strategy(),
    summary_sentences=st.integers(min_value=3, max_value=7)
)
def test_summary_sentence_count_bounds_russian(input_text: str, summary_sentences: int):
    summary_parts = []
    for i in range(summary_sentences):
        summary_parts.append(f"Это предложение номер {i + 1} в резюме.")
    mock_summary = ' '.join(summary_parts)

    summarizer = OpenAISummarizer(api_key="test-key")

    with patch.object(summarizer, '_call_api_with_tokens', return_value=(mock_summary, 100)):
        result = summarizer.summarize(input_text, "ru")

        assert result.success, f"Summarization should succeed: {result.error_message}"
        assert 3 <= result.sentence_count <= 7, (
            f"Sentence count should be between 3 and 7, got {result.sentence_count}"
        )

@settings(max_examples=100)
@given(input_text=russian_text_strategy())
def test_summary_language_preservation_russian(input_text: str):
    detector = LanguageDetector()
    detected_lang = detector.detect(input_text)

    assume(detected_lang == "ru")

    mock_summary = "Документ описывает основные принципы работы системы. Рассматриваются ключевые компоненты. Приводятся примеры использования."

    summarizer = OpenAISummarizer(api_key="test-key")

    with patch.object(summarizer, '_call_api_with_tokens', return_value=(mock_summary, 100)):
        result = summarizer.summarize(input_text, detected_lang)

        assert result.success, f"Summarization should succeed: {result.error_message}"
        assert result.language == "ru", f"Summary language should be 'ru', got '{result.language}'"

        summary_lang = detector.detect(result.summary)
        assert summary_lang == "ru", (
            f"Summary should be in Russian, detected as '{summary_lang}'"
        )

@settings(max_examples=100)
@given(input_text=english_text_strategy())
def test_summary_language_preservation_english(input_text: str):
    detector = LanguageDetector()
    detected_lang = detector.detect(input_text)

    assume(detected_lang == "en")

    mock_summary = "The document describes the main principles of the system. Key components are discussed. Usage examples are provided."

    summarizer = OpenAISummarizer(api_key="test-key")

    with patch.object(summarizer, '_call_api_with_tokens', return_value=(mock_summary, 100)):
        result = summarizer.summarize(input_text, detected_lang)

        assert result.success, f"Summarization should succeed: {result.error_message}"
        assert result.language == "en", f"Summary language should be 'en', got '{result.language}'"

        summary_lang = detector.detect(result.summary)
        assert summary_lang == "en", (
            f"Summary should be in English, detected as '{summary_lang}'"
        )

@settings(max_examples=50)
@given(
    num_failures=st.integers(min_value=1, max_value=3),
    max_retries=st.integers(min_value=1, max_value=5)
)
def test_retry_logic_for_api_failures(num_failures: int, max_retries: int):
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=0.001,
        max_delay=0.01,
        jitter=False,
    )

    handler = RetryHandler(config)
    call_count = 0

    def failing_then_succeeding():
        nonlocal call_count
        call_count += 1
        if call_count <= num_failures:
            raise Exception("API Error")
        return "success"

    if num_failures <= max_retries:
        result = handler.execute_with_retry(failing_then_succeeding)
        assert result == "success"
        assert call_count == num_failures + 1, (
            f"Should have called {num_failures + 1} times, called {call_count}"
        )
    else:
        try:
            handler.execute_with_retry(failing_then_succeeding)
            assert False, "Should have raised exception"
        except Exception as e:
            assert "API Error" in str(e)
            assert call_count == max_retries + 1, (
                f"Should have called {max_retries + 1} times, called {call_count}"
            )

@settings(max_examples=50)
@given(error_scenario=st.sampled_from(list(ErrorScenario)))
def test_retry_logic_retryable_scenarios(error_scenario: ErrorScenario):
    retryable_scenarios = {
        ErrorScenario.API_RATE_LIMIT,
        ErrorScenario.API_TIMEOUT,
        ErrorScenario.API_ERROR,
        ErrorScenario.SHEETS_AUTH_ERROR,
        ErrorScenario.SHEETS_WRITE_ERROR,
    }

    is_retryable = RetryHandler.is_retryable(error_scenario)
    expected = error_scenario in retryable_scenarios

    assert is_retryable == expected, (
        f"Error scenario {error_scenario} should be "
        f"{'retryable' if expected else 'not retryable'}"
    )

@settings(max_examples=30)
@given(
    base_delay=st.floats(min_value=0.1, max_value=2.0),
    max_delay=st.floats(min_value=5.0, max_value=60.0),
    attempt=st.integers(min_value=0, max_value=5)
)
def test_retry_exponential_backoff(base_delay: float, max_delay: float, attempt: int):
    config = RetryConfig(
        max_retries=5,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=2.0,
        jitter=False,
    )

    delay = config.get_delay(attempt)

    expected_delay = min(base_delay * (2.0 ** attempt), max_delay)
    assert delay == expected_delay, (
        f"Delay for attempt {attempt} should be {expected_delay}, got {delay}"
    )
    assert delay <= max_delay, (
        f"Delay {delay} should not exceed max_delay {max_delay}"
    )
