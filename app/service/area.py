import json
import logging
import requests
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.model.area import Area

base_url = "https://dmfw.mca.gov.cn/9095/xzqh/getList"
code_url = "http://192.168.1.3:8088"
proxy_api_url = "https://proxy.scdn.io/api/get_proxy.php"
proxy_api_params = {
    "protocol": "https",
    "count": 10,
    "country_code": "CN",
}

MAX_LEVEL = 4
REQUEST_TIMEOUT = 30
logger = logging.getLogger(__name__)
proxy_cache: list[str] = []


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
        "HTTP 请求详情: method=%s url=%s headers=%s body=%s",
        resp.request.method,
        resp.request.url,
        dict(resp.request.headers),
        request_body,
    )
    logger.info(
        "HTTP 响应详情: status_code=%s url=%s headers=%s body=%s",
        resp.status_code,
        resp.url,
        dict(resp.headers),
        response_body,
    )


def _load_proxies() -> list[str]:
    """获取 HTTPS 代理列表，失败时返回空列表并允许本地直连。"""
    global proxy_cache
    if proxy_cache:
        return proxy_cache

    try:
        resp = requests.get(
            url=proxy_api_url,
            params=proxy_api_params,
            timeout=REQUEST_TIMEOUT,
        )
        _log_http_detail(resp)
        resp.raise_for_status()
        payload = resp.json()
        proxies = payload["data"]["proxies"]
        proxy_cache = [str(item) for item in proxies if str(item).strip()]
        if not proxy_cache:
            logger.warning("代理服务返回空代理列表: %s", proxy_api_url)
    except (KeyError, TypeError, requests.RequestException, ValueError) as exc:
        logger.warning("获取代理列表失败，将回退本地直连: %s", exc)

    return proxy_cache


def _proxy_map(proxy: str) -> dict[str, str]:
    """将代理服务返回的 host:port 转换为 requests 代理配置。"""
    proxy_url = f"https://{proxy}"
    return {"http": proxy_url, "https": proxy_url}


def _request_with_proxy(url: str, params: dict[str, object]) -> requests.Response:
    """依次使用代理请求目标地址，全部失败后回退本地直连。"""
    proxies = _load_proxies()
    for proxy in proxies:
        try:
            resp = requests.get(
                url=url,
                params=params,
                proxies=_proxy_map(proxy),
                timeout=REQUEST_TIMEOUT,
            )
            _log_http_detail(resp)
            resp.raise_for_status()
            logger.debug("代理访问成功: proxy=%s url=%s", proxy, url)
            return resp
        except requests.RequestException as exc:
            logger.warning("代理访问失败: proxy=%s url=%s error=%s", proxy, url, exc)

    logger.warning("全部代理访问失败，回退本地直连: url=%s", url)
    resp = requests.get(url=url, params=params, timeout=REQUEST_TIMEOUT)
    _log_http_detail(resp)
    resp.raise_for_status()
    return resp


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
    resp = _request_with_proxy(base_url, {"maxLevel": 1})
    return resp.json()["data"]


def _fetch_children(area_code: str) -> list[dict[str, object]]:
    """请求指定区划的下一级 children。"""
    resp = _request_with_proxy(base_url, {"maxLevel": 1, "code": area_code})
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


def _build_area(node: dict[str, object], parent: dict[str, object]) -> Area:
    """将接口节点转换为 Area 记录。"""
    area = Area()
    area.code = get_unique_code()
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
    return area


def _save_node(db: Session, node: dict[str, object], parent: dict[str, object]) -> bool:
    """写入单个区划节点，已存在时跳过。"""
    area_code = str(node["code"])
    level = int(node["level"])
    exists = db.scalar(
        select(Area.id).where(
            Area.area_code == area_code,
            Area.level == level,
        )
    )
    if exists is not None:
        logger.debug(
            "区划已存在: level=%s area_code=%s",
            level,
            area_code,
        )
        return False
    area = create_area(db, _build_area(node, parent))
    logger.debug(
        "新增区划: level=%s area_code=%s area_name=%s full_name=%s",
        area.level,
        area.area_code,
        area.area_name,
        area.full_name,
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
    logger.info("行政区划同步完成: 新增 %d 条", inserted)
    return inserted


def get_province_code(db: Session = Depends(get_db)) -> int:
    """兼容旧入口：同步省市区街道数据。"""
    return sync_area_data(db)


def get_city_code(db: Session = Depends(get_db)) -> int:
    """兼容旧入口：同步省市区街道数据。"""
    return sync_area_data(db)
