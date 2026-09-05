import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.model.area import Area
from app.service.deal_lon import get_position


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.status_code = 200
        self.text = '{"status": "1", "geocodes": [{"location": "116.397428,39.90923"}]}'

    def json(self) -> dict[str, object]:
        return self.payload


class FakeQueryResult:
    def __init__(self, area: Area | None) -> None:
        self.area = area

    def first(self) -> Area | None:
        return self.area

    def __iter__(self):
        if isinstance(self.area, list):
            return iter(self.area)
        return iter([self.area])


class FakeSession:
    def __init__(self, area: Area) -> None:
        self.area = area
        self.committed = False
        self.refreshed: list[Area] = []

    def scalars(self, _statement: object):
        return [self.area]

    def scalar(self, _statement: object) -> Area | None:
        return self.area

    def commit(self) -> None:
        self.committed = True

    def refresh(self, area: Area) -> None:
        self.refreshed.append(area)


class GetPositionTests(unittest.TestCase):
    def test_geocodes_area_and_updates_database(self) -> None:
        area = Area()
        area.id = 12
        area.area_code = "110000000000"
        area.area_name = "Test Area"
        area.full_name = "中国Test Area"
        db = FakeSession(area)
        request = {
            "url": "",
            "params": {},
        }

        def get_with_retry(**kwargs: object) -> FakeResponse:
            request.update(kwargs)  # type: ignore[arg-type]
            return FakeResponse(
                {"status": "1", "geocodes": [{"location": "116.397428,39.90923"}]}
            )

        settings = SimpleNamespace(amap_key="test-key")
        with (
            patch("app.service.deal_lon.get_with_retry", side_effect=get_with_retry),
            patch("app.service.deal_lon.settings", settings),
        ):
            updated_count = get_position(db)

        self.assertEqual(
            {"address": "中国Test Area", "city": "110000", "key": "test-key"},
            request["params"],
        )
        self.assertEqual(116.397428, area.longitude)
        self.assertEqual(39.90923, area.latitude)
        self.assertEqual(1, updated_count)
        self.assertTrue(db.committed)
        self.assertEqual([area], db.refreshed)


if __name__ == "__main__":
    unittest.main()
