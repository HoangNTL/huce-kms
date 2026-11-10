# HUCE-KMS Content Crawler — Báo cáo Nghiệm thu Thực tế Phase 1 (Base Engine & DIRECT Mode)

> **Dự án**: HUCE-KMS (Hệ thống Quản lý Tri thức & Trợ lý AI - Trường Đại học Xây dựng Hà Nội)  
> **Module**: Content Crawler (Phase 1 — Base Engine)  
> **Ngày thực hiện**: 2026-11-10  
> **Trạng thái**: Hoàn thành và kiểm thử thành công trên các cổng thông tin thực tế của HUCE  

---

## 1. Mục tiêu Nghiệm thu Phase 1

Kiểm chứng hoạt động của **Core Crawler Engine** và **CLI Runner** ở chế độ **DIRECT Mode**, đảm bảo:
1. Crawl trực tiếp các URL bài viết thực tế từ các nguồn của Trường ĐH Xây Dựng Hà Nội (`huce.edu.vn`, `ctsv.huce.edu.vn`, `tuyensinh.huce.edu.vn`).
2. Làm sạch hoàn toàn mã rác (menu, footer, sidebar, mạng xã hội, banner quảng cáo).
3. Chuyển đổi nội dung chính sang định dạng **Markdown (`content.md`)** chuẩn ATX heading, giữ nguyên bảng biểu và phân cấp văn bản.
4. Tự động nhận diện và tải về các **tệp PDF đính kèm** (bao gồm cả các tài liệu được nhúng qua Google Drive preview iframes đặc thù của cổng thông tin HUCE) và **hình ảnh minh họa**.
5. Sinh file siêu dữ liệu chuẩn **`metadata.json`** kèm mã băm SHA-256 để chống trùng lặp và phục vụ nạp RAG ở Phase 3.

---

## 2. Kết quả Thực nghiệm trên các Cổng Thông tin Thực tế của HUCE

### Ca thử nghiệm 1: Bài viết Quy chế Đào tạo có tài liệu đính kèm (CTSV)
- **URL nguồn**: `https://ctsv.huce.edu.vn/quy-che-cong-tac-sinh-vien-doi-voi-chuong-trinh-dao-tao-dai-hoc-he-chinh-quy`
- **Lệnh thực thi**:
  ```bash
  uv run python -m tools.crawler.cli crawl --url "https://ctsv.huce.edu.vn/quy-che-cong-tac-sinh-vien-doi-voi-chuong-trinh-dao-tao-dai-hoc-he-chinh-quy"
  ```
- **Kết quả trả về**:
  * **Trạng thái**: `SUCCESS` (Thời gian xử lý: 4.93s)
  * **Thư mục lưu trữ**: `apps/backend/data/crawled/pages/1d36ce9b6744fc44/`
  * **Tiêu đề**: QUY CHẾ CÔNG TÁC SINH VIÊN ĐỐI VỚI CHƯƠNG TRÌNH ĐÀO TẠO ĐẠI HỌC HỆ CHÍNH QUY
  * **Ngày đăng trích xuất**: `09/05/2024`
  * **Tài liệu PDF tải về**: 1 file (`uc_2.pdf`, kích thước 8,172,924 bytes ~ 8.17MB, gồm 19 trang văn bản có dấu đỏ đóng mộc).
  * **Hình ảnh tải về**: 0 file rác (toàn bộ icon footer/mạng xã hội đã được lọc sạch).
  * **Trích đoạn `content.md`**:
    ```markdown
    # QUY CHẾ CÔNG TÁC SINH VIÊN ĐỐI VỚI CHƯƠNG TRÌNH ĐÀO TẠO ĐẠI HỌC HỆ CHÍNH QUY

    - **Nguồn:** https://ctsv.huce.edu.vn/quy-che-cong-tac-sinh-vien-doi-voi-chuong-trinh-dao-tao-dai-hoc-he-chinh-quy
    - **Ngày crawl:** 2026-11-10T11:24:32.020045+00:00
    - **Ngày đăng:** 09/05/2024

    ---

    [Tài liệu đính kèm (Google Drive)](./pdfs/uc_2.pdf)

    ## Tài liệu đính kèm

    - [uc_2.pdf](./pdfs/uc_2.pdf)
    ```

