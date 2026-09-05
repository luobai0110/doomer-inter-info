from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

# 引入模型以注册到 Base.metadata，供启动时自动建表
from app import model  # noqa: F401
from app.core.config import settings
from app.core.database import Base, engine, get_db
from app.core.logging import configure_logging
from app.core.response import ApiResponse, ok
from app.service.area import sync_area_data, update_area_by_id
from app.service.deal_lon import get_position
from app.service.import_region import import_regions
from app.service.weather import get_weather_data

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时建表，关闭时释放数据库连接池。"""
    # 目前无模型时为空操作；后续注册模型后可自动创建表。
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()


app = FastAPI(title="inter-info", lifespan=lifespan)


@app.get("/", response_model=ApiResponse[dict[str, str]])
def root() -> ApiResponse[dict[str, str]]:
    return ok({"message": "Hello from inter-info!"})


@app.get("/data/weather", response_model=ApiResponse[dict[str, str]])
def get_weather(db: Session = Depends(get_db)) -> ApiResponse[dict[str, str]]:
    """拉取并保存最新天气数据。"""
    get_weather_data(db=db)
    return ok({"message": "SUCCESS"})


@app.post("/data/area/sync", response_model=ApiResponse[dict[str, int]])
def sync_area(db: Session = Depends(get_db)) -> ApiResponse[dict[str, int]]:
    """拉取省市区街道数据并返回新增数量。"""
    inserted = sync_area_data(db=db)
    return ok({"inserted": inserted})


@app.post("/data/region/import", response_model=ApiResponse[dict[str, int]])
def import_region(db: Session = Depends(get_db)) -> ApiResponse[dict[str, int]]:
    """导入默认行政区划 Excel，返回 upsert 影响的记录数量。"""
    processed = import_regions(db=db)
    return ok({"processed": processed})


@app.get("/health/db", response_model=ApiResponse[dict[str, str]])
def db_health(db: Session = Depends(get_db)) -> ApiResponse[dict[str, str]]:
    """数据库连通性检查。"""
    db.execute(text("SELECT 1"))
    return ok({"status": "ok"})

@app.get("/data/sync/position", response_model=ApiResponse[dict[str, str]])
def sync_position(db:Session = Depends(get_db)) -> ApiResponse[dict[str, str]]:
    get_position(db)
    return ok({"status": "ok"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_config=None,
        log_level=settings.log_level.lower(),
    )
