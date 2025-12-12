import os
from dataclasses import dataclass
from typing import Optional

from src.models import ParseResult, ExtractionMethod, ErrorScenario

@dataclass
class OCRResult:
    text: str
    confidence: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None

class OCREngine:

    DEFAULT_LANGUAGE = "rus+eng"

    def __init__(
        self,
        engine: str = "tesseract",
        tesseract_path: Optional[str] = None,
        language: str = DEFAULT_LANGUAGE,
    ):
        self.engine = engine.lower()
        self.tesseract_path = tesseract_path
        self.language = language
        self._configure_tesseract()

    def _configure_tesseract(self) -> None:
        if self.tesseract_path and self.engine == "tesseract":
            try:
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
            except ImportError:
                pass

    def extract_text(self, image_path: str) -> OCRResult:
        if self.engine == "tesseract":
            return self._extract_with_tesseract(image_path)
        elif self.engine == "google_vision":
            return self._extract_with_google_vision(image_path)
        else:
            return OCRResult(
                text="",
                success=False,
                error_message=f"Unsupported OCR engine: {self.engine}",
            )

    def _extract_with_tesseract(self, image_path: str) -> OCRResult:
        try:
            import pytesseract
            from PIL import Image
        except ImportError as e:
            return OCRResult(
                text="",
                success=False,
                error_message=f"Required library not installed: {e}",
            )

        try:
            image = Image.open(image_path)

            data = pytesseract.image_to_data(
                image,
                lang=self.language,
                output_type=pytesseract.Output.DICT,
            )

            confidences = [
                conf for conf in data["conf"]
                if isinstance(conf, (int, float)) and conf >= 0
            ]
            avg_confidence = (
                sum(confidences) / len(confidences)
                if confidences else None
            )

            text = pytesseract.image_to_string(
                image,
                lang=self.language,
            )

            return OCRResult(
                text=text.strip(),
                confidence=avg_confidence,
                success=True,
            )

        except Exception as e:
            return OCRResult(
                text="",
                success=False,
                error_message=f"Tesseract OCR failed: {e}",
            )

    def _extract_with_google_vision(self, image_path: str) -> OCRResult:
        return OCRResult(
            text="",
            success=False,
            error_message="Google Vision OCR not implemented yet",
        )

    def process_pdf_pages(self, pdf_path: str) -> ParseResult:
        try:
            import pdf2image
        except ImportError:
            return ParseResult(
                text="",
                char_count=0,
                success=False,
                extraction_method=ExtractionMethod.TESSERACT_OCR,
                error_message="pdf2image library not installed",
                error_scenario=ErrorScenario.OCR_FAILED,
                used_ocr=True,
            )

        try:
            images = pdf2image.convert_from_path(pdf_path)

            if not images:
                return ParseResult(
                    text="",
                    char_count=0,
                    success=False,
                    extraction_method=ExtractionMethod.TESSERACT_OCR,
                    error_message="No pages found in PDF",
                    error_scenario=ErrorScenario.EMPTY_DOCUMENT,
                    used_ocr=True,
                )

            text_parts: list[str] = []
            confidences: list[float] = []

            for i, image in enumerate(images):
                temp_path = f"_temp_page_{i}.png"
                try:
                    image.save(temp_path, "PNG")
                    result = self.extract_text(temp_path)

                    if result.success and result.text:
                        text_parts.append(result.text)
                        if result.confidence is not None:
                            confidences.append(result.confidence)
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

            full_text = "\n\n".join(text_parts)
            char_count = len(full_text)

            avg_confidence = (
                sum(confidences) / len(confidences)
                if confidences else None
            )

            if char_count == 0:
                return ParseResult(
                    text="",
                    char_count=0,
                    success=False,
                    extraction_method=ExtractionMethod.TESSERACT_OCR,
                    error_message="OCR could not extract any text from PDF",
                    error_scenario=ErrorScenario.OCR_FAILED,
                    used_ocr=True,
                    ocr_confidence=avg_confidence,
                )

            return ParseResult(
                text=full_text,
                char_count=char_count,
                success=True,
                extraction_method=ExtractionMethod.TESSERACT_OCR,
                used_ocr=True,
                ocr_confidence=avg_confidence,
            )

        except Exception as e:
            error_msg = str(e).lower()

            if "password" in error_msg or "encrypted" in error_msg:
                return ParseResult(
                    text="",
                    char_count=0,
                    success=False,
                    extraction_method=ExtractionMethod.TESSERACT_OCR,
                    error_message="PDF is password protected",
                    error_scenario=ErrorScenario.PASSWORD_PROTECTED,
                    used_ocr=True,
                )

            if "poppler" in error_msg:
                return ParseResult(
                    text="",
                    char_count=0,
                    success=False,
                    extraction_method=ExtractionMethod.TESSERACT_OCR,
                    error_message="Poppler not installed (required for PDF to image conversion)",
                    error_scenario=ErrorScenario.OCR_FAILED,
                    used_ocr=True,
                )

            return ParseResult(
                text="",
                char_count=0,
                success=False,
                extraction_method=ExtractionMethod.TESSERACT_OCR,
                error_message=f"OCR processing failed: {e}",
                error_scenario=ErrorScenario.OCR_FAILED,
                used_ocr=True,
            )
