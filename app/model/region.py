from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Region(Base):
    """行政区划表，一行对应 Excel 中一条省/市/县记录。"""

    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="Excel 中的 id")
    province_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="省name")
    province_gb: Mapped[str] = mapped_column(String(20), nullable=False, comment="省gb")
    city_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="市name")
    city_gb: Mapped[str] = mapped_column(String(20), nullable=False, comment="市gb")
    county_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="县name")
    county_gb: Mapped[str] = mapped_column(String(20), nullable=False, comment="县gb")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )

    __table_args__ = (
        Index("ix_regions_code_path", "province_gb", "city_gb", "county_gb"),
    )
