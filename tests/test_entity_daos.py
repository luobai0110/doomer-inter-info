import unittest
from datetime import datetime
from unittest.mock import patch

from app.dao.area import (
    create_area,
    delete_area,
    get_area,
    list_areas,
    update_area,
)
from app.dao.metro_arrival import (
    create_metro_arrival_record,
    delete_metro_arrival_record,
    get_metro_arrival_record,
    list_metro_arrival_records,
    update_metro_arrival_record,
)
from app.dao.region import (
    create_region,
    delete_region,
    get_region,
    list_regions,
    update_region,
)
from app.dao.weather import (
    create_weather,
    delete_weather,
    get_weather,
    list_weathers,
    update_weather,
)
from app.schema.area import AreaCreate, AreaUpdate
from app.schema.metro import MetroArrivalRecordCreate, MetroArrivalRecordUpdate
from app.schema.region import RegionCreate, RegionUpdate
from app.schema.weather import WeatherCreate, WeatherUpdate


class FakeScalarResult:
    def __init__(self, items: list[object]) -> None:
        self.items = items

    def __iter__(self):
        return iter(self.items)


class FakeSession:
    def __init__(self) -> None:
        self.rows: dict[int, object] = {}
        self.next_id = 1

    def get(self, _model: object, primary_key: int) -> object | None:
        return self.rows.get(primary_key)

    def scalars(self, _statement: object) -> FakeScalarResult:
        return FakeScalarResult(list(self.rows.values()))

    def add(self, obj: object) -> None:
        if getattr(obj, "id", None) is None:
            obj.id = self.next_id  # type: ignore[attr-defined]
            self.next_id += 1
        self.rows[obj.id] = obj  # type: ignore[index]

    def commit(self) -> None:
        pass

    def refresh(self, _obj: object) -> None:
        pass

    def delete(self, obj: object) -> None:
        self.rows.pop(obj.id, None)  # type: ignore[attr-defined]


class AreaDaoTests(unittest.TestCase):
    def test_crud(self) -> None:
        db = FakeSession()
        area = create_area(
            db,
            AreaCreate(
                code=100001,
                area_code="110000000000",
                area_name="北京市",
                full_name="北京市",
            ),
        )
        self.assertEqual(100001, area.code)

        updated = update_area(db, area.id, AreaUpdate(area_name="北京市（更新）"))
        self.assertIsNotNone(updated)
        self.assertEqual("北京市（更新）", updated.area_name)

        self.assertIs(get_area(db, area.id), area)
        self.assertEqual(1, len(list_areas(db)))
        self.assertTrue(delete_area(db, area.id))
        self.assertFalse(delete_area(db, area.id))


class RegionDaoTests(unittest.TestCase):
    def test_crud(self) -> None:
        db = FakeSession()
        region = create_region(
            db,
            RegionCreate(
                id=42,
                province_name="浙江省",
                province_gb="33",
                city_name="杭州市",
                city_gb="3301",
                county_name="西湖区",
                county_gb="330106",
            ),
        )
        self.assertEqual("杭州市", region.city_name)

        updated = update_region(db, 42, RegionUpdate(city_name="杭州市（更新）"))
        self.assertIsNotNone(updated)
        self.assertEqual("杭州市（更新）", updated.city_name)

        self.assertIs(get_region(db, 42), region)
        self.assertEqual(1, len(list_regions(db)))
        self.assertTrue(delete_region(db, 42))
        self.assertFalse(delete_region(db, 42))


class WeatherDaoTests(unittest.TestCase):
    def test_crud(self) -> None:
        db = FakeSession()
        weather = create_weather(
            db,
            WeatherCreate(
                code=1,
                area_code="hz",
                area_name="杭州",
                data_date=datetime(2026, 9, 6, 12, 0, 0),
            ),
        )
        self.assertEqual("杭州", weather.area_name)

        updated = update_weather(db, weather.id, WeatherUpdate(status="DONE"))
        self.assertIsNotNone(updated)
        self.assertEqual("DONE", updated.status)

        self.assertIs(get_weather(db, weather.id), weather)
        self.assertEqual(1, len(list_weathers(db)))
        self.assertTrue(delete_weather(db, weather.id))
        self.assertFalse(delete_weather(db, weather.id))


class MetroArrivalDaoTests(unittest.TestCase):
    def test_crud(self) -> None:
        db = FakeSession()
        with patch(
            "app.dao.metro_arrival.get_unique_code",
            return_value=9001,
        ):
            record = create_metro_arrival_record(
                db,
                MetroArrivalRecordCreate(
                    line_name="1号线",
                    line_code="1",
                    direction="上行",
                    direction_code="UP",
                    station_name="龙翔桥",
                    station_code="LXQ",
                    order_no=3,
                    arrvie_time="12:00",
                    value_end_dttm="2026-09-06",
                ),
            )
        self.assertEqual("9001", record.record_code)

        updated = update_metro_arrival_record(
            db,
            record.id,
            MetroArrivalRecordUpdate(station_name="龙翔桥站"),
        )
        self.assertIsNotNone(updated)
        self.assertEqual("龙翔桥站", updated.station_name)

        self.assertIs(get_metro_arrival_record(db, record.id), record)
        self.assertEqual(1, len(list_metro_arrival_records(db)))
        self.assertTrue(delete_metro_arrival_record(db, record.id))
        self.assertFalse(delete_metro_arrival_record(db, record.id))


if __name__ == "__main__":
    unittest.main()
