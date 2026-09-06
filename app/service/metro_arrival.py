from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.model.metro import MetroArrivalRecord
from app.schema.metro import (
    MetroArrivalRecordPage,
    MetroArrivalRecordCreate,
    MetroArrivalRecordUpdate,
)
from app.service.snowflake import get_unique_code, get_unique_codes


def create_metro_arrival_record(
        db: Session,
        data: MetroArrivalRecordCreate,
) -> MetroArrivalRecord:
    """新增单条到站记录，record_code 自动取自雪花 ID 服务。"""
    record = MetroArrivalRecord(**data.model_dump())
    record.record_code = str(get_unique_code())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def create_metro_arrival_record_from_json(
        db: Session,
        data: dict[str, Any],
) -> MetroArrivalRecord:
    """新增单条到站记录，入参为外部下载的原始 JSON 对象。"""
    record_data = MetroArrivalRecordCreate.model_validate(data)
    return create_metro_arrival_record(db, record_data)


def create_metro_arrival_records(
        db: Session,
        data_list: list[MetroArrivalRecordCreate],
) -> list[MetroArrivalRecord]:
    """批量新增到站记录，一次请求 n=len(data) 个雪花 ID。"""
    if not data_list:
        return []

    codes = get_unique_codes(len(data_list))
    records = [MetroArrivalRecord(**data.model_dump()) for data in data_list]
    for record, code in zip(records, codes):
        record.record_code = str(code)
    db.add_all(records)
    db.commit()
    for record in records:
        db.refresh(record)
    return records


def get_metro_arrival_record(
        db: Session,
        record_id: int,
) -> MetroArrivalRecord | None:
    """按主键查询到站记录。"""
    return db.scalar(
        select(MetroArrivalRecord).where(MetroArrivalRecord.id == record_id)
    )


def list_metro_arrival_records(
        db: Session,
        *,
        offset: int = 0,
        limit: int = 100,
        line_code: str | None = None,
        station_code: str | None = None,
        value_end_dttm: date | None = None,
) -> MetroArrivalRecordPage:
    """按线路、站点和所属日期分页查询到站记录。"""
    stmt = select(MetroArrivalRecord)
    if line_code is not None:
        stmt = stmt.where(MetroArrivalRecord.line_code == line_code)
    if station_code is not None:
        stmt = stmt.where(MetroArrivalRecord.station_code == station_code)
    if value_end_dttm is not None:
        stmt = stmt.where(MetroArrivalRecord.value_end_dttm == value_end_dttm)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(
        db.scalars(
            stmt.order_by(
                MetroArrivalRecord.value_end_dttm,
                MetroArrivalRecord.order_no,
                MetroArrivalRecord.id,
            )
            .offset(offset)
            .limit(limit)
        )
    )
    return MetroArrivalRecordPage(total=total, items=items)


def update_metro_arrival_record(
        db: Session,
        record_id: int,
        data: MetroArrivalRecordUpdate,
) -> MetroArrivalRecord | None:
    """更新到站记录，未传字段保持原值。"""
    record = get_metro_arrival_record(db, record_id)
    if record is None:
        return None

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return record


def delete_metro_arrival_record(db: Session, record_id: int) -> bool:
    """删除到站记录，返回是否存在且删除成功。"""
    record = get_metro_arrival_record(db, record_id)
    if record is None:
        return False

    db.delete(record)
    db.commit()
    return True
