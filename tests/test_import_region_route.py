import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.database import get_db
from app.main import app


class FakeSession:
    closed = False

    def close(self) -> None:
        self.closed = True


class ImportRegionRouteTests(unittest.TestCase):
    def test_import_region_uses_default_excel_and_returns_count(self) -> None:
        db = FakeSession()
        app.dependency_overrides[get_db] = lambda: db
        client = TestClient(app)

        try:
            with patch("app.main.import_regions", return_value=3454) as import_mock:
                response = client.post("/data/region/import")
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(200, response.status_code)
        self.assertEqual(200, response.json()["code"])
        self.assertEqual({"processed": 3454}, response.json()["data"])
        import_mock.assert_called_once_with(db=db)


if __name__ == "__main__":
    unittest.main()
