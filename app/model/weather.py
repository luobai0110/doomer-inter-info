from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import BIGINT, JSONB
from datetime import datetime

from app.core.database import Base


class Weather(Base):
    __tablename__ = "weather"

    id = Column(BIGINT, primary_key=True)
    code = Column(BIGINT, unique=True, nullable=False)
    area_code = Column(String(50), nullable=False)
    area_name = Column(String(100))
    data_date = Column(DateTime, nullable=False)
    data_type = Column(String(20), default='HISTORY')
    source = Column(String(100))
    raw_data = Column(JSONB)
    cleand_data = Column(JSONB)
    status = Column(String(20), default='PENDING')
    clean_version = Column(String(20))
    quality_score = Column(Integer)
    has_error = Column(Boolean, default=False)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expired_at = Column(DateTime)

    __table_args__ = (
        CheckConstraint('quality_score >= 0 AND quality_score <= 100'),
    )
