from sqlalchemy import (
    BigInteger, Column, Date, DateTime, Integer, String, Time
)
from sqlalchemy.sql import func

from app.core.database import Base


class MetroArrivalRecord(Base):
    """地铁到站记录表 - 匹配已有表结构"""
    __tablename__ = 'metro_arrival_records'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    record_code = Column(String(50), nullable=False, comment="雪花id")
    line_name = Column(String(50), nullable=False, comment='线路名称')
    line_code = Column(String(10), nullable=False, comment='线路编码')
    direction = Column(String(50), nullable=False, comment='方向描述')
    direction_code = Column(String(10), nullable=False, comment='方向编码')
    station_name = Column(String(100), nullable=False, comment='站点名称')
    station_code = Column(String(20), nullable=False, comment='站点编码')
    order_no = Column(Integer, nullable=False, comment='站点序号')
    arrvie_time = Column(Time, nullable=False, comment='到站时间')
    train_seq_no = Column(String(50), comment='列车序列号')
    value_end_dttm = Column(Date, nullable=False, comment='数据所属日期')
    created_at = Column(DateTime, server_default=func.now(), comment='记录创建时间')

    def __repr__(self):
        return f"<MetroArrivalRecord(id={self.id}, line={self.line_name}, station={self.station_name}, date={self.value_end_dttm})>"
