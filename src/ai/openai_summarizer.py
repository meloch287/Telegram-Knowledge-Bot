from typing import Optional

from src.ai.base import AISummarizer
from src.models.enums import AIModel, ErrorScenario
from src.models.results import SummaryResult

class OpenAISummarizer(AISummarizer):

    MIN_SENTENCES = 3
    MAX_SENTENCES = 7

    MIN_TEXT_FOR_SUMMARY = 100

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4",
        max_tokens: int = 1000,
        temperature: float = 0.3,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.base_url = base_url
        self._client: Optional["openai.OpenAI"] = None

    @property
    def client(self) -> "openai.OpenAI":
        if self._client is None:
            import openai
            if self.base_url:
                self._client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
            else:
                self._client = openai.OpenAI(api_key=self.api_key)
        return self._client

    def _get_ai_model(self) -> AIModel:
        if "gpt-4" in self.model:
            return AIModel.OPENAI_GPT4
        return AIModel.OPENAI_GPT35

    def summarize(self, text: str, language: str) -> SummaryResult:
        if len(text) < self.MIN_TEXT_FOR_SUMMARY:
            sentence_count = self._count_sentences(text)
            return SummaryResult(
                summary=text,
                sentence_count=sentence_count,
                language=language,
                success=True,
                ai_model_used=self._get_ai_model(),
                tokens_used=0,
            )

        try:
            prompt = self._build_prompt(text, language)
            summary, tokens_used = self._call_api_with_tokens(prompt)
            sentence_count = self._count_sentences(summary)

            if sentence_count < self.MIN_SENTENCES or sentence_count > self.MAX_SENTENCES:
                summary, tokens_used = self._adjust_summary(
                    text, language, sentence_count, tokens_used
                )
                sentence_count = self._count_sentences(summary)

            return SummaryResult(
                summary=summary,
                sentence_count=sentence_count,
                language=language,
                success=True,
                ai_model_used=self._get_ai_model(),
                tokens_used=tokens_used,
            )

        except Exception as e:
            error_scenario = self._classify_error(e)
            return SummaryResult(
                summary="",
                sentence_count=0,
                language=language,
                success=False,
                ai_model_used=self._get_ai_model(),
                error_message=str(e),
                error_scenario=error_scenario,
            )

    def _call_api(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Ты - помощник для создания кратких резюме документов."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        return response.choices[0].message.content.strip()

    def _call_api_with_tokens(self, prompt: str) -> tuple[str, int]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Ты - помощник для создания кратких резюме документов."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        content = response.choices[0].message.content.strip()
        tokens = response.usage.total_tokens if response.usage else 0
        return content, tokens

    def _adjust_summary(
        self,
        text: str,
        language: str,
        current_count: int,
        tokens_used: int,
    ) -> tuple[str, int]:
        lang_instruction = "на русском языке" if language == "ru" else "in English"

        if current_count < self.MIN_SENTENCES:
            instruction = f"Создай резюме ровно из {self.MIN_SENTENCES} предложений"
        else:
            instruction = f"Создай резюме ровно из {self.MAX_SENTENCES} предложений"

        prompt = f"""{instruction} {lang_instruction}.
Резюме должно точно отражать основные темы и ключевые моменты документа.

Текст:
{text}

Резюме:"""

        summary, new_tokens = self._call_api_with_tokens(prompt)
        return summary, tokens_used + new_tokens

    def _classify_error(self, error: Exception) -> ErrorScenario:
        error_str = str(error).lower()

        if "rate limit" in error_str or "rate_limit" in error_str:
            return ErrorScenario.API_RATE_LIMIT
        elif "timeout" in error_str:
            return ErrorScenario.API_TIMEOUT
        else:
            return ErrorScenario.API_ERROR