---

### Ca thử nghiệm 2: Bài viết Tuyển sinh chứa nhiều hình ảnh minh họa (Tuyensinh)
- **URL nguồn**: `https://tuyensinh.huce.edu.vn/thong-tin-tuyen-sinh-dai-hoc-chinh-quy`
- **Lệnh thực thi**:
  ```bash
  uv run python -m tools.crawler.cli crawl --url "https://tuyensinh.huce.edu.vn/thong-tin-tuyen-sinh-dai-hoc-chinh-quy"
  ```
- **Kết quả trả về**:
  * **Trạng thái**: `PARTIAL` (Xử lý kiên cường: có 1 link ảnh phía trường bị 404, crawler ghi nhận cảnh báo và tiếp tục hoàn tất 20 ảnh còn lại mà không làm gãy tiến trình).
  * **Thư mục lưu trữ**: `apps/backend/data/crawled/pages/bc2075fe726d0bff/`
  * **Tiêu đề**: Thông tin tuyển sinh Đại học hệ chính quy
  * **Hình ảnh tải về**: 20 ảnh minh họa sơ đồ, infographic chỉ tiêu tuyển sinh lưu tại `images/`.

---

### Ca thử nghiệm 3: Báo cáo công khai dạng bảng biểu (HUCE Portal chính)
- **URL nguồn**: `https://huce.edu.vn/bao-cao-cong-khai-nam-2024`
- **Kết quả**: Bảng biểu cam kết chất lượng giáo dục (`| TT | Nội dung |`) được bảo toàn nguyên vẹn dạng Markdown Table chuẩn, loại bỏ các khối module điều hướng của website.

---

## 3. Cấu trúc Thư mục Dữ liệu Đầu ra (`data/crawled/`)

```text
apps/backend/data/crawled/
└── pages/
    ├── 1d36ce9b6744fc44/                        # Hash nhận diện URL (ctsv quy chế)
    │   ├── content.md                           # Markdown sạch kèm đường dẫn tương đối tới PDF
    │   ├── metadata.json                        # Manifest chuẩn (nguồn, ngày lấy, hash, media)
    │   ├── raw.html                             # Bản sao lưu HTML gốc ban đầu
    │   ├── pdfs/
    │   │   └── uc_2.pdf                         # File PDF quy chế 19 trang đã tải về local
    │   └── images/                              # Không có ảnh rác
    │
    └── bc2075fe726d0bff/                        # Tuyển sinh ĐHCQ
        ├── content.md
        ├── metadata.json
        ├── raw.html
        └── images/                              # 20 ảnh infographic tuyển sinh
```

---

## 4. Tổng kết Bộ Kiểm thử Tự động (Unit Tests)

Toàn bộ 43 unit tests của dự án (gồm 23 test RAG pipeline sẵn có và 20 test mới của module Crawler) đều chạy thành công 100%:
- `test_schemas.py`: Xác thực DTO Pydantic V2 và cấu hình cài đặt.
- `test_fetcher.py`: Kiểm thử chống SSRF, chặn IP nội bộ, chặn loopback, kiểm soát domain allowlist.
- `test_html_cleaner.py`: Kiểm thử bóc tách vùng bài viết chính, lọc thẻ giao diện thừa.
- `test_link_discoverer.py`: Kiểm thử quét liên kết PDF trực tiếp và Google Drive embedded preview.
- `test_markdown_converter.py`: Kiểm thử sinh Markdown, bảo toàn bảng và chuyển link cục bộ.
- `test_file_downloader.py`: Kiểm thử streaming download, giới hạn kích thước file và kiểm tra chữ ký file (%PDF, PNG).
- `test_artifact_storage.py`: Kiểm thử phân cấp thư mục và tính nhất quán của mã băm URL.
- `test_crawler_engine.py`: Kiểm thử luồng điều phối tích hợp toàn trình.
- `test_cli.py`: Kiểm thử CLI giao diện dòng lệnh.

```text
Ran 43 tests in 1.814s
OK
```
