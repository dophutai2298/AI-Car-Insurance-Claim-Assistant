# Hướng dẫn dự án

Các ghi chú bổ sung về cài đặt, cấu hình, workflow và bảo trì. README ở thư mục gốc chứa phần giới thiệu ngắn và các bước khởi động local.

## 1. Môi trường và chế độ chạy

Sao chép `.env.example` thành `.env` ở thư mục gốc repository. Không đưa secret hoặc dữ liệu local vào source control.

| Cấu hình | Giá trị hỗ trợ | Mặc định | Mục đích |
| --- | --- | --- | --- |
| `DAMAGE_MODEL_MODE` | `local` | `local` | Chạy `AI/CarDamageDetector` với model weights cục bộ. |
| `PART_SEARCH_MODE` | `mock`, `unavailable` | `mock` | Dùng catalog VNĐ trong PostgreSQL hoặc báo giá không khả dụng. |
| `DOCUMENT_OCR_MODE` | `deepdoc`, `mock` | `deepdoc` | Dùng DeepDoc OCR hoặc OCR demo xác định. |
| `LLM_MODE` | `mock`, `openai` | `mock` | Dùng response demo hoặc LangChain với chat model tương thích OpenAI. |

Cấu hình mẫu dùng detector xe cục bộ; tìm giá phụ tùng và LLM ở chế độ mock. OCR tài liệu mặc định dùng DeepDoc. Đặt `DOCUMENT_OCR_MODE=mock` để chạy demo tài liệu xác định hoặc test.

Để gọi LLM thật, cấu hình:

```dotenv
LLM_MODE=openai
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=your-supported-model
LLM_REQUEST_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=0
```

Khi không đặt `LLM_BASE_URL`, ứng dụng dùng endpoint OpenAI mặc định. Chỉ đặt biến này khi dùng nhà cung cấp tương thích OpenAI. Model cần hỗ trợ structured output theo yêu cầu của ứng dụng; khả năng truy cập và cách phản hồi tùy nhà cung cấp.

Đặt `LLM_TOKEN_USAGE_LOG_ENABLED=true` để in token usage do nhà cung cấp trả về cho document extraction, field validation và AI Review. Log gồm operation, model, số token và document type hoặc claim number; không ghi OCR text, prompt hay output của model. Token metadata không khả dụng nếu provider không trả về thông tin này.

Để debug local có kiểm soát, đặt `LLM_RAW_OUTPUT_LOG_ENABLED=true` để in JSON thô của AI Review trước khi parse và lưu. Output có thể chứa dữ liệu cá nhân và hồ sơ; hãy tắt ngoài môi trường phát triển được kiểm soát.

Detector lưu ảnh xe đã đánh dấu vào `UPLOAD_ROOT/<claim>/annotations/`. Các cấu hình liên quan gồm `DAMAGE_PART_MODEL_PATH`, `DAMAGE_MODEL_PATH`, `DAMAGE_OUTPUT_DIR`, `DAMAGE_PART_CONF`, `DAMAGE_DAMAGE_CONF`, `DAMAGE_MIN_PERCENT`, `DAMAGE_IMAGE_SIZE` và `DAMAGE_DEVICE`. Đường dẫn mặc định tính từ thư mục gốc repository. Chạy smoke test độc lập từ thư mục gốc:

```powershell
python backend/scripts/test_car_damage_detector.py
```

## 2. Tài khoản demo và API

Khi khởi động, backend tạo các bảng còn thiếu và seed user demo cùng danh sách hãng xe đã cấu hình. User hiện hữu không tự đổi theo credential trong environment. Đặt `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADJUSTER_EMAIL` và `ADJUSTER_PASSWORD` trong `.env` trước lần khởi động đầu tiên để chọn credential. Đổi mật khẩu tài khoản đã tồn tại bằng quy trình quản trị tài khoản hoặc database được phê duyệt.

API mặc định chạy tại `http://localhost:8000`:

- Health check: `GET /api/health`
- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI schema: `/openapi.json`

PostgreSQL mặc định lắng nghe ở cổng `5432`. Thông tin kết nối và credential container nằm trong `.env.example`; có thể ghi đè bằng `.env`.

## 3. Catalog giá xe và Step 4

Khi khởi động, ứng dụng tạo các bảng catalog/snapshot và seed giá minh họa cho Toyota Camry 2022, Toyota Vios 2023 và BMW M3 2024. Giá sửa và giá thay là các record riêng, so khớp chính xác theo hãng, model, năm, bộ phận và loại giá. Mã bộ phận chỉ chuẩn hóa chữ hoa/thường, khoảng trắng và dấu nối. Không có record chính xác thì giá không khả dụng.

