from sqlalchemy import select
from sqlalchemy.orm import Session

from app.model.area import Area
from app.schema.area import AreaCreate, AreaUpdate


def create_area(db: Session, data: AreaCreate) -> Area:
    """新增行政区划记录。"""
    area = Area(**data.model_dump())
    db.add(area)
    db.commit()
    db.refresh(area)
    return area


def get_area(db: Session, area_id: int) -> Area | None:
    """按主键查询行政区划记录。"""
    return db.get(Area, area_id)


def get_area_by_code(db: Session, code: int) -> Area | None:
    """按雪花 ID 查询行政区划记录。"""
    return db.scalar(select(Area).where(Area.code == code))


def get_area_by_area_code(db: Session, area_code: str) -> Area | None:
    """按行政区划编码查询记录。"""
    return db.scalar(select(Area).where(Area.area_code == area_code))


def list_areas(
    db: Session,
    skip: int = 0,
    limit: int = 100,
) -> list[Area]:
    """分页查询行政区划记录。"""
    return list(
        db.scalars(
            select(Area)
            .order_by(Area.id)
            .offset(skip)
            .limit(limit)
        )
    )


def update_area(
    db: Session,
    area_id: int,
    data: AreaUpdate,
) -> Area | None:
    """更新行政区划记录，记录不存在时返回 None。"""
    area = get_area(db, area_id)
    if area is None:
        return None

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(area, field, value)
    db.commit()
    db.refresh(area)
    return area


def delete_area(db: Session, area_id: int) -> bool:
    """删除行政区划记录，返回是否删除成功。"""
    area = get_area(db, area_id)
    if area is None:
        return False

    db.delete(area)
    db.commit()
    return True
