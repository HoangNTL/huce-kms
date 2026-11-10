# HUCE-KMS Content Crawler — Báo cáo Nghiệm thu Thực tế Phase 2 (Discovery, Human Approval & Batch Crawling)

> **Dự án**: HUCE-KMS (Hệ thống Quản lý Tri thức & Trợ lý AI - Trường Đại học Xây dựng Hà Nội)  
> **Module**: Content Crawler (Phase 2 — Discovery Engine, Review Queue & Batch Mode)  
> **Ngày thực hiện**: 2026-11-10  
> **Trạng thái**: Hoàn thành 100% mục tiêu Phase 2, đã kiểm thử thành công trên hệ thống cổng thông tin thực tế của HUCE  

---

## 1. Mục tiêu Nghiệm thu Phase 2

Phase 2 triển khai mô hình cốt lõi **Hybrid — URL-based Crawling + Discovery + Human Approval**, đảm bảo các yêu cầu kiến trúc đã thống nhất:
1. **Discovery Engine (`DISCOVERY` Mode)**: Quét danh mục, sitemap hoặc RSS feed để phát hiện các URL bài viết tiềm năng mà không tự ý crawl toàn bộ website.
2. **URL Normalizer**: Chuẩn hóa đường dẫn tuyệt đối, loại bỏ tham số theo dõi (`utm_*`, `fbclid`), phân trang và loại bỏ URL ngoài phạm vi cho phép (`huce.edu.vn`).
3. **Review Queue Manager (`APPROVE` Mode)**: Lưu hàng đợi bài viết phát hiện được (`discovered_<timestamp>.json`), cho phép quản trị viên lựa chọn và phê duyệt danh sách URL trước khi crawl (`approved.json`).
4. **Batch Crawl Engine (`APPROVED` Mode)**: Tự động crawl danh sách URL đã được phê duyệt với cơ chế giới hạn luồng đồng thời (`asyncio.Semaphore`), ghi nhận chi tiết lịch sử phiên crawl (`sessions/<session_id>/`).
5. **CLI Runner mở rộng**: Hỗ trợ đầy đủ 3 lệnh con: `discover`, `approve`, `crawl --input`.

---

## 2. Kết quả Thực nghiệm End-to-End trên Cổng Thông tin Thực tế

### Bước 1: Khám phá URL tiềm năng từ trang Danh mục Quy chế CTSV (`discover`)
- **Lệnh thực thi**:
  ```bash
  uv run python -m tools.crawler.cli discover --url "https://ctsv.huce.edu.vn/quy-che-quy-dinh" --max-items 10
  ```
- **Kết quả trả về**:
  * **Trạng thái**: Hoàn thành thành công.
  * **Tổng số bài viết phát hiện**: 5 bài viết.
  * **Tệp hàng đợi sinh ra**: `apps/backend/data/crawled/crawl-queue/discovered_20261110_121854.json`
  * **Danh sách trích xuất kèm ngày đăng**:
    1. `QUY CHẾ VĂN HÓA HỌC ĐƯỜNG TẠI TRƯỜNG ĐẠI HỌC XÂY DỰNG HÀ NỘI` (30/08/2024)  
       -> `https://ctsv.huce.edu.vn/quy-che-van-hoa-hoc-duong-tai-truong-dai-hoc-xay-dung-ha-noi`
    2. `QUY CHẾ CÔNG TÁC SINH VIÊN ĐỐI VỚI CHƯƠNG TRÌNH ĐÀO TẠO ĐẠI HỌC HỆ CHÍNH QUY` (09/05/2024)  
       -> `https://ctsv.huce.edu.vn/quy-che-cong-tac-sinh-vien-doi-voi-chuong-trinh-dao-tao-dai-hoc-he-chinh-quy`
    3. `Quy chế đánh giá kết quả rèn luyện sinh viên đại học hệ chính quy` (29/12/2021)  
       -> `https://ctsv.huce.edu.vn/quy-che-danh-gia-ket-qua-ren-luyen-sinh-vien-dai-hoc-he-chinh-quy`
    4. `Quy chế xét cấp học bổng khuyến khích học tập` (29/12/2021)  
       -> `https://ctsv.huce.edu.vn/quy-che-xet-cap-hoc-bong-khuyen-khich-hoc-tap`
    5. `Quy định về việc miễn giảm học phí, Hỗ trợ chi phí học tập, Hỗ trợ học tập` (29/12/2021)  
       -> `https://ctsv.huce.edu.vn/quy-dinh-ve-viec-mien-giam-hoc-phi-ho-tro-chi-phi-hoc-tap-ho-tro-hoc-tap`

---

