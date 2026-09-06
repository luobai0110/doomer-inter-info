import json

import requests

from app.core.config import settings
from app.core.http import get_with_retry
from app.core.logging import get_logger


REQUEST_TIMEOUT = 30
BACKOFF_SECONDS = (0.5, 1.0, 2.0)
logger = get_logger(__name__)


def _log_http_detail(resp: requests.Response) -> None:
    """输出雪花 ID 服务的请求与响应详情。"""
    request_body = resp.request.body
    if isinstance(request_body, bytes):
        request_body = request_body.decode("utf-8", errors="replace")

    try:
        response_body = json.dumps(resp.json(), ensure_ascii=False)
    except ValueError:
        response_body = resp.text

    logger.info(
        "HTTP 请求详情",
        method=resp.request.method,
        url=resp.request.url,
        headers=dict(resp.request.headers),
        body=request_body,
    )
    logger.info(
        "HTTP 响应详情",
        status_code=resp.status_code,
        url=resp.url,
        headers=dict(resp.headers),
        body=response_body,
    )


def get_unique_codes(count: int) -> list[int]:
    """按 n=xx 批量请求雪花 ID。"""
    if count <= 0:
        return []

    resp = get_with_retry(
        url=settings.snowflake_id_url,
        params={"n": count},
        timeout=REQUEST_TIMEOUT,
        backoff_seconds=BACKOFF_SECONDS,
    )
    _log_http_detail(resp)
    resp.raise_for_status()

    payload = resp.json()
    if not isinstance(payload, list):
        raise ValueError("雪花 ID 服务返回格式错误")
    if len(payload) != count:
        raise RuntimeError(
            f"雪花 ID 服务返回数量错误: 预期 {count}, 实际 {len(payload)}"
        )
    return [int(code) for code in payload]


def get_unique_code() -> int:
    """从雪花 ID 服务获取单个唯一编码。"""
    return get_unique_codes(1)[0]
