import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.model.area import Area
from app.service.deal_lon import get_position


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.status_code = 200

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
        self.scalars_count = 0

    def scalars(self, _statement: object):
        self.scalars_count += 1
        if self.scalars_count == 1:
            return [self.area.area_name]
        return FakeQueryResult(self.area)

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
        area.area_name = "Test Area"
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
            get_position(db)

        self.assertEqual(
            {"address": "Test Area", "key": "test-key"},
            request["params"],
        )
        self.assertEqual(116.397428, area.longitude)
        self.assertEqual(39.90923, area.latitude)
        self.assertTrue(db.committed)
        self.assertEqual([area], db.refreshed)


if __name__ == "__main__":
    unittest.main()
