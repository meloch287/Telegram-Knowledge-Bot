import asyncio
import logging
import os
import sys
import tempfile
from datetime import datetime
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.bot.handlers import TelegramBotHandler
from src.bot.notifications import NotificationService
from src.config import ConfigurationError, load_config
from src.models.config import WorkflowConfig
from src.models.enums import ErrorScenario, FileType
from src.models.metadata import Metadata
from src.processor import DocumentProcessor
from src.utils.logger import ProcessingLogger

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

class TelegramKnowledgeBot:

    def __init__(self, config: WorkflowConfig) -> None:
        self.config = config

        self.processing_logger = ProcessingLogger(config.log_file_path)

        self.processor = DocumentProcessor(
            config=config,
            logger=self.processing_logger,
        )

        self.handler = TelegramBotHandler(
            token=config.telegram_bot_token,
            webhook_url=config.webhook_url,
        )

        self.notification_service = NotificationService(
            max_file_size_mb=config.max_file_size_mb,
        )

        self.application: Optional[Application] = None

    def setup_application(self) -> Application:
        self.application = (
            Application.builder()
            .token(self.config.telegram_bot_token)
            .build()
        )

        self.application.add_handler(
            CommandHandler("start", self.handle_start)
        )
        self.application.add_handler(
            CommandHandler("help", self.handle_help)
        )
        self.application.add_handler(
            MessageHandler(filters.Document.ALL, self.handle_document)
        )
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.handle_text_message,
            )
        )

        return self.application

    async def handle_start(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        if update.effective_chat is None:
            return

        welcome_message = (
            "👋 Привет! Я бот для обработки документов.\n\n"
            f"{self.notification_service.get_instructions_message()}\n\n"
            "Я извлеку текст, создам краткое описание и выделю ключевые слова."
        )

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=welcome_message,
        )

    async def handle_help(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        if update.effective_chat is None:
            return

        help_message = (
            "📖 <b>Как использовать бота:</b>\n\n"
            "1. Отправьте документ (PDF, DOCX, TXT, MD) как вложение\n"
            "2. Или отправьте ссылку на документ\n\n"
            "Бот автоматически:\n"
            "• Извлечёт текст из документа\n"
            "• Создаст краткое описание (3-7 предложений)\n"
            "• Выделит ключевые слова (5-10)\n"
            "• Сохранит результаты в базу знаний\n\n"
            f"<b>Ограничения:</b>\n"
            f"• Максимальный размер файла: {self.config.max_file_size_mb}MB\n"
            "• Поддерживаемые форматы: PDF, DOCX, TXT, MD"
        )

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=help_message,
            parse_mode="HTML",
        )

    async def handle_document(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        if update.effective_chat is None or update.message is None:
            return

        chat_id = update.effective_chat.id
        document = update.message.document

        if document is None:
            await context.bot.send_message(
                chat_id=chat_id,
                text=self.notification_service.get_instructions_message(),
            )
            return

        file_info = {
            "file_name": document.file_name or "unknown",
            "file_size": document.file_size or 0,
            "file_id": document.file_id,
            "mime_type": document.mime_type,
        }

        validation = self.handler.validate_file(file_info)
        if not validation.is_valid:
            error_message = self.notification_service.get_error_message_from_validation(
                validation.error_scenario,
                validation.error_message,
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text=error_message,
            )
            return

        await context.bot.send_message(
            chat_id=chat_id,
            text=self.notification_service.get_processing_started_message(),
        )

        user = update.message.from_user
        user_info = {
            "id": user.id if user else 0,
            "username": user.username if user else None,
            "first_name": user.first_name if user else None,
        }

        try:
            metadata = self.handler.extract_metadata(file_info, user_info)

            file = await context.bot.get_file(document.file_id)

            suffix = os.path.splitext(file_info["file_name"])[1]
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix,
            ) as tmp_file:
                await file.download_to_drive(tmp_file.name)
                file_path = tmp_file.name

            try:
                result = self.processor.process_document(
                    file_path=file_path,
                    metadata=metadata,
                )

                notification = self.processor.get_notification_message(result)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=notification,
                    parse_mode="HTML",
                )

            finally:
                if os.path.exists(file_path):
                    os.unlink(file_path)

        except ValueError as e:
            self.processing_logger.log_error(
                error_type="MetadataError",
                message=str(e),
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Ошибка обработки: {str(e)}",
            )
        except Exception as e:
            self.processing_logger.log_error(
                error_type="ProcessingError",
                message=str(e),
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Произошла ошибка при обработке документа. Попробуйте позже.",
            )

    async def handle_text_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        if update.effective_chat is None or update.message is None:
            return

        chat_id = update.effective_chat.id
        text = update.message.text or ""

        url = self.handler.extract_url_from_message(text)

        if url is None:
            await context.bot.send_message(
                chat_id=chat_id,
                text=self.notification_service.get_instructions_message(),
            )
            return

        if not self.config.enable_url_download:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Загрузка по URL отключена. Пожалуйста, отправьте файл напрямую.",
            )
            return

        validation = self.handler.validate_url_input(url)
        if not validation.is_valid:
            error_message = self.notification_service.get_error_message_from_validation(
                validation.error_scenario,
                validation.error_message,
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text=error_message,
            )
            return

        await context.bot.send_message(
            chat_id=chat_id,
            text=self.notification_service.get_processing_started_message(),
        )

        file_path, file_name, error = self.processor.download_from_url(
            url=url,
            timeout=self.config.webhook_timeout,
        )

        if error or file_path is None or file_name is None:
            error_message = self.notification_service.get_error_message(
                error or ErrorScenario.URL_INVALID
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text=error_message,
            )
            return

        try:
            file_size = os.path.getsize(file_path)

            validation = self.processor.validate_file(file_name, file_size)
            if not validation.is_valid:
                error_message = self.notification_service.get_error_message_from_validation(
                    validation.error_scenario,
                    validation.error_message,
                )
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=error_message,
                )
                return

            user = update.message.from_user

            file_type = FileType.from_extension(
                os.path.splitext(file_name)[1].lstrip(".")
            )

            if file_type is None:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=self.notification_service.get_error_message(
                        ErrorScenario.UNSUPPORTED_FORMAT
                    ),
                )
                return

            metadata = Metadata(
                file_name=file_name,
                file_size=file_size,
                file_type=file_type,
                uploader_id=user.id if user else 0,
                uploader_username=user.username if user else None,
                timestamp=datetime.now(),
                source_url=url,
            )

            result = self.processor.process_document(
                file_path=file_path,
                metadata=metadata,
            )

            notification = self.processor.get_notification_message(result)
            await context.bot.send_message(
                chat_id=chat_id,
                text=notification,
                parse_mode="HTML",
            )

        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)

    def run_polling(self) -> None:
        if self.application is None:
            self.setup_application()

        logger.info("Starting bot in polling mode...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

    async def run_webhook(
        self,
        webhook_url: str,
        listen: str = "0.0.0.0",
        port: int = 8443,
        url_path: str = "",
        secret_token: Optional[str] = None,
    ) -> None:
        if self.application is None:
            self.setup_application()

        logger.info(f"Starting bot in webhook mode on {listen}:{port}...")

        await self.application.bot.set_webhook(
            url=f"{webhook_url}/{url_path}",
            secret_token=secret_token or self.config.telegram_webhook_secret,
        )

        await self.application.run_webhook(
            listen=listen,
            port=port,
            url_path=url_path,
            webhook_url=webhook_url,
            secret_token=secret_token or self.config.telegram_webhook_secret,
        )

def main() -> None:
    try:
        config = load_config()
        logger.info("Configuration loaded successfully")

        bot = TelegramKnowledgeBot(config)

        bot.setup_application()

        webhook_url = config.webhook_url

        if webhook_url:
            logger.info(f"Running in webhook mode with URL: {webhook_url}")
            asyncio.run(
                bot.run_webhook(
                    webhook_url=webhook_url,
                    secret_token=config.telegram_webhook_secret,
                )
            )
        else:
            logger.info("Running in polling mode")
            bot.run_polling()

    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
