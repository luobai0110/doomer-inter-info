from collections.abc import Iterator
from pathlib import Path

import pandas as pd
import structlog
from sqlalchemy.dialects.postgresql import Insert, insert as pg_insert
from sqlalchemy.orm import Session

from app.model.region import Region
from app.schema.region import RegionRecord

DEFAULT_EXCEL_NAME = "xzqh2020-03.xlsx"
SHEET_NAME = "Sheet1"
EXCEL_COLUMNS = ["id", "省name", "省gb", "市name", "市gb", "县name", "县gb"]
FIELD_BY_COLUMN = {
    "id": "id",
    "省name": "province_name",
    "省gb": "province_gb",
    "市name": "city_name",
    "市gb": "city_gb",
    "县name": "county_name",
    "县gb": "county_gb",
}
CODE_COLUMNS = frozenset({"id", "省gb", "市gb", "县gb"})
logger = structlog.get_logger(__name__)


def get_data_dir() -> Path:
    """返回项目 data 目录（Excel 数据所在位置）。"""
    return Path(__file__).resolve().parents[2] / "data"


def _to_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _to_code(value: object) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return _to_text(value)


def _read_excel_columns(path: Path) -> pd.DataFrame:
    """读取行政区划 Excel，并校验当前导入需要的表头。"""
    df = pd.read_excel(path, sheet_name=SHEET_NAME, dtype=object, engine="openpyxl")
    df.columns = [str(column).strip() for column in df.columns]
    missing = [column for column in EXCEL_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Excel 缺少表头: {', '.join(missing)}")
    return df.loc[:, EXCEL_COLUMNS]


def _to_record(row: dict[str, object]) -> RegionRecord:
    """把一行中文表头数据转换为数据库记录。"""
    fields = {
        field: (_to_code if column in CODE_COLUMNS else _to_text)(row[column])
        for column, field in FIELD_BY_COLUMN.items()
    }
    fields["id"] = int(fields["id"])
    return RegionRecord(**fields)


def _upsert_statement(values: list[dict[str, str | int]]) -> Insert:
    """构建按 Excel id 更新已有行政区划的 PostgreSQL upsert 语句。"""
    stmt = pg_insert(Region).values(values)
    return stmt.on_conflict_do_update(
        index_elements=[Region.id],
        set_={
            "province_name": stmt.excluded.province_name,
            "province_gb": stmt.excluded.province_gb,
            "city_name": stmt.excluded.city_name,
            "city_gb": stmt.excluded.city_gb,
            "county_name": stmt.excluded.county_name,
            "county_gb": stmt.excluded.county_gb,
        },
    )


def iter_records(path: Path) -> Iterator[RegionRecord]:
    """用 pandas 读取 Excel 表头，逐行解析行政区划记录。"""
    df = _read_excel_columns(path)
    for row in df.to_dict("records"):
        yield _to_record(row)


def import_regions(db: Session, path: Path | None = None) -> int:
    """把 Excel 写入 regions 表；按 Excel id upsert，重复执行不会重复入库。"""
    source = path or get_data_dir() / DEFAULT_EXCEL_NAME
    records = list(iter_records(source))
    values = [record.model_dump(by_alias=False) for record in records]

    stmt = _upsert_statement(values)
    result = db.execute(stmt)
    db.commit()
    return result.rowcount or 0


def main() -> None:
    """命令行入口：读取默认 Excel 并写入数据库。"""
    from app.core.logging import configure_logging

    from app.core.database import Base, SessionLocal, engine

    configure_logging()
    Base.metadata.create_all(bind=engine)
    source = get_data_dir() / DEFAULT_EXCEL_NAME
    with SessionLocal() as db:
        count = import_regions(db, source)
    logger.info("已写入行政区划记录", count=count, source=str(source))


if __name__ == "__main__":
    main()
