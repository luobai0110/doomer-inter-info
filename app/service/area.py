import json
import requests
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.model.area import Area

base_url = "https://dmfw.mca.gov.cn/9095/xzqh/getList"
code_url = settings.snowflake_id_url

MAX_LEVEL = 4
REQUEST_TIMEOUT = 30
logger = get_logger(__name__)


def _log_http_detail(resp: requests.Response) -> None:
    """输出外部请求与响应的详细信息。"""
    request_body = resp.request.body
    if isinstance(request_body, bytes):
        request_body = request_body.decode("utf-8", errors="replace")

    try:
        response_body = json.dumps(resp.json(), ensure_ascii=False)
    except ValueError:
        response_body = resp.text

    logger.info(
        "HTTP 请求详情",
        method=resp.request.method,
        url=resp.request.url,
        headers=dict(resp.request.headers),
        body=request_body,
    )
    logger.info(
        "HTTP 响应详情",
        status_code=resp.status_code,
        url=resp.url,
        headers=dict(resp.headers),
        body=response_body,
    )


def create_area(db: Session, area: Area) -> Area:
    """创建区划记录。"""
    db.add(area)
    db.commit()
    db.refresh(area)
    return area


def get_code(db: Session, level: int) -> list[Area]:
    """按层级查询区划记录。"""
    return list(db.scalars(select(Area).where(Area.level == level)))


def get_unique_code() -> int:
    """从雪花 ID 服务获取唯一编码。"""
    resp = requests.get(url=code_url, timeout=REQUEST_TIMEOUT)
    _log_http_detail(resp)
    resp.raise_for_status()
    return resp.json()[0]


def _to_bigint(value) -> int | None:
    """将行政区划 code 转为 BIGINT 可存整数。"""
    if value is None or value == "":
        return None
    return int(value)


def _fetch_top() -> dict[str, object]:
    """请求省级数据，返回包含省级节点和市级 children 的 data。"""
    resp = requests.get(
        url=base_url,
        params={"maxLevel": 1},
        timeout=REQUEST_TIMEOUT,
    )
    _log_http_detail(resp)
    resp.raise_for_status()
    return resp.json()["data"]


def _fetch_children(area_code: str) -> list[dict[str, object]]:
    """请求指定区划的下一级 children。"""
    resp = requests.get(
        url=base_url,
        params={"maxLevel": 1, "code": area_code},
        timeout=REQUEST_TIMEOUT,
    )
    _log_http_detail(resp)
    resp.raise_for_status()
    data = resp.json()["data"]
    return data.get("children") or []


def _child_context(node: dict[str, object], parent: dict[str, object]) -> dict[str, object]:
    """根据当前节点生成下一级节点所需的省市区上下文。"""
    context = dict(parent)
    level = int(node["level"])
    if level == 1:
        context.update(
            {
                "province_code": _to_bigint(node["code"]),
                "province_name": node["name"],
                "city_code": None,
                "city_name": None,
                "district_code": None,
                "district_name": None,
            }
        )
    elif level == 2:
        context.update(
            {
                "city_code": _to_bigint(node["code"]),
                "city_name": node["name"],
                "district_code": None,
                "district_name": None,
            }
        )
    elif level == 3:
        context.update(
            {
                "district_code": _to_bigint(node["code"]),
                "district_name": node["name"],
            }
        )
    elif level == 4:
        context.update(
            {
                "street_code": _to_bigint(node["code"]),
                "street_name": node["name"],
            }
        )
    return context


def _full_name(node: dict[str, object], parent: dict[str, object]) -> str:
    """按省、市、区、街道顺序拼接完整区划名称。"""
    level = int(node["level"])
    current_name = str(node["name"])
    if level == 1:
        parent_keys: tuple[str, ...] = ()
    elif level == 2:
        parent_keys = ("province_name",)
    elif level == 3:
        parent_keys = ("province_name", "city_name")
    else:
        parent_keys = ("province_name", "city_name", "district_name")

    parts = [str(parent[key]) for key in parent_keys if parent.get(key)]
    parts.append(current_name)
    return "".join(parts)


def _apply_area_fields(
    area: Area,
    node: dict[str, object],
    parent: dict[str, object],
) -> None:
    """将接口节点区划字段写入 Area 记录。"""
    area.area_code = str(node["code"])
    area.area_name = str(node["name"])
    area.full_name = _full_name(node, parent)
    area.level = int(node["level"])
    area.province_code = (
        _to_bigint(node["code"]) if area.level == 1 else parent.get("province_code")
    )
    area.province_name = (
        str(node["name"]) if area.level == 1 else parent.get("province_name")
    )
    area.city_code = (
        _to_bigint(node["code"]) if area.level == 2 else parent.get("city_code")
    )
    area.city_name = (
        str(node["name"]) if area.level == 2 else parent.get("city_name")
    )
    area.district_code = (
        _to_bigint(node["code"]) if area.level == 3 else parent.get("district_code")
    )
    area.district_name = (
        str(node["name"]) if area.level == 3 else parent.get("district_name")
    )
    area.street_code = (
        _to_bigint(node["code"])
        if area.level == 4
        else parent.get("street_code")
    )
    area.street_name = (
        str(node["name"]) if area.level == 4 else parent.get("street_name")
    )


def _build_area(node: dict[str, object], parent: dict[str, object]) -> Area:
    """将接口节点转换为 Area 记录。"""
    area = Area()
    area.code = get_unique_code()
    _apply_area_fields(area, node, parent)
    return area


def _save_node(db: Session, node: dict[str, object], parent: dict[str, object]) -> bool:
    """保存单个区划节点；已存在时更新并返回 False。"""
    area_code = str(node["code"])
    level = int(node["level"])
    existing_area = db.scalar(
        select(Area).where(
            Area.area_code == area_code,
            Area.level == level,
        )
    )
    if existing_area is not None:
        _apply_area_fields(existing_area, node, parent)
        db.commit()
        db.refresh(existing_area)
        logger.debug(
            "更新区划",
            id=existing_area.id,
            level=level,
            area_code=area_code,
            full_name=existing_area.full_name,
        )
        return False
    area = create_area(db, _build_area(node, parent))
    logger.debug(
        "新增区划",
        level=area.level,
        area_code=area.area_code,
        area_name=area.area_name,
        full_name=area.full_name,
    )
    return True


def _sync_node(db: Session, node: dict[str, object], parent: dict[str, object]) -> int:
    """递归同步节点及其下级区划，返回新增数量。"""
    saved = 1 if _save_node(db, node, parent) else 0
    level = int(node["level"])
    if level >= MAX_LEVEL:
        return saved

    children = node.get("children") or []
    if not children:
        children = _fetch_children(str(node["code"]))

    child_parent = _child_context(node, parent)
    for child in children:
        if str(child.get("code")) == str(node["code"]):
            continue
        saved += _sync_node(db, child, child_parent)
    return saved


def sync_area_data(db: Session = Depends(get_db)) -> int:
    """拉取省、市、区县、街道四级行政区划并写入数据库，返回新增数量。"""
    logger.info("开始同步省市区街道行政区划数据")
    top = _fetch_top()
    inserted = _sync_node(db, top, {})
    logger.info("行政区划同步完成", inserted=inserted)
    return inserted


def get_province_code(db: Session = Depends(get_db)) -> int:
    """兼容旧入口：同步省市区街道数据。"""
    return sync_area_data(db)


def get_city_code(db: Session = Depends(get_db)) -> int:
    """兼容旧入口：同步省市区街道数据。"""
    return sync_area_data(db)
