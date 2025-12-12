from dataclasses import dataclass
from typing import Optional

from .enums import (
    AIModel,
    ErrorScenario,
    ExtractionMethod,
    ProcessingStatus,
)
from .metadata import Metadata

@dataclass
class ValidationResult:
    is_valid: bool
    error_message: Optional[str] = None
    error_scenario: Optional[ErrorScenario] = None

@dataclass
class ParseResult:
    text: str
    char_count: int
    success: bool
    extraction_method: ExtractionMethod
    error_message: Optional[str] = None
    error_scenario: Optional[ErrorScenario] = None
    used_ocr: bool = False
    ocr_confidence: Optional[float] = None

    def __post_init__(self) -> None:
        if self.success and self.char_count == 0 and self.text:
            self.char_count = len(self.text)

@dataclass
class SummaryResult:
    summary: str
    sentence_count: int
    language: str
    success: bool
    ai_model_used: AIModel
    tokens_used: Optional[int] = None
    error_message: Optional[str] = None
    error_scenario: Optional[ErrorScenario] = None

@dataclass
class KeywordsResult:
    keywords: list[str]
    formatted: str
    count: int
    success: bool
    extraction_method: str
    error_message: Optional[str] = None
    error_scenario: Optional[ErrorScenario] = None

    def __post_init__(self) -> None:
        if self.success and self.count == 0 and self.keywords:
            self.count = len(self.keywords)

@dataclass
class ProcessingResult:
    metadata: Metadata
    parse_result: ParseResult
    summary_result: SummaryResult
    keywords_result: KeywordsResult
    status: ProcessingStatus
    processing_time: float
    error_scenario: Optional[ErrorScenario] = None
