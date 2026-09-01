import requests
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import now

from app.model.weather import Weather

history_url = "https://historical-forecast-api.open-meteo.com/v1/forecast"


def get_weather_data():



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



if __name__ == '__main__':
    get_weather_data()
