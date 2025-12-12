import time
from typing import Callable, Optional, TypeVar

from src.models.config import RetryConfig
from src.models.enums import ErrorScenario

T = TypeVar('T')

class RetryHandler:

    RETRYABLE_SCENARIOS = {
        ErrorScenario.API_RATE_LIMIT,
        ErrorScenario.API_TIMEOUT,
        ErrorScenario.API_ERROR,
        ErrorScenario.SHEETS_AUTH_ERROR,
        ErrorScenario.SHEETS_WRITE_ERROR,
    }

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self._attempt_count = 0
        self._last_delay = 0.0

    @property
    def attempt_count(self) -> int:
        return self._attempt_count

    @property
    def last_delay(self) -> float:
        return self._last_delay

    def execute_with_retry(
        self,
        func: Callable[[], T],
        retryable_errors: tuple = (Exception,),
    ) -> T:
        last_exception: Optional[Exception] = None
        self._attempt_count = 0

        for attempt in range(self.config.max_retries + 1):
            self._attempt_count = attempt + 1
            try:
                return func()
            except retryable_errors as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    delay = self.config.get_delay(attempt)
                    self._last_delay = delay
                    time.sleep(delay)
                    continue
                raise

        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected state in retry handler")

    async def execute_with_retry_async(
        self,
        func: Callable[[], T],
        retryable_errors: tuple = (Exception,),
    ) -> T:
        import asyncio

        last_exception: Optional[Exception] = None
        self._attempt_count = 0

        for attempt in range(self.config.max_retries + 1):
            self._attempt_count = attempt + 1
            try:
                return await func()
            except retryable_errors as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    delay = self.config.get_delay(attempt)
                    self._last_delay = delay
                    await asyncio.sleep(delay)
                    continue
                raise

        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected state in retry handler")

    @staticmethod
    def is_retryable(error_scenario: ErrorScenario) -> bool:
        return error_scenario in RetryHandler.RETRYABLE_SCENARIOS

    def reset(self) -> None:
        self._attempt_count = 0
        self._last_delay = 0.0
