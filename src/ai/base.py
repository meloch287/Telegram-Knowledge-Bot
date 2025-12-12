from abc import ABC, abstractmethod
from typing import Optional

from src.models.results import SummaryResult

class AISummarizer(ABC):

    @abstractmethod
    def summarize(self, text: str, language: str) -> SummaryResult:
        pass

    @abstractmethod
    def _call_api(self, prompt: str) -> str:
        pass

    def _build_prompt(self, text: str, language: str) -> str:
        lang_instruction = "на русском языке" if language == "ru" else "in English"

        return f"""Создай краткое резюме следующего текста {lang_instruction}.
Резюме должно содержать от 3 до 7 предложений.
Резюме должно точно отражать основные темы и ключевые моменты документа.

Текст:
{text}

Резюме:"""

    def _count_sentences(self, text: str) -> int:
        if not text or not text.strip():
            return 0

        import re
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        sentences = [s for s in sentences if s.strip()]
        return len(sentences)
