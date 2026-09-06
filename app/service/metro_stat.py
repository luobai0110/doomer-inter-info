from datetime import date, time
from decimal import Decimal

from fastapi import Depends
from sqlalchemy import extract, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.model.metro import MetroArrivalRecord
from app.model.metro_stat import MetroDailyArrivalStat
from app.service.snowflake import MAX_CODES_PER_REQUEST, get_unique_codes

logger = get_logger(__name__)

# 单批 upsert 最大行数：每行 10 列，避免超出 PostgreSQL 65535 的参数上限。
UPSERT_BATCH_SIZE = 500

# 新统计行的默认加权值，与表列 server_default 保持一致。
DEFAULT_WEIGHT = Decimal("1.0")

DimKey = tuple[date, str, str, str]


def _load_existing_weights(
    db: Session,
    stat_date: date | None,
) -> dict[DimKey, Decimal]:
    """读取统计范围内已有行的加权值，重算时保留人工调整。"""
    stmt = select(
        MetroDailyArrivalStat.stat_date,
        MetroDailyArrivalStat.line_code,
        MetroDailyArrivalStat.direction_code,
        MetroDailyArrivalStat.station_code,
        MetroDailyArrivalStat.weight,
    )
    if stat_date is not None:
        stmt = stmt.where(MetroDailyArrivalStat.stat_date == stat_date)
    return {
        (
            row.stat_date,
            row.line_code,
            row.direction_code,
            row.station_code,
        ): row.weight
        for row in db.execute(stmt)
    }


def _build_stat_rows(
    db: Session,
    stat_date: date | None,
    existing_weights: dict[DimKey, Decimal],
) -> list[dict[str, object]]:
    """按日期、线路、方向、站点聚合平均到站时刻，并按加权值修正出实际到站时间。"""
    avg_seconds = func.avg(extract("epoch", MetroArrivalRecord.arrvie_time))
    stmt = (
        select(
            MetroArrivalRecord.value_end_dttm.label("stat_date"),
            MetroArrivalRecord.line_code,
            MetroArrivalRecord.direction_code,
            MetroArrivalRecord.station_code,
            # 描述性列不参与分组，取确定性代表值；
            # 分组键与 upsert 冲突键严格一致，避免同批出现重复键。
            func.min(MetroArrivalRecord.line_name).label("line_name"),
            func.min(MetroArrivalRecord.direction).label("direction"),
            func.min(MetroArrivalRecord.station_name).label("station_name"),
            avg_seconds.label("avg_seconds"),
            func.count().label("record_count"),
        )
        .group_by(
            MetroArrivalRecord.value_end_dttm,
            MetroArrivalRecord.line_code,
            MetroArrivalRecord.direction_code,
            MetroArrivalRecord.station_code,
        )
        .order_by(
            MetroArrivalRecord.value_end_dttm,
            MetroArrivalRecord.line_code,
            MetroArrivalRecord.direction_code,
            MetroArrivalRecord.station_code,
        )
    )
    if stat_date is not None:
        stmt = stmt.where(MetroArrivalRecord.value_end_dttm == stat_date)

    rows: list[dict[str, object]] = []
    for record in db.execute(stmt):
        # 平均到站时刻：把到站时间折算为当天秒数取平均，四舍五入后还原为时刻。
        avg_secs = round(float(record.avg_seconds))
        # 实际到站时间：按该行加权值（已有人工调整则沿用）修正平均时刻，
        # 仅保留修正结果，修正差值不记录。
        weight = float(
            existing_weights.get(
                (
                    record.stat_date,
                    record.line_code,
                    record.direction_code,
                    record.station_code,
                ),
                DEFAULT_WEIGHT,
            )
        )
        actual_secs = round(avg_secs * weight)
        rows.append(
            {
                "stat_date": record.stat_date,
                "line_code": record.line_code,
                "line_name": record.line_name,
                "direction_code": record.direction_code,
                "direction": record.direction,
                "station_code": record.station_code,
                "station_name": record.station_name,
                "avg_arrival_time": time(
                    avg_secs // 3600, (avg_secs % 3600) // 60, avg_secs % 60
                ),
                "actual_arrival_time": time(
                    actual_secs // 3600,
                    (actual_secs % 3600) // 60,
                    actual_secs % 60,
                ),
                "record_count": record.record_count,
            }
        )
    return rows


