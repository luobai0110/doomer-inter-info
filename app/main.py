from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import Base, engine, get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时建表，关闭时释放数据库连接池。"""
    # 目前无模型时为空操作；后续注册模型后可自动创建表。
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()


app = FastAPI(title="inter-info", lifespan=lifespan)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Hello from inter-info!"}


@app.get("/health/db")
def db_health(db: Session = Depends(get_db)) -> dict[str, str]:
    """数据库连通性检查。"""
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)