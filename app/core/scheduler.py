from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.service.metro import get_metro_info

logger = get_logger(__name__)

TIMEZONE = ZoneInfo("Asia/Shanghai")


def sync_metro_info() -> None:
    """定时任务入口：使用独立数据库会话同步地铁到站数据。"""
    db = SessionLocal()
    try:
        inserted = get_metro_info(db)
        logger.info("定时同步地铁数据完成", inserted=inserted)
    except Exception:
        logger.exception("定时同步地铁数据失败")
    finally:
        db.close()


def create_scheduler() -> BackgroundScheduler:
    """创建应用内定时调度器。"""
    scheduler = BackgroundScheduler(timezone=TIMEZONE)
    scheduler.add_job(
        sync_metro_info,
        trigger=CronTrigger.from_crontab("0 5 * * *", timezone=TIMEZONE),
        id="sync-metro-info",
        name="每天同步地铁数据",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    return scheduler
