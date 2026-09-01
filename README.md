# inter-info

FastAPI + SQLAlchemy (PostgreSQL) 项目。

## 环境准备

```bash
uv sync
cp .env.example .env   # 按需修改数据库连接信息
```

## 数据库配置

- 连接信息全部来自 `.env`（见 [.env.example](.env.example)），由
  `app/core/config.py` 通过 `pydantic-settings` 加载，并生成 SQLAlchemy 连接串
  （`postgresql+psycopg2://...`）。
- `app/core/database.py` 提供：
  - `engine`：连接池引擎（`pool_size` / `max_overflow` / `echo` 均取自已 `.env`）；
  - `SessionLocal`：会话工厂；
  - `Base`：所有 ORM 模型的基类；
  - `get_db`：FastAPI 依赖，请求级会话，自动关闭。
- `app/main.py` 在启动时执行 `Base.metadata.create_all(bind=engine)` 建表
  （目前无模型，为空操作），退出时释放连接池。

在路由中使用数据库：

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import get_db

@app.get("/example")
def example(db: Session = Depends(get_db)):
    ...
```

## 运行

```bash
uv run fastapi dev        # 或: uv run uvicorn app.main:app --reload
```

健康检查：`GET /health/db`（执行 `SELECT 1` 验证数据库连通性）。