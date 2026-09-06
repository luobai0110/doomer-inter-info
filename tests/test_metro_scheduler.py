import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from app.core.scheduler import create_scheduler, sync_metro_info


class FakeSession:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class MetroSchedulerTests(unittest.TestCase):
    def test_scheduler_registers_daily_metro_sync(self) -> None:
        scheduler = create_scheduler()
        job = scheduler.get_job("sync-metro-info")

        self.assertIsNotNone(job)
        self.assertEqual("每天同步地铁数据", job.name)
        self.assertEqual("sync_metro_info", job.func.__name__)
        self.assertEqual("Asia/Shanghai", str(job.trigger.timezone))

        now = datetime(2026, 9, 6, 4, 59, tzinfo=ZoneInfo("Asia/Shanghai"))
        next_fire_time = job.trigger.get_next_fire_time(None, now)
        self.assertEqual(
            datetime(2026, 9, 6, 5, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
            next_fire_time,
        )

    def test_sync_metro_info_uses_and_closes_session(self) -> None:
        db = FakeSession()

        with (
            patch("app.core.scheduler.SessionLocal", return_value=db),
            patch("app.core.scheduler.get_metro_info", return_value=3) as metro_mock,
            patch("app.core.scheduler.logger.info") as logger_info,
        ):
            sync_metro_info()

        metro_mock.assert_called_once_with(db)
        logger_info.assert_called_once_with("定时同步地铁数据完成", inserted=3)
        self.assertTrue(db.closed)

    def test_sync_metro_info_closes_session_when_sync_fails(self) -> None:
        db = FakeSession()

        with (
            patch("app.core.scheduler.SessionLocal", return_value=db),
            patch(
                "app.core.scheduler.get_metro_info",
                side_effect=RuntimeError("network error"),
            ),
            patch("app.core.scheduler.logger.exception") as logger_exception,
        ):
            sync_metro_info()

        logger_exception.assert_called_once_with("定时同步地铁数据失败")
        self.assertTrue(db.closed)


if __name__ == "__main__":
    unittest.main()