Để seed catalog mock rộng hơn, chạy từ thư mục `backend`:

```powershell
python scripts/seed_price_catalog.py
```

Script bao phủ 19 hãng và các dòng xe khai báo trong source, từ 2015 đến năm hiện tại. Mỗi tổ hợp hãng/model/năm có giá sửa và thay riêng cho 21 nhãn bộ phận detector cùng bốn mã bộ phận lịch sử. Đây là tổ hợp và giá demo được tạo tự động, không phải năm sản xuất đã xác minh hoặc giá thị trường.

Có thể sửa `VEHICLES` (model và hệ số), `PART_PRICES_VND` (giá sửa/thay gốc) và `PRICE_OVERRIDES` (giá cụ thể theo hãng/model/năm/bộ phận). Giá tự sinh áp dụng hệ số model và điều chỉnh 3% mỗi năm so với 2024; hệ số năm nằm trong khoảng 60%-120%. Giá override bỏ qua cả hai hệ số.

Tùy chọn:

- `--dry-run` xem trước phạm vi mà không kết nối database.
- `--make Toyota --start-year 2020 --end-year 2026` giới hạn hãng và năm.
- Mặc định giữ nguyên giá đã có. `--update-existing` ghi đè giá và thay source metadata bằng nguồn mock của script.

Script đọc `DATABASE_URL` từ `.env` dự án và commit mọi thay đổi trong một transaction.

Mỗi Analysis lưu snapshot giá bất biến; catalog thay đổi chỉ áp dụng cho lần chạy sau. Snapshot USD lịch sử vẫn đọc được; giá VNĐ mới lưu dưới dạng số nguyên đồng.

Step 4 hiển thị đánh giá, tổng quan giá sửa/thay và bảng giá từng phụ tùng kèm nguồn. Khi thiếu giá, UI ghi rõ đây là tổng phụ các giá đã biết, chưa phải tổng ước tính đầy đủ. Giá mock chỉ tham khảo, chưa gồm công, vật tư, thuế và phí xưởng chưa được mô hình hóa. Giá không quyết định khoản bồi thường hoặc thay thế quyết định của adjuster.

AI Review nhận snapshot giá đã lưu trong request LLM hiện có. `price_recommendation` gồm `recommendation` (`SUPPORTS_REPAIR`, `SUPPORTS_REPLACEMENT` hoặc `MANUAL_REVIEW`) và `rationale` ngắn. Thiếu giá ở nhóm sửa hoặc thay sẽ yêu cầu thẩm định giá thủ công nhưng không làm mất các phần review còn lại. Khuyến nghị trái với đánh giá hư hỏng xác định cũng cần thẩm định thủ công. Số tiền trên UI luôn lấy từ Analysis; AI không tự tính giá. Khi AI mock hoặc không khả dụng, khuyến nghị giá vẫn là thẩm định thủ công.

Bản dịch tiếng Việt gồm cả rationale và giữ mã recommendation. Review lịch sử chưa có khuyến nghị giá vẫn xem được; chạy lại AI Review để tạo revision mới từ snapshot Analysis đã lưu. Version prompt/schema: `ai-review-v3-pricing` / `ai-review-schema-v3-pricing`; bản dịch: `ai-review-translation-vi-v2-pricing` / `ai-review-translation-schema-v2-pricing`.

## 4. Ngưỡng đánh giá hư hỏng

Admin cấu hình cách diễn giải kết quả model tại **Assessment rules**. Ngưỡng áp dụng cho từng bộ phận xe được phát hiện, không phải tỷ lệ hư hỏng của toàn bộ xe. Mặc định: ngưỡng sửa chữa tối đa 40%, ngưỡng thay thế tối thiểu 60%.

- Nếu mọi bộ phận được phát hiện bằng hoặc thấp hơn ngưỡng sửa chữa, kết quả là **Có khả năng sửa chữa**.
- Nếu một bộ phận đạt hoặc vượt ngưỡng thay thế, kết quả là **Có khả năng cần thay thế**. `broken_component` và `severe_deformation` cũng kích hoạt kết quả này bất kể phần trăm.
- Giá trị nằm giữa hai ngưỡng cần **kiểm tra thủ công**.

Với mặc định, 35% có thể hỗ trợ sửa chữa, 50% cần kiểm tra thủ công và 65% hỗ trợ thay thế. Admin có thể đổi giá trị toàn cục; mỗi analysis lưu ngưỡng đã dùng cho lần chạy đó. Đây là quy tắc hỗ trợ đánh giá, không phải quyết định bảo hiểm cuối cùng.

## 5. Điểm hoàn thiện phân tích ở Step 4

