from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WeatherCreate(BaseModel):
    """天气记录新增入参，code 为业务唯一编码。"""

    code: int
    area_code: str = Field(max_length=50)
    area_name: str | None = Field(default=None, max_length=100)
    data_date: datetime
    data_type: str | None = Field(default=None, max_length=20)
    source: str | None = Field(default=None, max_length=100)
    raw_data: dict[str, Any] | list[Any] | None = None
    cleand_data: dict[str, Any] | list[Any] | None = None
    status: str | None = Field(default=None, max_length=20)
    clean_version: str | None = Field(default=None, max_length=20)
    quality_score: int | None = Field(default=None, ge=0, le=100)
    has_error: bool | None = None
    error_message: str | None = None
    retry_count: int | None = None
    expired_at: datetime | None = None


class WeatherUpdate(BaseModel):
    """天气记录更新入参，只更新调用方显式传入的字段。"""

    code: int | None = None
    area_code: str | None = Field(default=None, max_length=50)
    area_name: str | None = Field(default=None, max_length=100)
    data_date: datetime | None = None
    data_type: str | None = Field(default=None, max_length=20)
    source: str | None = Field(default=None, max_length=100)
    raw_data: dict[str, Any] | list[Any] | None = None
    cleand_data: dict[str, Any] | list[Any] | None = None
    status: str | None = Field(default=None, max_length=20)
    clean_version: str | None = Field(default=None, max_length=20)
    quality_score: int | None = Field(default=None, ge=0, le=100)
    has_error: bool | None = None
    error_message: str | None = None
    retry_count: int | None = None
    expired_at: datetime | None = None


class WeatherOut(BaseModel):
    """天气记录输出。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: int
    area_code: str
    area_name: str | None
    data_date: datetime
    data_type: str | None
    source: str | None
    raw_data: dict[str, Any] | list[Any] | None
    cleand_data: dict[str, Any] | list[Any] | None
    status: str | None
    clean_version: str | None
    quality_score: int | None
    has_error: bool | None
    error_message: str | None
    retry_count: int | None
    created_at: datetime | None
    updated_at: datetime | None
    expired_at: datetime | None
