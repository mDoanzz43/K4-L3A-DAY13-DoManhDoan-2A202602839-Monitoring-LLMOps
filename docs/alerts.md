# Alert và runbook

Các alert đều dựa trên triệu chứng người dùng/SLO. Thông báo gửi tới Slack
`#llmops-alerts`; correlation ID là khóa nối dashboard, structured log và Langfuse trace.

## Alert 1 High Latency P95

- **Tên:** `HighLatencyP95`
- **Severity:** warning
- **Duration:** 5 phút
- **Kênh thông báo:** Slack `#llmops-alerts`
- **Owner:** `oncall-engineer`
- **SLI/SLO liên quan:** P95 latency; request tốt phải hoàn tất trong tối đa 3000 ms.
- **Điều kiện:** `latency_p95_ms > 2500` liên tục 5 phút. Cảnh báo sớm trước khi vi phạm ngưỡng SLO 3000 ms.
- **Ảnh hưởng:** Người dùng chờ lâu; tail latency tăng dù average có thể vẫn bình thường.
- **Ba bước kiểm tra đầu tiên:**
  1. Mở panel Latency, xác định thời điểm P95/P99 bắt đầu tăng và kiểm tra TTFT.
  2. Trong cùng khoảng thời gian, lọc `response_sent` có `latency_ms` cao và lấy `correlation_id`.
  3. Mở Langfuse trace cùng correlation ID, so sánh thời gian retrieval và generation.
- **Mitigation tạm thời:** Giảm concurrency, tắt incident/practice flag nếu đang bật; nếu retrieval chậm thì dùng fallback document/cache trong khi kiểm tra vector store.

## Alert 2 High Error Rate

- **Tên:** `HighErrorRate`
- **Severity:** critical
- **Duration:** 3 phút
- **Kênh thông báo:** Slack `#llmops-alerts`
- **Owner:** `oncall-engineer`
- **SLI/SLO liên quan:** Error rate; guardrail tối đa 2%.
- **Điều kiện:** `error_rate_pct > 2.0` liên tục 3 phút.
- **Ảnh hưởng:** Một phần request `/chat` trả lỗi và người dùng không nhận được câu trả lời.
- **Ba bước kiểm tra đầu tiên:**
  1. Xem panel Errors để xác định tỷ lệ và breakdown theo `error_type`.
  2. Lọc `request_failed`, lấy correlation ID và kiểm tra `tool_name`/`tool_success`.
  3. Mở trace tương ứng, tìm observation lỗi và status message ở retrieval hoặc generation.
- **Mitigation tạm thời:** Tắt thành phần/feature gây lỗi, dùng fallback an toàn và retry có giới hạn; rollback prompt nếu lỗi xuất hiện ngay sau khi đổi production label.

## Alert 3 Low Retrieval Success Rate

- **Tên:** `LowRetrievalSuccessRate`
- **Severity:** warning
- **Duration:** 5 phút
- **Kênh thông báo:** Slack `#llmops-alerts`
- **Owner:** `rag-team`
- **SLI/SLO liên quan:** Retrieval success rate; guardrail tối thiểu 90%.
- **Điều kiện:** `retrieval_success_rate_pct < 90.0` liên tục 5 phút.
- **Ảnh hưởng:** Câu trả lời thiếu grounding, có nguy cơ giảm chất lượng dù API vẫn trả HTTP 200.
- **Ba bước kiểm tra đầu tiên:**
  1. So sánh panel Retrieval success với Quality proxy trong cùng cửa sổ.
  2. Lọc log có `tool_name=retrieval` và `tool_success=false`, lấy correlation ID.
  3. Mở retrieval observation trên Langfuse, kiểm tra document count, latency và lỗi.
- **Mitigation tạm thời:** Dùng corpus/fallback document đã kiểm chứng, giảm tải truy vấn và kiểm tra lại kết nối/index trước khi bật lại retrieval chính.
