import httpx
import pytest
from fastapi.testclient import TestClient

from api.main import app
from worker.worker import check

# No "with" block, so the app's startup (opening the DB pool) does not run.
client = TestClient(app)

VALID_BODY = {"name": "Example", "url": "https://example.com"}


# ---------- API tests ----------

def test_create_monitor_without_key_returns_401():
    r = client.post("/monitors", json=VALID_BODY)
    assert r.status_code == 401


def test_create_monitor_with_wrong_key_returns_401():
    r = client.post("/monitors", json=VALID_BODY, headers={"X-API-Key": "wrong"})
    assert r.status_code == 401


def test_invalid_url_returns_422():
    # Correct key, bad URL: the key is accepted, then validation rejects the body.
    r = client.post(
        "/monitors",
        json={"name": "Bad", "url": "not-a-url"},
        headers={"X-API-Key": "test-key"},
    )
    assert r.status_code == 422


# ---------- Worker tests (status calculation) ----------

class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code


class FakeClient:
    """Stands in for httpx.Client so no real network call happens."""
    def __init__(self, status_code=None, error=None):
        self.status_code = status_code
        self.error = error

    def get(self, url, **kwargs):
        if self.error:
            raise self.error
        return FakeResponse(self.status_code)


@pytest.mark.parametrize("code, expected_ok", [
    (200, True),
    (399, True),    # below 400 counts as up
    (400, False),   # 400 and above counts as down
    (404, False),
    (500, False),
])
def test_status_code_decides_up_or_down(code, expected_ok):
    status, latency_ms, ok = check(FakeClient(status_code=code), "https://x.test")
    assert status == code
    assert ok is expected_ok
    assert latency_ms >= 0


def test_network_error_marks_site_down():
    client_with_error = FakeClient(error=httpx.ConnectError("boom"))
    status, latency_ms, ok = check(client_with_error, "https://x.test")
    assert status is None
    assert ok is False
