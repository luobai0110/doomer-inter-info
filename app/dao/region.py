from sqlalchemy import select
from sqlalchemy.orm import Session

from app.model.region import Region
from app.schema.region import RegionCreate, RegionUpdate


def create_region(db: Session, data: RegionCreate) -> Region:
    """新增行政区划 Excel 记录。"""
    region = Region(**data.model_dump())
    db.add(region)
    db.commit()
    db.refresh(region)
    return region


def get_region(db: Session, region_id: int) -> Region | None:
    """按主键（Excel id）查询行政区划记录。"""
    return db.get(Region, region_id)


def get_region_by_province_gb(db: Session, province_gb: str) -> list[Region]:
    """按省编码查询行政区划记录。"""
    return list(
        db.scalars(select(Region).where(Region.province_gb == province_gb))
    )


def list_regions(
    db: Session,
    skip: int = 0,
    limit: int = 100,
) -> list[Region]:
    """分页查询行政区划 Excel 记录。"""
    return list(
        db.scalars(
            select(Region)
            .order_by(Region.id)
            .offset(skip)
            .limit(limit)
        )
    )


def update_region(
    db: Session,
    region_id: int,
    data: RegionUpdate,
) -> Region | None:
    """更新行政区划 Excel 记录，记录不存在时返回 None。"""
    region = get_region(db, region_id)
    if region is None:
        return None

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(region, field, value)
    db.commit()
    db.refresh(region)
    return region


def delete_region(db: Session, region_id: int) -> bool:
    """删除行政区划 Excel 记录，返回是否删除成功。"""
    region = get_region(db, region_id)
    if region is None:
        return False

    db.delete(region)
    db.commit()
    return True
