import unittest

from app.dao.station import (
    create_station,
    delete_station,
    get_station,
    list_stations,
    update_station,
)
from app.model.station import Station
from app.schema.station import StationCreate, StationUpdate


class FakeScalarResult:
    def __init__(self, items: list[Station]) -> None:
        self.items = items

    def __iter__(self):
        return iter(self.items)


class FakeSession:
    def __init__(self) -> None:
        self.stations: dict[int, Station] = {}
        self.next_id = 1

    def get(self, _model: type[Station], station_id: int) -> Station | None:
        return self.stations.get(station_id)

    def scalars(self, _statement: object) -> FakeScalarResult:
        return FakeScalarResult(list(self.stations.values()))

    def add(self, station: Station) -> None:
        station.id = self.next_id
        self.next_id += 1
        self.stations[station.id] = station

    def commit(self) -> None:
        pass

    def refresh(self, _station: Station) -> None:
        pass

    def delete(self, station: Station) -> None:
        self.stations.pop(station.id, None)


class StationDaoTests(unittest.TestCase):
    def test_create_get_update_delete(self) -> None:
        db = FakeSession()

        created = create_station(
            db,
            StationCreate(
                map_code="1001",
                station_name="西湖文化广场",
                station_code="XHWHGC",
            ),
        )
        self.assertEqual("1001", created.map_code)

        found = get_station(db, created.id)
        self.assertIs(found, created)

        updated = update_station(
            db,
            created.id,
            StationUpdate(station_name="西湖文化广场站"),
        )
        self.assertIsNotNone(updated)
        self.assertEqual("西湖文化广场站", updated.station_name)
        self.assertEqual("1001", updated.map_code)

        self.assertTrue(delete_station(db, created.id))
        self.assertFalse(delete_station(db, created.id))
        self.assertIsNone(get_station(db, created.id))

    def test_list_stations_returns_all(self) -> None:
        db = FakeSession()
        create_station(db, StationCreate(station_name="站A", station_code="A"))
        create_station(db, StationCreate(station_name="站B", station_code="B"))

        stations = list_stations(db)

        self.assertEqual(2, len(stations))
        self.assertEqual(["站A", "站B"], [item.station_name for item in stations])


if __name__ == "__main__":
    unittest.main()
