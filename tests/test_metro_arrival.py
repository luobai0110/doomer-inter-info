import unittest
from datetime import time
from unittest.mock import patch

from app.model.metro import MetroArrivalRecord
from app.schema.metro import MetroArrivalRecordCreate
from app.service.metro_arrival import create_metro_arrival_records


class FakeSession:
    def __init__(self) -> None:
        self.add_all_calls: list[list[MetroArrivalRecord]] = []
        self.commit_count = 0

    def add_all(self, records: list[MetroArrivalRecord]) -> None:
        self.add_all_calls.append(list(records))

    def commit(self) -> None:
        self.commit_count += 1

    def refresh(self, _record: MetroArrivalRecord) -> None:
        pass


def build_record(order_no: int) -> MetroArrivalRecordCreate:
    return MetroArrivalRecordCreate.model_validate(
        {
            "line_name": "line-1",
            "line_code": "1",
            "direction": "up",
            "direction_code": "UP",
            "station_name": "station-a",
            "station_code": "A",
            "order_no": order_no,
            "arrvie_time": "12:00",
            "value_end_dttm": "2026-09-06",
        }
    )


class MetroArrivalRecordCreateTests(unittest.TestCase):
    def test_arrvie_time_24_hour_is_normalized_to_midnight(self) -> None:
        record = MetroArrivalRecordCreate.model_validate(
            {
                "line_name": "line-1",
                "line_code": "1",
                "direction": "up",
                "direction_code": "UP",
                "station_name": "station-a",
                "station_code": "A",
                "order_no": 1,
                "arrvie_time": "24:00",
                "value_end_dttm": "2026-09-06",
            }
        )

        self.assertEqual(time(0, 0), record.arrvie_time)

    def test_batch_insert_requests_snowflake_codes_in_chunks_of_512(self) -> None:
        db = FakeSession()
        data_list = [build_record(order_no) for order_no in range(600)]
        requested_counts: list[int] = []

        def fake_get_unique_codes(count: int) -> list[int]:
            requested_counts.append(count)
            return list(range(count))

        with patch(
            "app.service.metro_arrival.get_unique_codes",
            side_effect=fake_get_unique_codes,
        ):
            created = create_metro_arrival_records(db, data_list)

        self.assertEqual([512, 88], requested_counts)
        self.assertEqual([512, 88], [len(call) for call in db.add_all_calls])
        self.assertEqual(2, db.commit_count)
        self.assertEqual(600, len(created))
        self.assertEqual(600, sum(len(call) for call in db.add_all_calls))
        self.assertTrue(all(record.record_code for record in created))


if __name__ == "__main__":
    unittest.main()
