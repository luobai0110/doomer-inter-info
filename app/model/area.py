from sqlalchemy import BIGINT, Column, String, DOUBLE, SmallInteger

from app.core.database import Base


class Area(Base):
    __tablename__ = "area"

    # 主键
    id = Column(BIGINT, primary_key=True)
    # code 雪花id
    code = Column(BIGINT, unique=True, nullable=False)
    # 行政规划code
    area_code = Column(String(50), nullable=False)
    # 区划名称
    area_name = Column(String(100))
    # 经度
    longitude = Column(DOUBLE(2))
    # 纬度
    latitude = Column(DOUBLE(2))

    # ========== 新增省市区字段 ==========
    # 省
    province_code = Column(BIGINT, index=True)      # 省code
    province_name = Column(String(50))              # 省名称

    # 市
    city_code = Column(BIGINT, index=True)          # 市code
    city_name = Column(String(50))                  # 市名称

    # 区/县
    district_code = Column(BIGINT, index=True)      # 区code
    district_name = Column(String(50))              # 区名称

    # 层级标识（可选，便于区分）
    level = Column(SmallInteger, comment="1-省 2-市 3-区/县 4-街道/乡镇")

    # 完整名称（可选，便于展示）
    full_name = Column(String(200), comment="完整行政区划名称")
