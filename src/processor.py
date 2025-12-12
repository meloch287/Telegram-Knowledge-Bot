import os
import tempfile
import time
from datetime import datetime
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlparse

import requests

from src.ai.keyword_extractor import KeywordExtractor
from src.ai.language_detector import LanguageDetector
from src.ai.openai_summarizer import OpenAISummarizer
from src.bot.notifications import NotificationService
from src.models.config import RetryConfig, WorkflowConfig
from src.models.enums import (
    AIModel,
    ErrorScenario,
    ExtractionMethod,
    FileType,
    ProcessingStatus,
)
from src.models.metadata import Metadata
from src.models.results import (
    KeywordsResult,
    ParseResult,
    ProcessingResult,
    SummaryResult,
    ValidationResult,
)
from src.models.storage import GoogleSheetsRow
from src.parsers.factory import ParserFactory
from src.utils.logger import ProcessingLogger
from src.utils.retry_handler import RetryHandler
from src.utils.validators import validate_file, validate_url

class DocumentProcessor:

    def __init__(
        self,
        config: WorkflowConfig,
        logger: Optional[ProcessingLogger] = None,
    ) -> None:
        self.config = config

        self.parser_factory = ParserFactory()
        self.language_detector = LanguageDetector()
        self.notification_service = NotificationService(
            max_file_size_mb=config.max_file_size_mb
        )

        self.logger = logger or ProcessingLogger(config.log_file_path)

        retry_config = RetryConfig(
            max_retries=config.max_retries,
            base_delay=config.retry_base_delay,
            max_delay=config.retry_max_delay,
        )
        self.retry_handler = RetryHandler(retry_config)

        self.summarizer = self._create_summarizer()
        self.keyword_extractor = KeywordExtractor()

    def _create_summarizer(self) -> OpenAISummarizer:
        if self.config.ai_provider == "openrouter":
            return OpenAISummarizer(
                api_key=self.config.openai_api_key or "",
                model=self.config.openai_model,
                base_url="https://openrouter.ai/api/v1",
            )
        if self.config.ai_provider == "openai":
            return OpenAISummarizer(
                api_key=self.config.openai_api_key or "",
                model=self.config.openai_model,
            )
        return OpenAISummarizer(
            api_key=self.config.openai_api_key or "",
            model=self.config.openai_model,
        )

    def process_document(
        self,
        file_path: str,
        metadata: Metadata,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> ProcessingResult:
        start_time = time.time()

        self.logger.log_upload(metadata)

        if on_progress:
            on_progress(self.notification_service.get_processing_started_message())

        parse_result = self._parse_document(file_path, metadata.file_type)

        if not parse_result.success:
            return self._create_failed_result(
                metadata=metadata,
                parse_result=parse_result,
                processing_time=time.time() - start_time,
                error_scenario=parse_result.error_scenario,
            )

        self.logger.log_extraction(
            status="success",
            char_count=parse_result.char_count,
            extraction_method=parse_result.extraction_method.value,
            used_ocr=parse_result.used_ocr,
            file_name=metadata.file_name,
        )

        language = self.language_detector.detect(parse_result.text)
        metadata.language = language

        summary_result = self._summarize_with_retry(parse_result.text, language)

        if not summary_result.success:
            return self._create_failed_result(
                metadata=metadata,
                parse_result=parse_result,
                summary_result=summary_result,
                processing_time=time.time() - start_time,
                error_scenario=summary_result.error_scenario,
            )

        self.logger.log_api_call(
            service=self.config.ai_provider,
            status="success",
            model=summary_result.ai_model_used.value,
            tokens_used=summary_result.tokens_used,
        )

        keywords_result = self._extract_keywords(parse_result.text, language)

        if not keywords_result.success:
            return self._create_failed_result(
                metadata=metadata,
                parse_result=parse_result,
                summary_result=summary_result,
                keywords_result=keywords_result,
                processing_time=time.time() - start_time,
                error_scenario=keywords_result.error_scenario,
            )

        self.logger.log_keywords(
            extraction_method=keywords_result.extraction_method,
            keyword_count=keywords_result.count,
            status="success",
            language=language,
        )

        processing_time = time.time() - start_time

        return ProcessingResult(
            metadata=metadata,
            parse_result=parse_result,
            summary_result=summary_result,
            keywords_result=keywords_result,
            status=ProcessingStatus.COMPLETED,
            processing_time=processing_time,
        )

    def _parse_document(
        self,
        file_path: str,
        file_type: FileType,
    ) -> ParseResult:
        parser = self.parser_factory.get_parser_by_type(file_type)

        if parser is None:
            return ParseResult(
                text="",
                char_count=0,
                success=False,
                extraction_method=ExtractionMethod.PLAIN_READ,
                error_message=f"No parser available for file type: {file_type.value}",
                error_scenario=ErrorScenario.UNSUPPORTED_FORMAT,
            )

        try:
            return parser.parse(file_path)
        except Exception as e:
            self.logger.log_error(
                error_type="ParseError",
                message=str(e),
                error_scenario=ErrorScenario.CORRUPTED_FILE,
                context={"file_path": file_path, "file_type": file_type.value},
            )
            return ParseResult(
                text="",
                char_count=0,
                success=False,
                extraction_method=ExtractionMethod.PLAIN_READ,
                error_message=str(e),
                error_scenario=ErrorScenario.CORRUPTED_FILE,
            )

    def _summarize_with_retry(
        self,
        text: str,
        language: str,
    ) -> SummaryResult:
        try:
            def summarize_func() -> SummaryResult:
                return self.summarizer.summarize(text, language)

            return self.retry_handler.execute_with_retry(
                summarize_func,
                retryable_errors=(Exception,),
            )
        except Exception as e:
            self.logger.log_error(
                error_type="SummarizationError",
                message=str(e),
                error_scenario=ErrorScenario.API_ERROR,
            )
            self.logger.log_api_call(
                service=self.config.ai_provider,
                status="error",
            )
            return SummaryResult(
                summary="",
                sentence_count=0,
                language=language,
                success=False,
                ai_model_used=AIModel.OPENAI_GPT4,
                error_message=str(e),
                error_scenario=ErrorScenario.API_ERROR,
            )

    def _extract_keywords(
        self,
        text: str,
        language: str,
    ) -> KeywordsResult:
        try:
            return self.keyword_extractor.extract(
                text=text,
                count=self.config.keywords_max_count,
                language=language,
            )
        except Exception as e:
            self.logger.log_error(
                error_type="KeywordExtractionError",
                message=str(e),
                error_scenario=ErrorScenario.API_ERROR,
            )
            return KeywordsResult(
                keywords=[],
                formatted="",
                count=0,
                success=False,
                extraction_method="yake",
                error_message=str(e),
                error_scenario=ErrorScenario.API_ERROR,
            )

    def _create_failed_result(
        self,
        metadata: Metadata,
        parse_result: Optional[ParseResult] = None,
        summary_result: Optional[SummaryResult] = None,
        keywords_result: Optional[KeywordsResult] = None,
        processing_time: float = 0.0,
        error_scenario: Optional[ErrorScenario] = None,
    ) -> ProcessingResult:
        if parse_result is None:
            parse_result = ParseResult(
                text="",
                char_count=0,
                success=False,
                extraction_method=ExtractionMethod.PLAIN_READ,
                error_scenario=error_scenario,
            )

        if summary_result is None:
            summary_result = SummaryResult(
                summary="",
                sentence_count=0,
                language=metadata.language or "en",
                success=False,
                ai_model_used=AIModel.OPENAI_GPT4,
                error_scenario=error_scenario,
            )

        if keywords_result is None:
            keywords_result = KeywordsResult(
                keywords=[],
                formatted="",
                count=0,
                success=False,
                extraction_method="yake",
                error_scenario=error_scenario,
            )

        return ProcessingResult(
            metadata=metadata,
            parse_result=parse_result,
            summary_result=summary_result,
            keywords_result=keywords_result,
            status=ProcessingStatus.FAILED,
            processing_time=processing_time,
            error_scenario=error_scenario,
        )

    def validate_file(
        self,
        file_name: str,
        file_size: int,
    ) -> ValidationResult:
        return validate_file(file_name, file_size)

    def validate_url(self, url: str) -> ValidationResult:
        return validate_url(url)

    def download_from_url(
        self,
        url: str,
        timeout: int = 30,
    ) -> tuple[Optional[str], Optional[str], Optional[ErrorScenario]]:
        validation = self.validate_url(url)
        if not validation.is_valid:
            return None, None, validation.error_scenario

        try:
            response = requests.get(url, timeout=timeout, stream=True)
            response.raise_for_status()

            file_name = self._extract_filename_from_response(url, response)

            if not file_name:
                return None, None, ErrorScenario.URL_INVALID

            if not self.parser_factory.is_supported(file_name):
                return None, None, ErrorScenario.UNSUPPORTED_FORMAT

            suffix = os.path.splitext(file_name)[1]
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix,
            ) as tmp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    tmp_file.write(chunk)
                return tmp_file.name, file_name, None

        except requests.exceptions.Timeout:
            self.logger.log_error(
                error_type="URLDownloadError",
                message=f"Timeout downloading from {url}",
                error_scenario=ErrorScenario.URL_INVALID,
            )
            return None, None, ErrorScenario.URL_INVALID
        except requests.exceptions.RequestException as e:
            self.logger.log_error(
                error_type="URLDownloadError",
                message=str(e),
                error_scenario=ErrorScenario.URL_INVALID,
                context={"url": url},
            )
            return None, None, ErrorScenario.URL_INVALID

    def _extract_filename_from_response(
        self,
        url: str,
        response: requests.Response,
    ) -> Optional[str]:
        content_disposition = response.headers.get("Content-Disposition", "")
        if "filename=" in content_disposition:
            parts = content_disposition.split("filename=")
            if len(parts) > 1:
                filename = parts[1].strip('"\'')
                if filename:
                    return filename

        parsed = urlparse(url)
        path = parsed.path
        if path and path != "/":
            filename = path.rsplit("/", 1)[-1]
            if filename and "." in filename:
                return filename

        return None

    def create_sheets_row(
        self,
        result: ProcessingResult,
    ) -> GoogleSheetsRow:
        return GoogleSheetsRow(
            timestamp=result.metadata.timestamp.isoformat(),
            uploader_id=str(result.metadata.uploader_id),
            uploader_username=result.metadata.uploader_username or "",
            file_name=result.metadata.file_name,
            file_type=result.metadata.file_type.value,
            file_size=result.metadata.file_size,
            char_count=result.parse_result.char_count,
            language=result.metadata.language or "",
            summary=result.summary_result.summary,
            keywords=result.keywords_result.formatted,
            status=result.status.value,
            error_message=result.summary_result.error_message or "",
            ai_model_used=result.summary_result.ai_model_used.value,
            extraction_method=result.parse_result.extraction_method.value,
            ocr_used=result.parse_result.used_ocr,
            processing_time=result.processing_time,
        )

    def get_notification_message(
        self,
        result: ProcessingResult,
    ) -> str:
        if result.status == ProcessingStatus.COMPLETED:
            return self.notification_service.get_processing_complete_message(
                summary=result.summary_result.summary,
                keywords=result.keywords_result.formatted,
            )

        if result.error_scenario:
            return self.notification_service.get_error_message(result.error_scenario)

        return "❌ Произошла неизвестная ошибка. Попробуйте позже"
