from sqlalchemy import select
from sqlalchemy.orm import Session

from app.model.station import Station
from app.schema.station import StationCreate, StationUpdate


def create_station(db: Session, data: StationCreate) -> Station:
    """新增车站信息。"""
    station = Station(**data.model_dump())
    db.add(station)
    db.commit()
    db.refresh(station)
    return station


def get_station(db: Session, station_id: int) -> Station | None:
    """按主键查询车站信息。"""
    return db.get(Station, station_id)


def get_station_by_map_code(db: Session, map_code: str) -> Station | None:
    """按雪花 ID 查询车站信息。"""
    return db.scalar(select(Station).where(Station.map_code == map_code))


def get_station_by_station_code(db: Session, station_code: str) -> Station | None:
    """按车站编号查询车站信息。"""
    return db.scalar(select(Station).where(Station.station_code == station_code))


def list_stations(
    db: Session,
    skip: int = 0,
    limit: int = 100,
) -> list[Station]:
    """分页查询车站信息。"""
    return list(
        db.scalars(
            select(Station)
            .order_by(Station.id)
            .offset(skip)
            .limit(limit)
        )
    )


def update_station(
    db: Session,
    station_id: int,
    data: StationUpdate,
) -> Station | None:
    """更新车站信息，记录不存在时返回 None。"""
    station = get_station(db, station_id)
    if station is None:
        return None

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(station, field, value)
    db.commit()
    db.refresh(station)
    return station


def delete_station(db: Session, station_id: int) -> bool:
    """删除车站信息，返回是否删除成功。"""
    station = get_station(db, station_id)
    if station is None:
        return False

    db.delete(station)
    db.commit()
    return True
