from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.http import get_with_retry
from app.core.logging import get_logger
from app.service.area import get_all_area_names, get_area_by_name, update_area_by_id

base_url = "https://restapi.amap.com/v3/geocode/geo"
REQUEST_TIMEOUT = 30
logger = get_logger(__name__)


def get_position(db: Session) -> None:
    logger.info("开始同步经纬度")
    areas = get_all_area_names(db)

    if not settings.amap_key:
        logger.warning("高德服务密钥未配置")
        return

    for area in areas:
        logger.info("请求高德地理编码", address=area.area_name)
        logger.info("请求信息", base_url=base_url, area_name=area)
        resp = get_with_retry(
            url=base_url,
            params={"address": area, "key": settings.amap_key},
            timeout=REQUEST_TIMEOUT,
        )

        logger.info("响应信息", resp=resp.text)
        if resp.status_code != 200:
            logger.warning(
                "高德地理编码请求失败",
                address=area.full_name,
                city=area.area_code[:6],
                status_code=resp.status_code,
            )
            continue
        logger.info("响应信息", resp=resp.text)
        data = resp.json()
        geocodes = data.get("geocodes") or []
        if not geocodes:
            logger.warning(
                "高德地理编码结果为空",
                address=area,
                infocode=data.get("infocode"),
            )
            continue

        location = str(geocodes[0].get("location", ""))
        coordinates = location.split(",")
        if len(coordinates) != 2:
            logger.warning(
                "高德地理编码坐标格式错误",
                address=area,
                location=location,
            )
            continue

        try:
            longitude = float(coordinates[0])
            latitude = float(coordinates[1])
        except ValueError:
            logger.warning(
                "高德地理编码坐标解析失败",
                address=area,
                location=location,
            )
            continue

        area = get_area_by_name(area, db)
        if area is None:
            logger.warning("未找到区划记录", address=area)
            continue

        area.longitude = longitude
        area.latitude = latitude
        update_area_by_id(area, db)
        logger.debug("区划坐标已更新", address=area)

    logger.info("completed")
