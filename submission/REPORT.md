# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Đỗ Mạnh Đoan
- **MSSV:** 2A202602839
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/mDoanzz43/K4-L3A-DAY13-DoManhDoan-2A202602839-Monitoring-LLMOps
- **Commit SHA cuối:** 
- **Challenge ID:** day13-k4-l3a-monitoring-llmops-v1
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602839`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| CP0 — Langfuse project có trace | `evidence/06-trace-list.png` |
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-version1.png`, `evidence/09-prompt-version2.png` |
| Prompt rollback | `evidence/10-prompt-promoted.png`, `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | 100/100 | Vượt mục tiêu gate (≥80/100), đạt điểm tuyệt đối |
| `validate_dashboard.py` | 6/6 panel | 6/6 panel | Hợp lệ toàn bộ 6 panel theo contract dashboard.yaml |
| `pytest` | 22 passed | 28 passed | 100% test pass; bổ sung test PII, middleware, tracing và dashboard runtime |
| Số traces hợp lệ | 0 | 18 | Observations API v2 xác nhận 18 root traces gần nhất; workload cuối tạo 10 traces mới |
| Số PII leak | 0 | 0 | Đã scrub sạch Email, Phone VN, Credit Card, CCCD |
| Latency P95 / TTFT P95 | 1292.0ms / 50.0ms | 1276.0ms / 50.0ms | Dashboard runtime: P50 152ms, P99 1276ms |
| Retrieval success rate | 100% | 100% | 10/10 requests thành công |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Trong `CorrelationIdMiddleware` (`app/middleware.py`), trước mỗi request gọi `clear_contextvars()` để tránh rò rỉ context giữa các request. Header `x-request-id` chỉ được nhận khi khớp chính xác `req-<8-hex>`; nếu thiếu hoặc sai định dạng thì sinh ID mới bằng `f"req-{uuid.uuid4().hex[:8]}"`. Sau đó bind vào `structlog` contextvars qua `bind_contextvars(correlation_id=correlation_id)` và lưu vào `request.state.correlation_id`. Khi request hoàn tất, trả correlation ID qua response header `x-request-id` và thời gian xử lý qua header `x-response-time-ms`.
- **Các metadata được ghi vào structured log:** Tại endpoint `/chat` (`app/main.py`), trước khi ghi log `request_received`, gọi `bind_contextvars` để enrich context với: `user_id_hash` (băm sha256 12 ký tự), `session_id`, `feature`, `model` (lấy từ `agent.model`), và `env` (từ biến môi trường `APP_ENV`). Nhờ vậy các log tiếp theo (`response_sent`, `request_failed`) đều tự động chứa đầy đủ các trường này.
- **Cách bảo đảm PII được scrub trước khi ghi:** Xây dựng processor `scrub_event` và hàm đệ quy `_scrub_value` trong `app/logging_config.py` để quét và che toàn bộ chuỗi nhạy cảm theo các regex trong `app/pii.py` (`email`, `phone_vn`, `cccd`, `credit_card`). Processor `scrub_event` được đặt ngay trước `JsonlFileProcessor` và `JSONRenderer` trong pipeline của `structlog`, đảm bảo dữ liệu luôn được che giấu thành `[REDACTED_...]` trước khi serialize JSON hoặc ghi vào file `data/logs.jsonl`.
- **Cách kiểm chứng kết quả:** Chạy `python scripts/validate_logs.py` đạt 100/100 điểm với 0 PII leak detected. Chạy `python -m pytest -q` pass 28/28 tests, gồm Email, Phone VN, CCCD, thẻ thanh toán, propagation/validation correlation ID, tracing và dashboard runtime. Kiểm tra trực tiếp runtime log thấy các trường PII đã được thay thế thành `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CCCD]`, `[REDACTED_CREDIT_CARD]`.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Workload được chạy với key của project `day13-k4-l3a-2A202602839`. Sau khi flush SDK, truy vấn Langfuse Observations API v2 trong cửa sổ 10 phút ghi nhận 18 root observations gần nhất; 10 request cuối đều trả HTTP 200 và sinh trace riêng.
- **Cấu trúc root/retrieval/generation observations:** Root `lab-agent-run` loại `AGENT`; hai child cùng parent là `knowledge-retrieval` loại `RETRIEVER` và `llm-generation` loại `GENERATION`. Candidate trace `8492f5c40df54696c41e5030ff7d31ca` có model `claude-sonnet-4-5`, usage 49 input + 107 output = 156 tokens, total cost `$0.001752`.
- **Cách nối trace với log:** Middleware tạo `correlation_id`, bind vào structured log và truyền vào `LabAgent.run`. Cùng ID được đặt trong metadata của root, retrieval và generation; ví dụ candidate trace dùng `req-4c3fbcbf`. Không capture raw input/output; chỉ ghi preview đã qua `summarize_text`/PII scrubber.
- **Prompt name:** `day13-chat`.
- **Version/label baseline:** version 1, labels `baseline` và `production` (trạng thái cuối sau rollback).
- **Version/label candidate:** version 2, label `candidate`; template vẫn giữ đủ `{{feature}}`, `{{docs}}`, `{{message}}` và thêm yêu cầu trả lời súc tích theo context.
- **Trace ID của mỗi version:** baseline/v1 `3962e96a8fc47342392697d04e4fa197`; candidate/v2 `8492f5c40df54696c41e5030ff7d31ca`; production sau promote v2 `a505b5ab2b1aa0bec39aacb194ec3f98`; production sau rollback v1 `ecfd42e9718e5ba73449cb7be1a4f454`.
- **Cách promote và rollback `production`:** Dùng `scripts/complete_cp2_langfuse.py`: bỏ `production` khỏi v1 và gắn vào v2, chạy một trace xác nhận; sau đó bỏ label khỏi v2, gắn lại `baseline, production` cho v1 và chạy trace rollback. Script dùng cache TTL 0 để mỗi lần kiểm chứng đọc label mới nhất. Trạng thái cuối đã xác nhận: v1=`baseline, production`, v2=`candidate`.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Dashboard runtime tại `/dashboard` đọc `data/logs.jsonl` trong cửa sổ 60 phút, tự refresh 30 giây và hiển thị đúng 6 panel: Latency/TTFT, Traffic, Errors/Retrieval, Cost, Tokens và Quality. Ảnh cuối ghi nhận P95 1276ms, TTFT P95 50ms, traffic 3.30 request/phút, error 0%, retrieval 100%, cost `$0.040518`, tổng 3242 tokens và quality 0.880. Contract được kiểm tra bằng `validate_dashboard.py` đạt 6/6.
- **SLO và lý do chọn:** `config/slo.yaml` định nghĩa request tốt là `response_sent` có latency ≤3000ms, mục tiêu 99.5% trong 28 ngày. Baseline P95 1292ms nên 3000ms tạo khoảng đệm hợp lý cho concurrency nhưng vẫn phát hiện rõ retrieval chậm; guardrails bổ sung error ≤2%, cost/ngày ≤$2.5, quality ≥0.75 và retrieval success ≥90%.
- **Cách tính error budget:** `100% - 99.5% = 0.5%`; tương đương tối đa 5 bad requests/1000, 50/10000, hoặc 201.6 phút trong 28 ngày nếu minh họa theo availability liên tục.
- **Ba alert và runbook tương ứng:** `HighLatencyP95` (>2500ms trong 5m, warning), `HighErrorRate` (>2% trong 3m, critical), `LowRetrievalSuccessRate` (<90% trong 5m, warning). Cả ba là symptom-based, có owner, Slack `#llmops-alerts` và runbook Metrics → Logs → Traces tại `docs/alerts.md`.

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1` (cohort K4, seed 1311, affected feature `monitoring`).
- **Khoảng thời gian điều tra:** 2026-09-29 11:57:45Z–11:58:03Z. Challenge chạy 5 query với concurrency 5; `rag_slow` được tắt ngay sau khi thu evidence.
- **Triệu chứng từ metrics:** So với baseline P95 1276ms/P99 1276ms, dashboard incident ghi nhận P95 tăng lên 2654ms và P99 lên 3927ms; vượt `latency_threshold_ms=2000` của challenge. Error rate vẫn 0%, retrieval success 100%, TTFT P95 vẫn 50ms, nên đây là sự cố latency chứ không phải lỗi request hay generation TTFT.
- **Log line và correlation ID liên quan:** Request session `k4-l3a-challenge-s03`, `correlation_id=req-9715a095`, `response_sent.latency_ms=3927`, `ttft_ms=50`, `tool_name=retrieval`, `tool_success=true`, timestamp `2026-09-29T11:57:52.210511Z`.
- **Trace ID và span gây ảnh hưởng:** Langfuse trace `2920186b9db9c1d3eb81571b964ad3c2` có cùng `correlation_id=req-9715a095`. Root `lab-agent-run` mất 3.928s; child `knowledge-retrieval` mất 2.501s trong khi `llm-generation` chỉ 0.152s. Retrieval là span chiếm phần lớn latency.
- **Root cause:** Challenge bật incident `rag_slow`, làm retrieval sleep/chậm 2.5 giây. Generation, token/cost và TTFT không tăng tương ứng, nên không phải LLM là nút thắt.
- **Fix action:** Tắt `rag_slow`; với hệ thống thật, kiểm tra vector store/index/network, đặt timeout và fallback cho retrieval, cache các truy vấn phổ biến, đồng thời giới hạn concurrency để tránh tail latency bị khuếch đại.
- **Preventive measure:** Alert `HighLatencyP95` và `LowRetrievalSuccessRate`; theo dõi riêng latency retrieval, đặt span budget/timeout, circuit breaker và load test định kỳ. Runbook bắt buộc nối metric → correlation ID trong log → retrieval span trong trace trước khi kết luận.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Tôi dùng `correlation_id` làm khóa xuyên suốt structured log và metadata của cả root/retrieval/generation observations. Dashboard runtime đọc cùng nguồn `data/logs.jsonl`, còn Langfuse giữ trace chi tiết; cách tách này giữ log dễ truy vấn nhưng vẫn khoanh vùng được span mà không capture raw PII.
- **Một lỗi/blocker đã gặp:** Langfuse organization mới trả HTTP 410 khi script dùng legacy `GET /api/public/traces`, dù dữ liệu trace đã được ingest thành công.
- **Cách tìm nguyên nhân và xử lý:** Tôi đọc error response, xác nhận endpoint thay thế rồi chuyển script sang Observations API v2 `get_many`, lọc root observation theo session và nhóm bằng `trace_id`. Sau đó truy vấn các field group `metadata,model,usage,prompt,metrics` để kiểm tra cây trace, token và cost.
- **Cách hiểu luồng Metrics → Logs → Traces:** Metrics cho biết triệu chứng và cửa sổ sự cố (P95/P99 tăng); structured log trong cửa sổ đó cung cấp request cụ thể qua `correlation_id`; trace cùng ID cho thấy thời gian từng child span. Với challenge, dashboard chỉ ra P95 2654ms/P99 3927ms, log chọn `req-9715a095`, rồi trace chứng minh retrieval 2.501s trong khi generation chỉ 0.152s, từ đó kết luận `rag_slow` là root cause.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** Prompt version/label cho biết chính xác nội dung nào phục vụ request và cho phép rollback mà không sửa code. Token/cost giúp phát hiện output bất thường hoặc cost spike. SLO/error budget chuyển metric thành mức chấp nhận vận hành; alert duration tránh cảnh báo do spike ngắn. Workflow promote v2 rồi rollback v1 đã được xác nhận bằng hai trace thật.
- **Điều quan trọng nhất đã học:** Không nên kết luận nguyên nhân chỉ từ average hoặc một lớp dữ liệu. Một incident đáng tin cậy cần metric xác định triệu chứng, log xác định request và trace chứng minh span gây ảnh hưởng, đồng thời evidence phải cùng correlation ID/thời gian.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Lab dùng fake LLM và dashboard local dựa trên JSONL nên chưa phản ánh storage/aggregation phân tán ở production. Phần kỹ thuật và evidence bắt buộc CP0–CP3 đã hoàn thành; commit SHA cuối và thao tác nộp LMS chỉ được chốt ở CP4 sau lần kiểm tra cuối.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit nội dung cuối đã kiểm thử.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối sẽ được nộp trên LMS/Codelabs sau khi push.
