from pydantic import BaseModel, ConfigDict, Field


class StationCreate(BaseModel):
    """车站信息新增入参。"""

    map_code: str | None = Field(default=None, max_length=50)
    station_name: str | None = Field(default=None, max_length=50)
    station_code: str | None = Field(default=None, max_length=50)


class StationUpdate(BaseModel):
    """车站信息更新入参，只更新调用方显式传入的字段。"""

    map_code: str | None = Field(default=None, max_length=50)
    station_name: str | None = Field(default=None, max_length=50)
    station_code: str | None = Field(default=None, max_length=50)


class StationOut(BaseModel):
    """车站信息输出。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    map_code: str | None
    station_name: str | None
    station_code: str | None
