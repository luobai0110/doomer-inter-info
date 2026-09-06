from pydantic import BaseModel, ConfigDict, Field


class AreaCreate(BaseModel):
    """行政区划新增入参，code 为雪花 ID。"""

    code: int
    area_code: str = Field(max_length=50)
    area_name: str | None = Field(default=None, max_length=100)
    longitude: float | None = None
    latitude: float | None = None
    province_code: int | None = None
    province_name: str | None = Field(default=None, max_length=50)
    city_code: int | None = None
    city_name: str | None = Field(default=None, max_length=50)
    district_code: int | None = None
    district_name: str | None = Field(default=None, max_length=50)
    street_code: int | None = None
    street_name: str | None = Field(default=None, max_length=50)
    level: int | None = None
    full_name: str | None = Field(default=None, max_length=200)


class AreaUpdate(BaseModel):
    """行政区划更新入参，只更新调用方显式传入的字段。"""

    code: int | None = None
    area_code: str | None = Field(default=None, max_length=50)
    area_name: str | None = Field(default=None, max_length=100)
    longitude: float | None = None
    latitude: float | None = None
    province_code: int | None = None
    province_name: str | None = Field(default=None, max_length=50)
    city_code: int | None = None
    city_name: str | None = Field(default=None, max_length=50)
    district_code: int | None = None
    district_name: str | None = Field(default=None, max_length=50)
    street_code: int | None = None
    street_name: str | None = Field(default=None, max_length=50)
    level: int | None = None
    full_name: str | None = Field(default=None, max_length=200)


class AreaOut(BaseModel):
    """行政区划输出。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: int
    area_code: str
    area_name: str | None
    longitude: float | None
    latitude: float | None
    province_code: int | None
    province_name: str | None
    city_code: int | None
    city_name: str | None
    district_code: int | None
    district_name: str | None
    street_code: int | None
    street_name: str | None
    level: int | None
    full_name: str | None
