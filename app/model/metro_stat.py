from sqlalchemy import (
    BigInteger, Column, Date, Index, Integer, Numeric, String, Time, text
)

from app.core.database import Base


class MetroDailyArrivalStat(Base):
    """地铁每日到站统计表：按日期、线路、方向、站点统计平均到站时刻。

    avg_arrival_time 为统计原始值；weight 为实际到站修正加权值
    （默认 1.0，可人工调整），统计后按其修正出 actual_arrival_time，
    修正差值本身不记录。
    """

    __tablename__ = "metro_daily_arrival_stats"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID（自增）")
    stat_code = Column(String(50), comment="雪花ID")
    stat_date = Column(Date, nullable=False, comment="统计日期")
    line_code = Column(String(10), nullable=False, comment="线路编码")
    line_name = Column(String(50), nullable=False, comment="线路名称")
    direction_code = Column(String(10), nullable=False, comment="方向编码")
    direction = Column(String(50), nullable=False, comment="方向描述")
    station_code = Column(String(20), nullable=False, comment="站点编码")
    station_name = Column(String(100), nullable=False, comment="站点名称")
    avg_arrival_time = Column(Time, nullable=False, comment="平均到站时刻（统计原始值）")
    weight = Column(
        Numeric(10, 4),
        nullable=False,
        server_default=text("1.0"),
        comment="实际到站修正加权值",
    )
    actual_arrival_time = Column(
        Time, comment="实际到站时间（平均到站时刻×加权值，统计后修正）"
    )
    record_count = Column(Integer, nullable=False, comment="参与统计的到站记录数")

    __table_args__ = (
        Index(
            "ux_metro_daily_arrival_stats_dim",
            "stat_date",
            "line_code",
            "direction_code",
            "station_code",
            unique=True,
        ),
        {"comment": "地铁每日到站统计表"},
    )

    def __repr__(self) -> str:
        return (
            f"<MetroDailyArrivalStat(stat_code={self.stat_code}, "
            f"stat_date={self.stat_date}, line_code={self.line_code}, "
            f"direction_code={self.direction_code}, "
            f"station_code={self.station_code}, "
            f"avg_arrival_time={self.avg_arrival_time}, weight={self.weight}, "
            f"actual_arrival_time={self.actual_arrival_time})>"
        )
