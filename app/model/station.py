from sqlalchemy import BigInteger, Column, Index, String

from app.core.database import Base


class Station(Base):
    """车站信息表"""

    __tablename__ = "station"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID（自增）")
    map_code = Column(String(50), comment="雪花ID")
    station_name = Column(String(50), comment="车站名称")
    station_code = Column(String(50), comment="车站编号")

    __table_args__ = (
        Index("idx_station_map_code", "map_code"),
        Index("idx_station_station_name", "station_name"),
        Index("idx_station_station_code", "station_code"),
        {"comment": "车站信息表"},
    )

    def __repr__(self) -> str:
        return (
            f"<Station(id={self.id}, station_name={self.station_name}, "
            f"station_code={self.station_code})>"
        )
