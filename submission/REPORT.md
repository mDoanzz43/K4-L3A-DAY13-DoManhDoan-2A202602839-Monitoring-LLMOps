# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Đỗ Mạnh Đoan
- **MSSV:** 2A202602839
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/mDoanzz43/K4-L3A-DAY13-DoManhDoan-2A202602839-Monitoring-LLMOps
- **Commit SHA cuối:** 
- **Challenge ID:** 
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602839`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| CP0 — Langfuse project có trace | `evidence/image.png` |
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | 100/100 | Vượt mục tiêu gate (≥80/100), đạt điểm tuyệt đối |
| `validate_dashboard.py` | 6/6 panel | 6/6 panel | Hợp lệ toàn bộ 6 panel theo contract dashboard.yaml |
| `pytest` | 22 passed | 26 passed | 100% test pass; bổ sung test PII và middleware correlation ID |
| Số traces hợp lệ | 0 | 10 | 10 traces được sinh qua load test |
| Số PII leak | 0 | 0 | Đã scrub sạch Email, Phone VN, Credit Card, CCCD |
| Latency P95 / TTFT P95 | 1292.0ms / 50.0ms | 1292.0ms / 50.0ms | P50 đạt ~403ms, TTFT P95 là 50ms |
| Retrieval success rate | 100% | 100% | 10/10 requests thành công |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Trong `CorrelationIdMiddleware` (`app/middleware.py`), trước mỗi request gọi `clear_contextvars()` để tránh rò rỉ context giữa các request. Header `x-request-id` chỉ được nhận khi khớp chính xác `req-<8-hex>`; nếu thiếu hoặc sai định dạng thì sinh ID mới bằng `f"req-{uuid.uuid4().hex[:8]}"`. Sau đó bind vào `structlog` contextvars qua `bind_contextvars(correlation_id=correlation_id)` và lưu vào `request.state.correlation_id`. Khi request hoàn tất, trả correlation ID qua response header `x-request-id` và thời gian xử lý qua header `x-response-time-ms`.
- **Các metadata được ghi vào structured log:** Tại endpoint `/chat` (`app/main.py`), trước khi ghi log `request_received`, gọi `bind_contextvars` để enrich context với: `user_id_hash` (băm sha256 12 ký tự), `session_id`, `feature`, `model` (lấy từ `agent.model`), và `env` (từ biến môi trường `APP_ENV`). Nhờ vậy các log tiếp theo (`response_sent`, `request_failed`) đều tự động chứa đầy đủ các trường này.
- **Cách bảo đảm PII được scrub trước khi ghi:** Xây dựng processor `scrub_event` và hàm đệ quy `_scrub_value` trong `app/logging_config.py` để quét và che toàn bộ chuỗi nhạy cảm theo các regex trong `app/pii.py` (`email`, `phone_vn`, `cccd`, `credit_card`). Processor `scrub_event` được đặt ngay trước `JsonlFileProcessor` và `JSONRenderer` trong pipeline của `structlog`, đảm bảo dữ liệu luôn được che giấu thành `[REDACTED_...]` trước khi serialize JSON hoặc ghi vào file `data/logs.jsonl`.
- **Cách kiểm chứng kết quả:** Chạy `python scripts/validate_logs.py` đạt 100/100 điểm với 0 PII leak detected và 30 unique correlation IDs. Chạy `python -m pytest -q` pass 26/26 tests, gồm Email, Phone VN, CCCD, thẻ thanh toán và propagation/validation correlation ID. Kiểm tra trực tiếp runtime log thấy các trường PII đã được thay thế thành `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CCCD]`, `[REDACTED_CREDIT_CARD]`.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:**
- **Cấu trúc root/retrieval/generation observations:**
- **Cách nối trace với log:**
- **Prompt name:**
- **Version/label baseline:**
- **Version/label candidate:**
- **Trace ID của mỗi version:**
- **Cách promote và rollback `production`:**

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:**
- **SLO và lý do chọn:**
- **Cách tính error budget:**
- **Ba alert và runbook tương ứng:**

## 7. Điều tra challenge

- **Challenge ID:**
- **Khoảng thời gian điều tra:**
- **Triệu chứng từ metrics:**
- **Log line và correlation ID liên quan:**
- **Trace ID và span gây ảnh hưởng:**
- **Root cause:**
- **Fix action:**
- **Preventive measure:**

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**
- **Một lỗi/blocker đã gặp:**
- **Cách tìm nguyên nhân và xử lý:**
- **Cách hiểu luồng Metrics → Logs → Traces:**
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
- **Điều quan trọng nhất đã học:**
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:**

## 9. Checklist trước khi nộp

- [ ] Kết quả và evidence thuộc commit SHA cuối.
- [ ] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [ ] Incident evidence nối đúng metric → log → trace.
- [ ] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [ ] Repository chạy lại được theo README.
- [ ] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
