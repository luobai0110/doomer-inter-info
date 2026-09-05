import unittest
from unittest.mock import patch

import requests

from app.service import area as area_service
from app.service.area import sync_area_data


class FakeTransaction:
    def __init__(self, db: "FakeSession") -> None:
        self.db = db

    def __enter__(self) -> "FakeTransaction":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        if exc_type is None:
            self.db.committed += 1
        else:
            self.db.rolled_back += 1
        return False


class FakeSession:
    def __init__(self) -> None:
        self.added: list[area_service.Area] = []
        self.transaction_count = 0
        self.committed = 0
        self.rolled_back = 0
        self.flush_count = 0

    def begin(self) -> FakeTransaction:
        self.transaction_count += 1
        return FakeTransaction(self)

    def scalar(self, _statement: object) -> None:
        return None

    def add(self, area: area_service.Area) -> None:
        self.added.append(area)

    def flush(self) -> None:
        self.flush_count += 1


def national_root() -> dict[str, object]:
    return {
        "code": "00",
        "name": None,
        "level": 0,
        "children": [
            province_node("110000000000", "北京市"),
            province_node("120000000000", "天津市"),
        ],
    }


def province_node(code: str, name: str) -> dict[str, object]:
    return {
        "code": code,
        "name": name,
        "level": 1,
        "children": [
            {
                "code": f"{code[:2]}0100000000",
                "name": f"{name}城区",
                "level": 2,
                "children": [
                    {
                        "code": f"{code[:2]}0101000000",
                        "name": f"{name}城区中心街道",
                        "level": 3,
                    }
                ],
            }
        ],
    }


class SyncAreaDataTests(unittest.TestCase):
    def test_one_transaction_per_top_level_area(self) -> None:
        db = FakeSession()
        with (
            patch.object(area_service, "_fetch_top", return_value=national_root()),
            patch.object(
                area_service,
                "get_unique_code",
                side_effect=lambda: 900000000000 + len(db.added),
            ),
            patch.object(
                area_service,
                "_fetch_children",
                side_effect=AssertionError("不应请求已有 children"),
            ),
        ):
            inserted = sync_area_data(db)

        self.assertEqual(6, inserted)
        self.assertEqual(2, db.transaction_count)
        self.assertEqual(2, db.committed)
        self.assertEqual(0, db.rolled_back)
        self.assertEqual(
            [
                "110000000000",
                "110100000000",
                "110101000000",
                "120000000000",
                "120100000000",
                "120101000000",
            ],
            [area.area_code for area in db.added],
        )

    def test_failed_children_request_skips_that_code(self) -> None:
        root = national_root()
        province = root["children"][0]
        province["children"] = [
            {
                "code": "110100000000",
                "name": "北京市城区",
                "level": 2,
                "children": [
                    {
                        "code": "110101000000",
                        "name": "东城区",
                        "level": 3,
                    }
                ],
            },
            {
                "code": "110200000000",
                "name": "北京市失败市",
                "level": 2,
            },
        ]
        db = FakeSession()

        def fetch_children(area_code: str) -> list[dict[str, object]]:
            if area_code == "110100000000":
                return []
            raise requests.ConnectionError("下游请求失败")

        with (
            patch.object(area_service, "_fetch_top", return_value=root),
            patch.object(
                area_service,
                "get_unique_code",
                side_effect=lambda: 900000000000 + len(db.added),
            ),
            patch.object(area_service, "_fetch_children", side_effect=fetch_children),
        ):
            inserted = sync_area_data(db)

        self.assertEqual(6, inserted)
        self.assertEqual(2, db.transaction_count)
        self.assertEqual(2, db.committed)
        self.assertNotIn(
            "110200000000",
            [area.area_code for area in db.added],
        )

    def test_stop_at_county_level(self) -> None:
        db = FakeSession()
        with (
            patch.object(area_service, "_fetch_top", return_value=national_root()),
            patch.object(
                area_service,
                "get_unique_code",
                side_effect=lambda: 900000000000 + len(db.added),
            ),
            patch.object(
                area_service,
                "_fetch_children",
                side_effect=AssertionError("不应递归到街道层级"),
            ),
        ):
            inserted = sync_area_data(db)

        self.assertEqual(6, inserted)
        self.assertTrue(
            all(area.level <= 3 for area in db.added),
        )

    def test_failed_snowflake_request_skips_province(self) -> None:
        root = national_root()
        db = FakeSession()

        code_calls = {"count": 0}

        def get_unique_code() -> int:
            code_calls["count"] += 1
            if code_calls["count"] == 1:
                raise requests.ConnectionError("雪花 ID 服务失败")
            return 900000000000 + len(db.added)

        with (
            patch.object(area_service, "_fetch_top", return_value=root),
            patch.object(
                area_service,
                "get_unique_code",
                side_effect=get_unique_code,
            ),
            patch.object(
                area_service,
                "_fetch_children",
                side_effect=AssertionError("不应请求已有 children"),
            ),
        ):
            inserted = sync_area_data(db)

        self.assertEqual(3, inserted)
        self.assertEqual(2, db.transaction_count)
        self.assertEqual(2, db.committed)
        self.assertEqual(
            ["120000000000", "120100000000", "120101000000"],
            [area.area_code for area in db.added],
        )


if __name__ == "__main__":
    unittest.main()
