import unittest
from datetime import time

from app.schema.metro import MetroArrivalRecordCreate


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


if __name__ == "__main__":
    unittest.main()
