from abc import ABC, abstractmethod

from src.models import ParseResult

class DocumentParser(ABC):

    @abstractmethod
    def parse(self, file_path: str) -> ParseResult:
        pass

    @abstractmethod
    def supports(self, file_extension: str) -> bool:
        pass

    def _normalize_extension(self, extension: str) -> str:
        return extension.lower().lstrip(".")
