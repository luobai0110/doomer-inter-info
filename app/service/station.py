from fastapi import Depends
from sqlalchemy import or_, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.model.metro import MetroArrivalRecord
from app.model.station import Station
from app.service.snowflake import MAX_CODES_PER_REQUEST, get_unique_codes

logger = get_logger(__name__)

UNIQUE_INDEX_NAME = "ux_station_station_code"
LEGACY_INDEX_NAME = "idx_station_station_code"


def _ensure_station_unique_index(db: Session) -> None:
    """确保 station_code 唯一索引存在，upsert 的 ON CONFLICT 依赖该索引。

    create_all 只创建缺失的表，不会为已存在的旧表补建索引，
    因此同步前按需补齐；旧表若存在非唯一索引则一并清理。
    """
    index_names = set(
        db.execute(
            text("SELECT indexname FROM pg_indexes WHERE tablename = 'station'")
        ).scalars()
    )
    if UNIQUE_INDEX_NAME in index_names:
        return
    if LEGACY_INDEX_NAME in index_names:
        logger.warning("清理 station_code 上的旧非唯一索引", index=LEGACY_INDEX_NAME)
        db.execute(text(f"DROP INDEX {LEGACY_INDEX_NAME}"))
    logger.warning("补建 station_code 唯一索引", index=UNIQUE_INDEX_NAME)
    db.execute(
        text(f"CREATE UNIQUE INDEX {UNIQUE_INDEX_NAME} ON station (station_code)")
    )
    db.commit()


def _backfill_missing_map_codes(db: Session) -> int:
    """为 map_code 为空的站点分批申请雪花 ID 并回填。

    首次启动同步后全部站点均无 map_code，此处按雪花服务单次上限
    分批申请；后续同步仅对新入库且缺码的站点补发。单批失败时保留
    已补发进度，不阻断启动，剩余站点下次同步时重试。
    """
    stations = list(
        db.scalars(
            select(Station)
            .where(or_(Station.map_code.is_(None), Station.map_code == ""))
            .order_by(Station.id)
        )
    )
    if not stations:
        logger.debug("站点均已具备雪花ID，无需补发")
        return 0

    logger.info(
        "发现缺少雪花ID的站点，开始分批申请",
        count=len(stations),
        batch_size=MAX_CODES_PER_REQUEST,
    )
    assigned = 0
    try:
        for start in range(0, len(stations), MAX_CODES_PER_REQUEST):
            chunk = stations[start : start + MAX_CODES_PER_REQUEST]
            codes = get_unique_codes(len(chunk))
            for station, code in zip(chunk, codes, strict=True):
                station.map_code = str(code)
            db.commit()
            assigned += len(chunk)
    except Exception:
        db.rollback()
        logger.exception("雪花ID申请失败，剩余站点下次同步时重试", assigned=assigned)
    if assigned:
        logger.info("站点雪花ID补发完成", count=assigned)
    return assigned


def sync_station_data(db: Session = Depends(get_db)) -> int:
    """从到站记录表同步站点数据，按 station_code 更新或插入。"""
    logger.info("开始同步站点数据")
    _ensure_station_unique_index(db)
    records = db.execute(
        select(
            MetroArrivalRecord.station_code,
            MetroArrivalRecord.station_name,
        )
        .group_by(
            MetroArrivalRecord.station_name,
            MetroArrivalRecord.station_code,
        )
        .order_by(MetroArrivalRecord.station_name)
    ).all()

    stations = {
        record.station_code: record.station_name
        for record in records
    }
    if not stations:
        logger.info("到站记录表暂无站点数据，跳过同步")
        return 0

    stmt = pg_insert(Station).values(
        [
            {"station_code": code, "station_name": name}
            for code, name in stations.items()
        ]
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[Station.station_code],
        set_={"station_name": stmt.excluded.station_name},
    )
    db.execute(stmt)
    db.commit()
    logger.info("站点数据同步完成", station_count=len(stations))
    _backfill_missing_map_codes(db)
    return len(stations)
