import time
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """通用响应结构，与其他服务保持一致。"""

    code: int
    message: str | None
    data: T | None
    timestamp: int


def _now_millis() -> int:
    """返回当前时间的毫秒时间戳。"""
    return int(time.time() * 1000)


def ok(
    data: T | None = None,
    message: str = "SUCCESS",
    code: int = 200,
) -> ApiResponse[T]:
    """构造成功响应。"""
    return ApiResponse(
        code=code,
        message=message,
        data=data,
        timestamp=_now_millis(),
    )


def fail(
    message: str,
    code: int = 500,
    data: T | None = None,
) -> ApiResponse[T]:
    """构造失败响应。"""
    return ApiResponse(
        code=code,
        message=message,
        data=data,
        timestamp=_now_millis(),
    )
