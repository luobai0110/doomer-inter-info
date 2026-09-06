from sqlalchemy import select
from sqlalchemy.orm import Session

from app.model.weather import Weather
from app.schema.weather import WeatherCreate, WeatherUpdate


def create_weather(db: Session, data: WeatherCreate) -> Weather:
    """新增天气记录。"""
    weather = Weather(**data.model_dump())
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
    return list(
        db.scalars(
            select(Weather)
            .order_by(Weather.id)
            .offset(skip)
            .limit(limit)
        )
    )


def update_weather(
    db: Session,
    weather_id: int,
    data: WeatherUpdate,
) -> Weather | None:
    """更新天气记录，记录不存在时返回 None。"""
    weather = get_weather(db, weather_id)
    if weather is None:
        return None

    for field, value in data.model_dump(exclude_unset=True).items():
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
