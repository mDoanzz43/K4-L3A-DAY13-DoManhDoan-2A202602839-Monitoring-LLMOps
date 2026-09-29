import re

from fastapi.testclient import TestClient

from app.main import app


def test_valid_request_id_is_propagated() -> None:
    request_id = "req-1a2B3c4D"

    with TestClient(app) as client:
        response = client.get("/health", headers={"x-request-id": request_id})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == request_id
    assert float(response.headers["x-response-time-ms"]) >= 0


def test_invalid_request_id_is_replaced() -> None:
    with TestClient(app) as client:
        response = client.get("/health", headers={"x-request-id": "req-not-hex"})

    assert response.status_code == 200
    generated_id = response.headers["x-request-id"]
    assert generated_id != "req-not-hex"
    assert re.fullmatch(r"req-[0-9a-f]{8}", generated_id)
