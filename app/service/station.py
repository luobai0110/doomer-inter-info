from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.model.station import Station


def sync_station_data(db: Session = Depends(get_db)) -> int:
    """从到站记录表同步站点数据，按 station_code 更新或插入。"""
    records = db.execute(
        text(
            """
            SELECT station_code, station_name
            FROM metro_arrival_records
            GROUP BY station_name, station_code
            ORDER BY station_name
            """
        )
    ).all()

    stations = {
        record.station_code: record.station_name
        for record in records
    }
    if not stations:
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
    return len(stations)
