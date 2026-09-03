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
