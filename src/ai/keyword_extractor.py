from typing import Optional

import yake

from src.ai.language_detector import LanguageDetector
from src.models.enums import ErrorScenario
from src.models.results import KeywordsResult

class KeywordExtractor:

    MIN_KEYWORDS = 5
    MAX_KEYWORDS = 10

    DEFAULT_MAX_NGRAM_SIZE = 2
    DEFAULT_DEDUPLICATION_THRESHOLD = 0.9
    DEFAULT_DEDUPLICATION_ALGO = 'seqm'
    DEFAULT_WINDOW_SIZE = 1

    def __init__(
        self,
        method: str = "yake",
        max_ngram_size: int = DEFAULT_MAX_NGRAM_SIZE,
        deduplication_threshold: float = DEFAULT_DEDUPLICATION_THRESHOLD,
        window_size: int = DEFAULT_WINDOW_SIZE,
    ):
        self.method = method
        self.max_ngram_size = max_ngram_size
        self.deduplication_threshold = deduplication_threshold
        self.window_size = window_size
        self._language_detector = LanguageDetector()

    def extract(
        self,
        text: str,
        count: Optional[int] = None,
        language: Optional[str] = None,
    ) -> KeywordsResult:
        if count is None:
            count = self.MAX_KEYWORDS
        count = max(self.MIN_KEYWORDS, min(count, self.MAX_KEYWORDS))

        if not text or len(text.strip()) < 10:
            return KeywordsResult(
                keywords=[],
                formatted="",
                count=0,
                success=False,
                extraction_method=self.method,
                error_message="Text is too short for keyword extraction",
                error_scenario=ErrorScenario.EMPTY_DOCUMENT,
            )

        if language is None:
            language = self._language_detector.detect(text)

        try:
            keywords = self._extract_with_yake(text, count, language)

            if len(keywords) < self.MIN_KEYWORDS:
                keywords = self._extract_with_yake(
                    text, count, language, max_ngram_size=3
                )

            keywords = keywords[:self.MAX_KEYWORDS]

            formatted = self.format_keywords(keywords)

            return KeywordsResult(
                keywords=keywords,
                formatted=formatted,
                count=len(keywords),
                success=True,
                extraction_method=self.method,
            )

        except Exception as e:
            return KeywordsResult(
                keywords=[],
                formatted="",
                count=0,
                success=False,
                extraction_method=self.method,
                error_message=str(e),
                error_scenario=ErrorScenario.API_ERROR,
            )

    def _extract_with_yake(
        self,
        text: str,
        count: int,
        language: str,
        max_ngram_size: Optional[int] = None,
    ) -> list[str]:
        if max_ngram_size is None:
            max_ngram_size = self.max_ngram_size

        yake_language = self._map_language_to_yake(language)

        kw_extractor = yake.KeywordExtractor(
            lan=yake_language,
            n=max_ngram_size,
            dedupLim=self.deduplication_threshold,
            dedupFunc=self.DEFAULT_DEDUPLICATION_ALGO,
            windowsSize=self.window_size,
            top=count * 2,
        )

        keywords_with_scores = kw_extractor.extract_keywords(text)

        keywords = [kw for kw, score in keywords_with_scores]

        keywords = self._clean_keywords(keywords, language)

        return keywords[:count]

    def _map_language_to_yake(self, language: str) -> str:
        language_map = {
            'ru': 'ru',
            'en': 'en',
        }
        return language_map.get(language, 'en')

    def _clean_keywords(self, keywords: list[str], language: str) -> list[str]:
        cleaned = []
        seen = set()

        for kw in keywords:
            kw = ' '.join(kw.split())

            if len(kw) < 2:
                continue

            kw_lower = kw.lower()
            if kw_lower in seen:
                continue
            seen.add(kw_lower)

            if not any(c.isalpha() for c in kw):
                continue

            cleaned.append(kw)

        return cleaned

    def format_keywords(self, keywords: list[str]) -> str:
        return ", ".join(keywords)
