from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.http import RateLimiter, get_with_retry
from app.core.logging import get_logger
from app.service.area import get_all_area_names

base_url = "https://restapi.amap.com/v3/geocode/geo"
REQUEST_TIMEOUT = 30
AMAP_REQUESTS_PER_SECOND = 3
logger = get_logger(__name__)
_amap_rate_limiter = RateLimiter(AMAP_REQUESTS_PER_SECOND)


def get_position(db: Session) -> int:
    logger.info("开始同步经纬度")
    areas = get_all_area_names(db)
    updated_count = 0

    if not settings.amap_key:
        logger.warning("高德服务密钥未配置")
        return updated_count

    for area in areas:
        logger.info("请求高德地理编码", address=area.area_name)
        logger.info("请求信息", base_url=base_url, area_name=area.area_name)
        resp = get_with_retry(
            url=base_url,
            params={"address": area.full_name, "key": settings.amap_key, "city": area.area_code[:6]},
            timeout=REQUEST_TIMEOUT,
            rate_limiter=_amap_rate_limiter,
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
                code=area.code,
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

        area.longitude = longitude
        area.latitude = latitude
        db.commit()
        db.refresh(area)
        updated_count += 1
        logger.debug("区划坐标已更新", id=area.id, address=area.area_name)

    logger.info("经纬度同步完成", updated_count=updated_count)
    return updated_count
