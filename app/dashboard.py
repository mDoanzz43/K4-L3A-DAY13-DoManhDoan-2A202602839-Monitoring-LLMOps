from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from statistics import mean
from typing import Any

from .logging_config import LOG_PATH
from .metrics import percentile


WINDOW_MINUTES = 60


def _challenge_latency_threshold() -> int | None:
    path = Path("config/challenge.json")
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8")).get("latency_threshold_ms")
    except (json.JSONDecodeError, OSError):
        return None
    return value if isinstance(value, int) and value > 0 else None


def _timestamp(record: dict[str, Any]) -> datetime | None:
    raw = record.get("ts")
    if not isinstance(raw, str):
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def load_recent_records(path: Path = LOG_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    timestamps = [value for record in records if (value := _timestamp(record))]
    if not timestamps:
        return records
    cutoff = max(timestamps) - timedelta(minutes=WINDOW_MINUTES)
    return [record for record in records if (_timestamp(record) or cutoff) >= cutoff]


def dashboard_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    requests = [record for record in records if record.get("event") == "request_received"]
    responses = [record for record in records if record.get("event") == "response_sent"]
    failures = [record for record in records if record.get("event") == "request_failed"]
    latencies = [int(record["latency_ms"]) for record in responses if "latency_ms" in record]
    ttfts = [int(record["ttft_ms"]) for record in responses if "ttft_ms" in record]
    qualities = [float(record["quality_score"]) for record in responses if "quality_score" in record]
    retrieval_events = [
        record
        for record in records
        if record.get("tool_name") == "retrieval" and record.get("tool_success") is not None
    ]
    retrieval_success = (
        100 * sum(record.get("tool_success") is True for record in retrieval_events) / len(retrieval_events)
        if retrieval_events
        else 0.0
    )
    error_types = Counter(str(record.get("error_type", "unknown")) for record in failures)
    request_count = len(requests)
    request_times = [value for record in requests if (value := _timestamp(record))]
    active_minutes = (
        max(1.0, (max(request_times) - min(request_times)).total_seconds() / 60)
        if len(request_times) >= 2
        else 1.0
    )
    return {
        "latency_p50": percentile(latencies, 50),
        "latency_p95": percentile(latencies, 95),
        "latency_p99": percentile(latencies, 99),
        "ttft_p95": percentile(ttfts, 95),
        "request_count": request_count,
        "requests_per_minute": round(request_count / active_minutes, 2),
        "error_rate_pct": round(100 * len(failures) / request_count, 2) if request_count else 0.0,
        "error_breakdown": dict(error_types),
        "retrieval_success_pct": round(retrieval_success, 2),
        "total_cost_usd": round(sum(float(record.get("cost_usd", 0)) for record in responses), 6),
        "tokens_in": sum(int(record.get("tokens_in", 0)) for record in responses),
        "tokens_out": sum(int(record.get("tokens_out", 0)) for record in responses),
        "quality_avg": round(mean(qualities), 3) if qualities else 0.0,
        "record_count": len(records),
    }


def _metric(label: str, value: str) -> str:
    return f'<div class="metric"><span>{escape(label)}</span><strong>{escape(value)}</strong></div>'


def render_dashboard(records: list[dict[str, Any]]) -> str:
    summary = dashboard_summary(records)
    challenge_threshold = _challenge_latency_threshold()
    latency_limit = challenge_threshold or 3000
    latency_threshold_text = "P95 SLO ≤ 3000 ms"
    if challenge_threshold:
        latency_threshold_text += f" • challenge > {challenge_threshold} ms"
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    errors = ", ".join(f"{key}: {value}" for key, value in summary["error_breakdown"].items()) or "none"
    cards = [
        ("latency", "Latency & TTFT", latency_threshold_text, "ms", "ok" if summary["latency_p95"] <= latency_limit else "bad", "".join([
            _metric("Latency P50", f'{summary["latency_p50"]:.0f} ms'),
            _metric("Latency P95", f'{summary["latency_p95"]:.0f} ms'),
            _metric("Latency P99", f'{summary["latency_p99"]:.0f} ms'),
            _metric("TTFT P95", f'{summary["ttft_p95"]:.0f} ms'),
        ])),
        ("traffic", "Traffic", "Expected ≥ 1 request/min", "requests/min", "ok" if summary["requests_per_minute"] >= 1 else "warn", "".join([
            _metric("Requests", str(summary["request_count"])),
            _metric("Rate", f'{summary["requests_per_minute"]:.2f} req/min'),
        ])),
        ("errors", "Errors & Retrieval", "Error ≤ 2% • Retrieval ≥ 90%", "%", "ok" if summary["error_rate_pct"] <= 2 and summary["retrieval_success_pct"] >= 90 else "bad", "".join([
            _metric("Error rate", f'{summary["error_rate_pct"]:.2f}%'),
            _metric("Retrieval success", f'{summary["retrieval_success_pct"]:.2f}%'),
            _metric("Breakdown", errors),
        ])),
        ("cost", "Cost", "60-minute budget ≤ $2.50", "USD", "ok" if summary["total_cost_usd"] <= 2.5 else "bad", _metric("Total cost", f'${summary["total_cost_usd"]:.6f}')),
        ("tokens", "Tokens", "Combined threshold ≤ 50,000", "tokens", "ok" if summary["tokens_in"] + summary["tokens_out"] <= 50000 else "bad", "".join([
            _metric("Input", f'{summary["tokens_in"]:,}'),
            _metric("Output", f'{summary["tokens_out"]:,}'),
            _metric("Total", f'{summary["tokens_in"] + summary["tokens_out"]:,}'),
        ])),
        ("quality", "Quality proxy", "Average target ≥ 0.75", "score 0–1", "ok" if summary["quality_avg"] >= 0.75 else "bad", _metric("Average", f'{summary["quality_avg"]:.3f}')),
    ]
    panels = "".join(
        f'''<section class="panel" data-panel="{panel_id}">
          <div class="panel-head"><div><h2>{title}</h2><small>{unit}</small></div><span class="status {status}">{threshold}</span></div>
          <div class="metrics">{content}</div>
        </section>'''
        for panel_id, title, threshold, unit, status, content in cards
    )
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="30">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Day 13 LLMOps Dashboard</title>
<style>
:root{{--bg:#08111f;--surface:#101d30;--line:#24344d;--text:#e8eef8;--muted:#93a4bc;--cyan:#38bdf8;--green:#34d399;--amber:#fbbf24;--red:#fb7185}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at top right,#123354 0,#08111f 42%);color:var(--text);font:16px Inter,Segoe UI,sans-serif}}
main{{max-width:1500px;margin:auto;padding:34px}}header{{display:flex;justify-content:space-between;align-items:end;margin-bottom:28px}}h1{{font-size:34px;margin:0 0 8px}}p,small{{color:var(--muted)}}.meta{{text-align:right;line-height:1.6}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}}.panel{{min-height:245px;background:linear-gradient(145deg,rgba(20,36,59,.96),rgba(12,25,43,.96));border:1px solid var(--line);border-radius:18px;padding:22px;box-shadow:0 18px 50px rgba(0,0,0,.22)}}
.panel-head{{display:flex;justify-content:space-between;gap:16px;align-items:start;border-bottom:1px solid var(--line);padding-bottom:15px}}h2{{margin:0 0 4px;font-size:22px}}.status{{font-size:12px;border-radius:999px;padding:7px 10px;font-weight:700}}.ok{{color:var(--green);background:#123d37}}.warn{{color:var(--amber);background:#443514}}.bad{{color:var(--red);background:#471e2a}}
.metrics{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:18px}}.metric{{background:#0a1728;border:1px solid #1e3049;border-radius:12px;padding:13px;display:flex;flex-direction:column;gap:8px}}.metric span{{color:var(--muted);font-size:13px}}.metric strong{{font-size:22px;color:#fff;word-break:break-word}}footer{{margin-top:22px;color:var(--muted)}}
@media(max-width:1000px){{.grid{{grid-template-columns:1fr 1fr}}}}@media(max-width:650px){{.grid{{grid-template-columns:1fr}}header{{display:block}}.meta{{text-align:left;margin-top:12px}}}}
</style></head><body><main><header><div><h1>K4-L3A Day 13 — Monitoring & LLMOps</h1><p>Runtime dashboard sourced from <code>data/logs.jsonl</code></p></div><div class="meta">Time range: last 60 minutes<br>Refresh: 30 seconds<br>{generated_at}</div></header>
<div class="grid">{panels}</div><footer>{summary["record_count"]} log records analyzed • Metrics → Logs → Traces</footer></main></body></html>'''
