import uuid
from datetime import datetime

import openmeteo_requests
import requests_cache
from retry_requests import retry
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.model.weather import Weather

url = "https://api.open-meteo.com/v1/forecast"

params = {
    "latitude": 52.52,
    "longitude": 13.41,
    "daily": ["weather_code", "temperature_2m_max", "temperature_2m_min", "apparent_temperature_max", "apparent_temperature_min", "uv_index_max", "uv_index_clear_sky_max", "moon_phase", "moonset", "moonrise", "sunshine_duration", "daylight_duration", "sunset", "sunrise", "rain_sum", "showers_sum", "snowfall_sum", "precipitation_sum", "precipitation_hours", "precipitation_probability_max", "et0_fao_evapotranspiration", "shortwave_radiation_sum", "wind_direction_10m_dominant", "wind_gusts_10m_max", "wind_speed_10m_max"],
    "hourly": ["temperature_2m", "relative_humidity_2m", "dew_point_2m", "apparent_temperature", "precipitation_probability", "precipitation", "rain", "snowfall", "showers", "snow_depth", "weather_code", "pressure_msl", "surface_pressure", "cloud_cover", "cloud_cover_low", "cloud_cover_mid", "cloud_cover_high", "visibility", "evapotranspiration", "et0_fao_evapotranspiration", "vapour_pressure_deficit", "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m", "temperature_80m", "soil_temperature_0cm", "soil_moisture_0_to_1cm"],
    "timezone": "Asia/Singapore",
}

cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)


def _serialize_variable_values(variable) -> list[float | None] | None:
    """将 Open-Meteo 变量序列化为可存入 JSONB 的普通列表。"""
    if variable is None or variable.ValuesIsNone():
        return None
    return [None if value != value else value for value in variable.ValuesAsNumpy().tolist()]


def _to_text(value) -> object:
    """Open-Meteo 的字符串字段实际返回 bytes，转为 str 以便 JSON 序列化。"""
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def _serialize_block(block) -> dict[str, object] | None:
    """序列化 Open-Meteo 的日/时级数据块。"""
    if block is None:
        return None
    return {
        "time": block.Time(),
        "time_end": block.TimeEnd(),
        "interval": block.Interval(),
        "variables": [
            {
                "variable": variable.Variable(),
                "unit": variable.Unit(),
                "values": _serialize_variable_values(variable),
            }
            for variable in (block.Variables(i) for i in range(block.VariablesLength()))
            if variable is not None
        ],
    }


def _serialize_response(response) -> dict[str, object]:
    """将单个 Open-Meteo 响应转为 JSON 安全的字典。"""
    return {
        "latitude": response.Latitude(),
        "longitude": response.Longitude(),
        "elevation": response.Elevation(),
        "generation_time_ms": response.GenerationTimeMilliseconds(),
        "timezone": _to_text(response.Timezone()),
        "timezone_abbreviation": _to_text(response.TimezoneAbbreviation()),
        "current": _serialize_block(response.Current()),
        "hourly": _serialize_block(response.Hourly()),
        "daily": _serialize_block(response.Daily()),
    }


def get_weather_data(
    db: Session,
    latitude: float = 52.52,
    longitude: float = 13.41,
) -> Weather:
    """拉取 Open-Meteo 天气数据并写入数据库。"""
    request_params = {**params, "latitude": latitude, "longitude": longitude}
    responses = openmeteo.weather_api(url=url, params=request_params)
    data: dict[str, object] = {
        "code": uuid.uuid4().int & ((1 << 63) - 1),
        "area_code": "test",
        "area_name": "HZ",
        "data_date": datetime.utcnow(),
        "data_type": "NOW",
        "source": "openmeteo",
        "raw_data": [_serialize_response(response) for response in responses],
        "status": "PENDING",
    }
    return create_weather(db=db, data=data)



def create_weather(db: Session, data: dict[str, object]) -> Weather:
    """创建天气记录。"""
    weather = Weather(**data)
    db.add(weather)
    db.commit()
    db.refresh(weather)
    return weather


def get_weather(db: Session, weather_id: int) -> Weather | None:
    """按主键查询天气记录。"""
    return db.get(Weather, weather_id)


def get_weather_by_code(db: Session, code: int) -> Weather | None:
    """按业务编码查询天气记录。"""
    return db.scalar(select(Weather).where(Weather.code == code))


def list_weathers(
    db: Session,
    skip: int = 0,
    limit: int = 100,
) -> list[Weather]:
    """分页查询天气记录。"""
    return list(db.scalars(select(Weather).offset(skip).limit(limit)))


def update_weather(
    db: Session,
    weather_id: int,
    data: dict[str, object],
) -> Weather | None:
    """更新天气记录，记录不存在时返回 None。"""
    weather = get_weather(db, weather_id)
    if weather is None:
        return None
    for field, value in data.items():
        setattr(weather, field, value)
    db.commit()
    db.refresh(weather)
    return weather


def delete_weather(db: Session, weather_id: int) -> bool:
    """删除天气记录，返回是否删除成功。"""
    weather = get_weather(db, weather_id)
    if weather is None:
        return False
    db.delete(weather)
    db.commit()
    return True
