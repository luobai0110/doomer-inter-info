import logging
import threading
import time
from collections.abc import Callable
from typing import Any

import requests

DEFAULT_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_SECONDS = (0.5, 1.0, 2.0)
RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})

logger = logging.getLogger(__name__)


class RateLimiter:
    """跨线程限制实际 HTTP 请求频率。"""

    def __init__(self, requests_per_second: int) -> None:
        self._min_interval_seconds = 1 / requests_per_second
        self._lock = threading.Lock()
        self._next_request_time = 0.0

    def wait(self) -> None:
        """等待到当前线程的下一个请求槽位。"""
        with self._lock:
            now = time.monotonic()
            delay_seconds = max(0.0, self._next_request_time - now)
            self._next_request_time = now + delay_seconds + self._min_interval_seconds

        if delay_seconds > 0:
            time.sleep(delay_seconds)


def _log_retry(
    url: str,
    attempt: int,
    delay_seconds: float,
    status_code: int | None,
    error: str | None,
) -> None:
    """输出请求重试的关键信息。"""
    logger.warning(
        "HTTP 请求重试",
        extra={
            "url": url,
            "attempt": attempt + 1,
            "delay_seconds": delay_seconds,
            "status_code": status_code,
            "error": error,
        },
    )


def get_with_retry(
    url: str,
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_seconds: tuple[float, ...] = DEFAULT_BACKOFF_SECONDS,
    rate_limiter: RateLimiter | None = None,
    on_attempt: Callable[
        [requests.Response | None, requests.RequestException | None], None
    ]
    | None = None,
    **kwargs: Any,
) -> requests.Response:
    """发送 GET 请求，并对超时、连接错误和可重试状态码自动重试。"""
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
    last_response: requests.Response | None = None
    last_error: requests.RequestException | None = None

    for attempt in range(max_retries + 1):
        last_response = None
        last_error = None
        if rate_limiter is not None:
            rate_limiter.wait()
        try:
            last_response = requests.get(url=url, **kwargs)
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_error = exc

        if on_attempt is not None:
            on_attempt(last_response, last_error)

        if last_error is None and last_response is not None:
            if last_response.status_code not in RETRYABLE_STATUS_CODES:
                return last_response
        elif last_error is not None and attempt == max_retries:
            raise last_error

        if attempt == max_retries:
            return last_response

        delay_seconds = backoff_seconds[min(attempt, len(backoff_seconds) - 1)]
        _log_retry(
            url=url,
            attempt=attempt,
            delay_seconds=delay_seconds,
            status_code=last_response.status_code if last_response else None,
            error=str(last_error) if last_error else None,
        )
        time.sleep(delay_seconds)

    raise RuntimeError("HTTP 请求重试流程异常终止")