### Bước 2: Quản trị viên Phê duyệt URL cần thu thập (`approve`)
- **Lệnh thực thi**: Phê duyệt 2 bài viết quy chế mới nhất (chỉ số 1 và 2):
  ```bash
  uv run python -m tools.crawler.cli approve --input "data/crawled/crawl-queue/discovered_20261110_121854.json" --indices 1,2
  ```
- **Kết quả trả về**:
  * **Tệp danh sách phê duyệt**: `apps/backend/data/crawled/crawl-queue/approved.json`
  * **Số URL được duyệt**: 2 URLs.

---

### Bước 3: Thu thập Dữ liệu Hỗn hợp theo Lô đã Phê duyệt (`crawl --input`)
- **Lệnh thực thi**:
  ```bash
  uv run python -m tools.crawler.cli crawl --input "data/crawled/crawl-queue/approved.json" --concurrency 2
  ```
- **Kết quả trả về**:
  * **Session ID**: `2026-11-10_121938`
  * **Tổng URL xử lý**: 2/2 thành công (`100%`)
  * **Thời gian hoàn thành**: 11.13 giây (2 workers chạy song song)
  * **Kết quả từng bài viết**:
    1. **Bài viết 1**: `QUY CHẾ VĂN HÓA HỌC ĐƯỜNG TẠI TRƯỜNG ĐẠI HỌC XÂY DỰNG HÀ NỘI`
       - Status: `SUCCESS`
       - Tải về: 1 file PDF quy chế chính thức (`uc.pdf`, dung lượng 4.57 MB, gồm 10 trang văn bản).
       - Thư mục artifact: `apps/backend/data/crawled/pages/4f33474d82bba4a1/`
    2. **Bài viết 2**: `QUY CHẾ CÔNG TÁC SINH VIÊN ĐỐI VỚI CHƯƠNG TRÌNH ĐÀO TẠO ĐẠI HỌC HỆ CHÍNH QUY`
       - Status: `SUCCESS`
       - Tải về: 1 file PDF quy chế đào tạo (`uc.pdf`, dung lượng 8.17 MB, gồm 19 trang có dấu mộc).
       - Thư mục artifact: `apps/backend/data/crawled/pages/1d36ce9b6744fc44/`
  * **Lưu vết phiên làm việc (Session Logs)**:
    - `apps/backend/data/crawled/sessions/2026-11-10_121938/session.json`
    - `apps/backend/data/crawled/sessions/2026-11-10_121938/results.json`

---

## 3. Tổng hợp Bộ Kiểm thử Tự động (Automated Unit Tests)

Toàn bộ các module của Phase 2 được xây dựng theo chuẩn **Test-Driven Development (TDD)**:

| Tên Test Suite | File Kiểm Thử | Số Lượng Test | Trạng Thái |
| :--- | :--- | :---: | :---: |
| **URL Normalizer** | `tests/services/crawler/test_url_normalizer.py` | 5 | PASSED |
| **Listing Extractor** | `tests/services/crawler/test_listing_extractor.py` | 2 | PASSED |
| **Feed Parsers (Sitemap & RSS)** | `tests/services/crawler/test_feed_parsers.py` | 2 | PASSED |
| **Discovery Engine** | `tests/services/crawler/test_discovery_engine.py` | 2 | PASSED |
| **Review Queue Manager** | `tests/services/crawler/test_review_queue.py` | 2 | PASSED |
| **Batch Crawl Engine** | `tests/services/crawler/test_batch_crawl.py` | 1 | PASSED |
| **CLI Discovery & Approval** | `tests/services/crawler/test_cli_discovery.py` | 4 | PASSED |
| **Cộng dồn Phase 1 Tests** | `tests/services/crawler/test_*.py` | 23 | PASSED |
| **Tổng số Crawler Tests** | `tests/services/crawler/` | **41 tests** | **100% PASSED** |
| **Toàn bộ Test Suite Dự án** | `tests/` | **60 tests** | **100% PASSED** |

---

## 4. Kết luận & Sẵn sàng cho Phase 3

Hệ thống **HUCE-KMS Content Crawler** hiện đã hoàn thiện đầy đủ cả 3 chế độ vận hành:
1. **DIRECT Mode**: Dành cho bài viết chỉ định cụ thể.
2. **DISCOVERY Mode**: Tự động phát hiện danh sách bài viết từ danh mục / feed.
3. **APPROVED Mode**: Phê duyệt có kiểm soát bởi người dùng và crawl theo lô có giới hạn luồng song song.

Hệ thống đã sẵn sàng cho **Phase 3 (RAG Integration)**: Xây dựng `CrawlIngestionAdapter` để kết nối các Crawl Artifacts (`content.md`, `metadata.json`, `pdfs/`) vào pipeline `DocumentService` sẵn có của dự án.
