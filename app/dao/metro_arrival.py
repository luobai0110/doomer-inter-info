from sqlalchemy import select
from sqlalchemy.orm import Session

from app.model.metro import MetroArrivalRecord
from app.schema.metro import MetroArrivalRecordCreate, MetroArrivalRecordUpdate
from app.service.snowflake import get_unique_code


def create_metro_arrival_record(
    db: Session,
    data: MetroArrivalRecordCreate,
) -> MetroArrivalRecord:
    """新增到站记录，record_code 自动取自雪花 ID 服务。"""
    record = MetroArrivalRecord(**data.model_dump())
    record.record_code = str(get_unique_code())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_metro_arrival_record(
    db: Session,
    record_id: int,
) -> MetroArrivalRecord | None:
    """按主键查询到站记录。"""
    return db.get(MetroArrivalRecord, record_id)


def list_metro_arrival_records(
    db: Session,
    skip: int = 0,
    limit: int = 100,
) -> list[MetroArrivalRecord]:
    """分页查询到站记录。"""
    return list(
        db.scalars(
            select(MetroArrivalRecord)
            .order_by(MetroArrivalRecord.id)
            .offset(skip)
            .limit(limit)
        )
    )


def update_metro_arrival_record(
    db: Session,
    record_id: int,
    data: MetroArrivalRecordUpdate,
) -> MetroArrivalRecord | None:
    """更新到站记录，记录不存在时返回 None。"""
    record = get_metro_arrival_record(db, record_id)
    if record is None:
        return None

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return record


def delete_metro_arrival_record(db: Session, record_id: int) -> bool:
    """删除到站记录，返回是否删除成功。"""
    record = get_metro_arrival_record(db, record_id)
    if record is None:
        return False

    db.delete(record)
    db.commit()
    return True
