import re
from typing import Optional

class LanguageDetector:

    CYRILLIC_PATTERN = re.compile(r'[\u0400-\u04FF]')

    LATIN_PATTERN = re.compile(r'[a-zA-Z]')

    RUSSIAN_MARKERS = {
        'и', 'в', 'на', 'с', 'по', 'для', 'что', 'это', 'как', 'не',
        'из', 'к', 'от', 'до', 'за', 'при', 'но', 'или', 'а', 'о',
        'он', 'она', 'они', 'мы', 'вы', 'я', 'ты', 'его', 'её', 'их',
    }

    ENGLISH_MARKERS = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'can', 'shall',
        'of', 'to', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
        'and', 'or', 'but', 'not', 'this', 'that', 'it', 'as', 'if',
    }

    def detect(self, text: str) -> str:
        if not text or not text.strip():
            return "en"

        cyrillic_count = len(self.CYRILLIC_PATTERN.findall(text))
        latin_count = len(self.LATIN_PATTERN.findall(text))

        total_letters = cyrillic_count + latin_count
        if total_letters == 0:
            return "en"

        cyrillic_ratio = cyrillic_count / total_letters

        if cyrillic_ratio > 0.7:
            return "ru"
        elif cyrillic_ratio < 0.3:
            return "en"

        return self._detect_by_words(text)

    def _detect_by_words(self, text: str) -> str:
        words = set(re.findall(r'\b\w+\b', text.lower()))

        russian_matches = len(words & self.RUSSIAN_MARKERS)
        english_matches = len(words & self.ENGLISH_MARKERS)

        if russian_matches > english_matches:
            return "ru"
        elif english_matches > russian_matches:
            return "en"

        if self.CYRILLIC_PATTERN.search(text):
            return "ru"

        return "en"

    def is_russian(self, text: str) -> bool:
        return self.detect(text) == "ru"

    def is_english(self, text: str) -> bool:
        return self.detect(text) == "en"
