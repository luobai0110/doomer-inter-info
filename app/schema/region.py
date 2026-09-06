from pydantic import BaseModel, ConfigDict, Field


class RegionRecord(BaseModel):
    """Excel 一行行政区划数据的内存表示，中文表头作为字段别名。"""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    province_name: str = Field(alias="省name")
    province_gb: str = Field(alias="省gb")
    city_name: str = Field(alias="市name")
    city_gb: str = Field(alias="市gb")
    county_name: str = Field(alias="县name")
    county_gb: str = Field(alias="县gb")


class RegionCreate(BaseModel):
    """行政区划 Excel 记录新增入参。"""

    id: int
    province_name: str = Field(max_length=100)
    province_gb: str = Field(max_length=20)
    city_name: str = Field(max_length=100)
    city_gb: str = Field(max_length=20)
    county_name: str = Field(max_length=100)
    county_gb: str = Field(max_length=20)


class RegionUpdate(BaseModel):
    """行政区划 Excel 记录更新入参，只更新调用方显式传入的字段。"""

    province_name: str | None = Field(default=None, max_length=100)
    province_gb: str | None = Field(default=None, max_length=20)
    city_name: str | None = Field(default=None, max_length=100)
    city_gb: str | None = Field(default=None, max_length=20)
    county_name: str | None = Field(default=None, max_length=100)
    county_gb: str | None = Field(default=None, max_length=20)


class RegionOut(BaseModel):
    """行政区划 Excel 记录输出。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    province_name: str
    province_gb: str
    city_name: str
    city_gb: str
    county_name: str
    county_gb: str