def _backfill_missing_stat_codes(db: Session) -> int:
    """为 stat_code 为空的统计记录批量申请雪花 ID 并回填。

    新入库的统计行先置空，统计完成后一次性批量申请；
    申请失败时不阻断流程，记录异常后等待下次统计重试。
    """
    stats = list(
        db.scalars(
            select(MetroDailyArrivalStat)
            .where(
                or_(
                    MetroDailyArrivalStat.stat_code.is_(None),
                    MetroDailyArrivalStat.stat_code == "",
                )
            )
            .order_by(MetroDailyArrivalStat.id)
        )
    )
    if not stats:
        logger.debug("统计记录均已具备雪花ID，无需补发")
        return 0

    logger.info(
        "发现缺少雪花ID的统计记录，开始分批申请",
        count=len(stats),
        batch_size=MAX_CODES_PER_REQUEST,
    )
    assigned = 0
    try:
        for start in range(0, len(stats), MAX_CODES_PER_REQUEST):
            chunk = stats[start : start + MAX_CODES_PER_REQUEST]
            codes = get_unique_codes(len(chunk))
            for stat, code in zip(chunk, codes, strict=True):
                stat.stat_code = str(code)
            db.commit()
            assigned += len(chunk)
    except Exception:
        db.rollback()
        logger.exception("雪花ID申请失败，剩余记录下次统计时重试", assigned=assigned)
    if assigned:
        logger.info("统计记录雪花ID补发完成", count=assigned)
    return assigned


def calc_daily_avg_arrival_time(
    db: Session = Depends(get_db),
    stat_date: date | None = None,
) -> int:
    """计算每日地铁到站平均时刻并 upsert 入 metro_daily_arrival_stats。

    按统计日期、线路、方向、站点分组；avg_arrival_time 为统计原始值，
    同时按行上加权值（默认 1.0，可人工调整）修正出 actual_arrival_time
    一并落库，修正差值本身不记录。stat_date 为空时全量重算，传入日期
    时只重算该日；已有行的加权值与雪花ID在重算时保留。返回统计分组数。
    """
    logger.info("开始统计每日平均到站时间", stat_date=stat_date)
    existing_weights = _load_existing_weights(db, stat_date)
    rows = _build_stat_rows(db, stat_date, existing_weights)
    if not rows:
        logger.info("无到站记录可统计，跳过", stat_date=stat_date)
        return 0

    for start in range(0, len(rows), UPSERT_BATCH_SIZE):
        batch = rows[start : start + UPSERT_BATCH_SIZE]
        stmt = pg_insert(MetroDailyArrivalStat).values(batch)
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                MetroDailyArrivalStat.stat_date,
                MetroDailyArrivalStat.line_code,
                MetroDailyArrivalStat.direction_code,
                MetroDailyArrivalStat.station_code,
            ],
            set_={
                "line_name": stmt.excluded.line_name,
                "direction": stmt.excluded.direction,
                "station_name": stmt.excluded.station_name,
                "avg_arrival_time": stmt.excluded.avg_arrival_time,
                "actual_arrival_time": stmt.excluded.actual_arrival_time,
                "record_count": stmt.excluded.record_count,
            },
        )
        db.execute(stmt)
    db.commit()
    logger.info(
        "每日平均到站时间统计完成",
        stat_group_count=len(rows),
        stat_date=stat_date,
    )
    _backfill_missing_stat_codes(db)
    return len(rows)