Step 4 chỉ chạy sau khi Step 3 lưu được analysis snapshot sẵn sàng. Step 3 chặn **Save All** nếu phân tích tài liệu bắt buộc thất bại, thiếu giá trị bắt buộc, hoặc giá trị có thể so sánh là `MISMATCH` hay không thể kiểm tra. Cần sửa dữ liệu và hoàn tất Step 3 trước khi chạy AI Review. Mismatch là điều kiện chặn workflow, không phải khoản trừ điểm.

**Analysis completeness score** được tính theo quy tắc xác định. LLM không tạo điểm này; đây cũng không phải xác suất hồ sơ hợp lệ hay được duyệt. Mỗi review đủ điều kiện bắt đầu từ 100 điểm, trừ 5 điểm cho mỗi warning trong snapshot đã lưu; điểm thấp nhất là 0:

```text
điểm = max(0, 100 - (số warning * 5))
```

Ví dụ: 0 warning = 100; 1 = 95; 2 = 90; từ 20 trở lên = 0. Tài liệu bắt buộc có trạng thái `FAILED` bị Step 3 chặn, không chuyển thành khoản trừ điểm.

Warning còn trong snapshot sẵn sàng sẽ làm giảm điểm và cần kiểm tra phần phân tích liên quan. Điểm không đánh giá việc tài liệu match, mức hư hỏng, nội dung LLM hay quyết định adjuster. LLM fallback tự nó không đổi điểm. Review lịch sử giữ điểm đã lưu. Đây chỉ là tín hiệu giới hạn về xử lý, không thay thế điều kiện match ở Step 3 hoặc human review.

## 6. Quyền truy cập

- `ADMIN` được dùng tất cả API cần đăng nhập, quản lý claim và cấu hình, đồng thời tạo tài khoản `USER` trong Admin Config.
- `USER` chỉ tạo và sửa Draft do mình tạo trong Claim Information và Evidence & documents. Sau khi nộp Draft đầy đủ, User xem mã hồ sơ, ngày tạo và trạng thái trong My Claims. User không được xóa hồ sơ hoặc truy cập workflow nội bộ và cấu hình.
- `ADJUSTER` xem hồ sơ khách hàng đã nộp trong work queue và chạy Analysis, AI Review, Human Review. Adjuster không được mở Draft khách hàng chưa nộp, sửa chứng cứ, tạo claim hoặc account, hay quản lý cấu hình.

## 7. Kiểm tra tự động

Kiểm tra backend, chạy từ `backend`:

```powershell
pytest
python scripts/check_health.py
python scripts/check_database.py
```

Kiểm tra frontend, chạy từ `frontend`:

```powershell
npm test
npm run build
```

`check_database.py` cần PostgreSQL truy cập được theo cấu hình `DATABASE_URL`.

## 8. Migration field tài liệu cũ

Dừng toàn bộ backend và triển khai code mới trước khi chạy migration. Kiểm tra số dòng ở từng database, sau đó dùng số lượng do `--check` trả về làm giá trị kỳ vọng:

```powershell
cd backend
python scripts/migrate_legacy_document_analysis_fields.py --check
python scripts/migrate_legacy_document_analysis_fields.py --apply --expected-legacy-rows COUNT_FROM_CHECK
python scripts/migrate_legacy_document_analysis_fields.py --check
```

Thay `COUNT_FROM_CHECK` bằng số dòng mà lệnh đầu tiên trả về cho database đó. Migration xác minh số dòng kỳ vọng rồi xóa `document_analysis_fields` trong cùng transaction PostgreSQL. Nếu có dữ liệu lịch sử, migration sao chép và xác minh dữ liệu trong `legacy_document_analysis_fields_archive` trước; bảng rỗng thì không cần archive. Ứng dụng không đọc archive; các dòng archive tự bị xóa cùng document analysis cha khi xóa claim.

Khôi phục schema cũ và các dòng archive còn lại bằng lệnh:

```powershell
python scripts/migrate_legacy_document_analysis_fields.py --rollback
```

Rollback không khôi phục được claim đã bị xóa sau migration. Ứng dụng không tự xóa bảng cũ khi khởi động hoặc chạy `create_all`.

## 9. File local và dữ liệu database

- Chứng cứ tải lên được lưu trong `UPLOAD_ROOT` (mặc định: `uploads` tại thư mục gốc repository).
- Dữ liệu PostgreSQL nằm trong Docker Compose volume `postgres-data`.
- Wheel DeepDoc là package riêng tư, cần tải riêng và không được commit.
- Không đưa `.env`, chứng cứ tải lên hoặc dữ liệu nhạy cảm khác vào source control.
