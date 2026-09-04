# inter-info

FastAPI + SQLAlchemy (PostgreSQL) 项目，提供数据库健康检查、天气数据拉取、行政区划 Excel 导入和省市区街道行政区划同步能力。

## 环境准备

```bash
uv sync
cp .env.example .env
```

复制 `.env` 后按实际环境修改配置。`.env` 不提交到仓库。

## 配置

配置通过 `pydantic-settings` 从 `.env` 加载，定义见 [app/core/config.py](app/core/config.py)。

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `DB_HOST` | `127.0.0.1` | PostgreSQL 地址 |
| `DB_PORT` | `5432` | PostgreSQL 端口 |
| `DB_USER` / `DB_PASSWORD` | `postgres` | 数据库账号信息 |
| `DB_NAME` | `inter` | 数据库名 |
| `DB_POOL_SIZE` | `10` | SQLAlchemy 常规连接池大小 |
| `DB_MAX_OVERFLOW` | `20` | 连接池允许的额外连接数 |
| `DB_ECHO` | `false` | 是否输出 SQLAlchemy SQL 日志 |
| `SNOWFLAKE_ID_URL` | `http://192.168.1.3:8088` | 雪花 ID 服务地址 |
| `LOG_LEVEL` | `INFO` | 日志级别，支持标准日志级别，如 `DEBUG`、`INFO`、`WARNING` |

数据库连接串由 `DB_*` 配置生成，格式为 `postgresql+psycopg2://...`。

## 运行

```bash
uv run fastapi dev
# 或
uv run uvicorn app.main:app --reload
```

API 文档：

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

启动时会通过 `Base.metadata.create_all` 创建缺失表，退出时释放数据库连接池。

## 接口

通用响应结构包含 `code`、`message`、`data` 和 `timestamp`。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/` | 服务根接口 |
| `GET` | `/health/db` | 执行 `SELECT 1`，检查数据库连通性 |
| `GET` | `/data/weather` | 从 Open-Meteo 拉取天气数据并保存 |
| `POST` | `/data/area/sync` | 同步省、市、区县、街道行政区划 |

区划同步返回示例：

```json
{
  "code": 200,
  "message": "SUCCESS",
  "data": {
    "inserted": 0
  },
  "timestamp": 1756992000000
}
```

`inserted` 只统计新增记录。同步时按 `area_code + level` 查找已有区划：

- 不存在时插入新记录；
- 已存在时原地更新区划字段，不生成新的雪花 ID；
- 更新记录不计入 `inserted`。

`area` 表保存 `area_code`、`area_name`、`level`、省/市/区/街道的 code 和 name，以及按
`省 + 市 + 区 + 街道` 顺序拼接的 `full_name`。

> 注意：`create_all` 只创建缺失表，不会给已存在的 `area` 表自动补新列。历史数据库需要先手工执行迁移或
> `ALTER TABLE` 补齐 `street_code`、`street_name` 等字段。

## 行政区划 Excel 导入

`data/xzqh2020-03.xlsx` 的表头为：

```text
id 省name 省gb 市name 市gb 县name 县gb
```

数据对应 [app/model/region.py](app/model/region.py) 中的 `regions` 表，Pydantic 表示为
[app/schema/region.py](app/schema/region.py) 的 `RegionRecord`。

导入命令：

```bash
uv run python -m app.service.import_region
```

脚本会先建表，再按 Excel 中的 `id` 执行 PostgreSQL upsert，重复执行不会产生重复数据。

## 日志

日志框架基于 [structlog](https://www.structlog.org/)，应用日志和 Uvicorn 运行日志统一输出为单行 JSON。
日志级别由 `LOG_LEVEL` 控制。

输出示例：

```json
{"event": "HTTP 请求详情", "method": "GET", "url": "https://dmfw.mca.gov.cn/9095/xzqh/getList", "logger": "app.service.area", "level": "info", "timestamp": "2026-09-04T08:00:00.000000Z"}
```

日志输出到 stdout，便于容器或日志采集器直接解析。
