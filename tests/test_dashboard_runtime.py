from fastapi.testclient import TestClient

from app.dashboard import dashboard_summary
from app.main import app


def test_dashboard_summary_calculates_required_signals() -> None:
    summary = dashboard_summary(
        [
            {"event": "request_received"},
            {
                "event": "response_sent",
                "latency_ms": 400,
                "ttft_ms": 50,
                "cost_usd": 0.002,
                "tokens_in": 20,
                "tokens_out": 80,
                "quality_score": 0.9,
                "tool_name": "retrieval",
                "tool_success": True,
            },
        ]
    )
    assert summary["latency_p95"] == 400
    assert summary["retrieval_success_pct"] == 100
    assert summary["tokens_in"] == 20
    assert summary["quality_avg"] == 0.9


def test_runtime_dashboard_has_exactly_six_panels() -> None:
    with TestClient(app) as client:
        response = client.get("/dashboard")

    assert response.status_code == 200
    assert response.text.count('data-panel="') == 6
    for panel_id in ("latency", "traffic", "errors", "cost", "tokens", "quality"):
        assert f'data-panel="{panel_id}"' in response.text
    assert "Time range: last 60 minutes" in response.text
    assert "Refresh: 30 seconds" in response.text
