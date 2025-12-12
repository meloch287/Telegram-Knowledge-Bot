import os
from typing import Optional

from src.models import FileType
from src.parsers.base import DocumentParser
from src.parsers.pdf_parser import PDFParser
from src.parsers.docx_parser import DOCXParser
from src.parsers.txt_parser import TXTParser
from src.parsers.md_parser import MDParser

class ParserFactory:

    def __init__(self) -> None:
        self._parsers: list[DocumentParser] = [
            PDFParser(),
            DOCXParser(),
            TXTParser(),
            MDParser(),
        ]

    def get_parser(self, file_path: str) -> Optional[DocumentParser]:
        extension = self._get_extension(file_path)

        for parser in self._parsers:
            if parser.supports(extension):
                return parser

        return None

    def get_parser_by_type(self, file_type: FileType) -> Optional[DocumentParser]:
        return self.get_parser(f"file.{file_type.value}")

    def is_supported(self, file_path: str) -> bool:
        return self.get_parser(file_path) is not None

    def supported_extensions(self) -> list[str]:
        return FileType.supported_extensions()

    def _get_extension(self, file_path: str) -> str:
        _, ext = os.path.splitext(file_path)
        return ext.lower().lstrip(".")
