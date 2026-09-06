from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MetroArrivalRecordCreate(BaseModel):
    """地铁到站记录新增入参，record_code 由服务端雪花 ID 生成。"""

    @field_validator("arrvie_time", mode="before")
    @classmethod
    def normalize_end_of_day(cls, value: object) -> object:
        # 数据源用 24:00 表示当天最后一刻，Python time 无法表示，统一存为 00:00。
        if value == "24:00":
            return "00:00"
        return value

    line_name: str = Field(max_length=50)
    line_code: str = Field(max_length=10)
    direction: str = Field(max_length=50)
    direction_code: str = Field(max_length=10)
    station_name: str = Field(max_length=100)
    station_code: str = Field(max_length=20)
    order_no: int
    arrvie_time: time
    train_seq_no: str | None = Field(default=None, max_length=50)
    value_end_dttm: date


class MetroArrivalRecordUpdate(BaseModel):
    """地铁到站记录更新入参，只更新调用方显式传入的字段。"""

    line_name: str | None = Field(default=None, max_length=50)
    line_code: str | None = Field(default=None, max_length=10)
    direction: str | None = Field(default=None, max_length=50)
    direction_code: str | None = Field(default=None, max_length=10)
    station_name: str | None = Field(default=None, max_length=100)
    station_code: str | None = Field(default=None, max_length=20)
    order_no: int | None = None
    arrvie_time: time | None = None
    train_seq_no: str | None = Field(default=None, max_length=50)
    value_end_dttm: date | None = None


class MetroArrivalRecordOut(BaseModel):
    """地铁到站记录输出。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    record_code: str
    line_name: str
    line_code: str
    direction: str
    direction_code: str
    station_name: str
    station_code: str
    order_no: int
    arrvie_time: time
    train_seq_no: str | None
    value_end_dttm: date
    created_at: datetime | None


class MetroArrivalRecordPage(BaseModel):
    """地铁到站记录分页结果。"""

    total: int
    items: list[MetroArrivalRecordOut]
