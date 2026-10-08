# AI Car Insurance Claim Assistant

Proof of concept full-stack hỗ trợ xử lý hồ sơ bảo hiểm ô tô. Điều chỉnh viên có thể xem thông tin hồ sơ, tài liệu chứng cứ, kết quả OCR và trích xuất dữ liệu, đánh giá hư hỏng xe, đề xuất của AI và quyết định kiểm duyệt của con người.

**Ngôn ngữ:** [English](README.md) | Tiếng Việt

## Chức năng

- Phân quyền theo vai trò `ADMIN` và `ADJUSTER`.
- Quản lý hồ sơ, thông tin xe, sự cố và các file chứng cứ.
- Chạy OCR và LLM để trích xuất thông tin từ giấy tờ tùy thân, hợp đồng bảo hiểm, giấy đăng ký xe và giấy phép lái xe.
- Phân tích hư hỏng xe và hiển thị kết quả đã chuẩn hóa theo từng bộ phận.
- Hỗ trợ AI Review, Human Review và cấu hình quy tắc đánh giá.
- Lưu dữ liệu ứng dụng trong PostgreSQL và lưu file tải lên trong thư mục local được cấu hình.

Đây là PoC hỗ trợ ra quyết định. Kết quả phân tích và đề xuất của AI cần được điều chỉnh viên có thẩm quyền xem xét.

## Công nghệ

- Frontend: React, TypeScript, Vite, HeroUI, Tailwind CSS, TanStack Query/Table và Recharts.
- Backend: Python, FastAPI, SQLAlchemy và Pydantic.
- Database: PostgreSQL.
- OCR tài liệu: package riêng tư `deepdoc_vietocr` (DeepDoc, VietOCR và ONNX).
- LLM: mặc định chạy mock; có thể cấu hình tích hợp OpenAI-compatible qua LangChain.

## Yêu cầu

- Python 3.10 hoặc 3.11.
- Node.js 20.19+ hoặc 22.12+.
- Docker Desktop hoặc runtime tương thích Docker Compose.
- Có quyền tải wheel riêng tư `deepdoc_vietocr` để dùng OCR tài liệu thật.
- OpenAI API key nếu sử dụng `LLM_MODE=openai`.

## Hướng dẫn cài đặt

Các lệnh dưới đây chạy từ thư mục gốc của repository, trừ khi lệnh `cd` thay đổi thư mục.

### 1. Cấu hình môi trường

```powershell
Copy-Item .env.example .env
```

File cấu hình mẫu dùng detector xe cục bộ; tìm giá phụ tùng và LLM vẫn ở chế độ mock. OCR tài liệu mặc định dùng DeepDoc. Để chạy demo tài liệu xác định hoặc test, đặt `DOCUMENT_OCR_MODE=mock` trong `.env`.

Để gọi LLM thật, cấu hình các giá trị sau trong `.env`:

```dotenv
LLM_MODE=openai
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=your-supported-model
LLM_REQUEST_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=0
```

Khi không cấu hình `LLM_BASE_URL`, ứng dụng dùng endpoint OpenAI mặc định. Chỉ cấu hình `LLM_BASE_URL` khi dùng nhà cung cấp tương thích OpenAI. Không commit API key hoặc secret khác lên Git.

Để in token usage do nhà cung cấp trả về cho document extraction, field validation và AI Review, đặt `LLM_TOKEN_USAGE_LOG_ENABLED=true`. Log gồm operation, model, số token và document type hoặc claim number liên quan; không ghi OCR text, prompt hay nội dung model trả lời. Nếu nhà cung cấp không trả metadata token, log ghi nhận trạng thái không khả dụng.

Để debug AI Review trên máy local, đặt `LLM_RAW_OUTPUT_LOG_ENABLED=true` để in JSON thô do model trả về trước khi parse và lưu vào database. Nội dung này có thể chứa thông tin hồ sơ và dữ liệu cá nhân, vì vậy nên tắt ngoài môi trường phát triển local có kiểm soát.

### 2. Khởi động PostgreSQL

```powershell
docker compose up -d postgres
```

PostgreSQL được mở tại cổng `5432`. Thông tin kết nối và credential local mặc định nằm trong `.env.example`; hãy đổi trong `.env` trước khi chạy ứng dụng nếu cần.

### 3. Cài đặt và khởi động backend

Wheel DeepDoc là package riêng tư và không được lưu trong Git. Tải `deepdoc_vietocr-0.1.0-py3-none-any.whl` từ [Google Drive](https://drive.google.com/file/d/1LBGigUwhSzncbh4uMpkq5kZzU1JETlQz/view?usp=sharing), rồi đặt tại `backend/package/deepdoc_vietocr-0.1.0-py3-none-any.whl` trước khi cài requirements.

Backend cũng cài các dependency của detector từ `AI/requirements.txt`. Giữ model weights ở `AI/models/car_part.pt` và `AI/models/car_damage.pt`, hoặc cấu hình lại đường dẫn trong `.env`.

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --reload-dir app
```

Nếu PowerShell chặn kích hoạt virtual environment, dùng lệnh kích hoạt phù hợp với shell đang sử dụng hoặc gọi trực tiếp `.venv\Scripts\python.exe`.

Khi khởi động, API tạo các bảng còn thiếu và tạo tài khoản demo cùng danh sách hãng xe nếu chưa có. Tài khoản hiện hữu không tự đổi mật khẩu khi cập nhật biến môi trường. Hãy cấu hình credential trước lần chạy đầu tiên. Để đổi mật khẩu tài khoản đã tồn tại, cần dùng quy trình quản trị tài khoản hoặc database được phê duyệt.

Tài khoản demo trong cấu hình mẫu:

| Vai trò | Email | Mật khẩu |
| --- | --- | --- |
| Admin | `admin@example.com` | `Admin123!` |
| Adjuster | `adjuster@example.com` | `Adjuster123!` |

Đặt `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADJUSTER_EMAIL` và `ADJUSTER_PASSWORD` trong `.env` trước lần khởi động đầu tiên để dùng credential khác.

Backend chạy tại `http://localhost:8000`:

- Health check: `GET /api/health`
- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI schema: `/openapi.json`

### 4. Cài đặt và khởi động frontend

Mở terminal khác tại thư mục gốc:

```powershell
cd frontend
npm install
npm run dev
```

Mở `http://localhost:5173`.

## Chế độ chạy

| Cấu hình | Giá trị hỗ trợ | Mặc định | Mục đích |
| --- | --- | --- | --- |
| `DAMAGE_MODEL_MODE` | `local` | `local` | Chạy `AI/CarDamageDetector` với model weights cục bộ. |
| `PART_SEARCH_MODE` | `mock`, `unavailable` | `mock` | Giá phụ tùng demo hoặc không trả kết quả tìm giá. |
| `DOCUMENT_OCR_MODE` | `deepdoc`, `mock` | `deepdoc` | OCR DeepDoc hoặc OCR demo xác định. |
| `LLM_MODE` | `mock`, `openai` | `mock` | Response demo hoặc gọi chat model tương thích OpenAI qua LangChain. |

Với chế độ `openai`, cần đặt `OPENAI_API_KEY` và `OPENAI_MODEL`. Model được chọn cần hỗ trợ structured output theo yêu cầu của ứng dụng. Khả năng truy cập và cách phản hồi có thể khác nhau giữa các nhà cung cấp/model.

Detector xử lý từng ảnh xe đã upload và lưu ảnh kết quả vào `UPLOAD_ROOT/<claim>/annotations/`. Có thể cấu hình `DAMAGE_PART_MODEL_PATH`, `DAMAGE_MODEL_PATH`, `DAMAGE_OUTPUT_DIR`, `DAMAGE_PART_CONF`, `DAMAGE_DAMAGE_CONF`, `DAMAGE_MIN_PERCENT`, `DAMAGE_IMAGE_SIZE`, và `DAMAGE_DEVICE` trong `.env`. Đường dẫn mặc định tính từ thư mục gốc dự án. Chạy thử độc lập bằng `python backend/scripts/test_car_damage_detector.py`.

## Cách tính điểm hoàn thiện phân tích ở Step 4

Step 4 chỉ chạy sau khi Step 3 lưu được analysis snapshot ở trạng thái sẵn sàng. Step 3 chặn **Save All** nếu phân tích tài liệu bắt buộc bị lỗi, thiếu giá trị bắt buộc, hoặc giá trị có thể đối chiếu đang `MISMATCH` hay không thể kiểm tra. Cần sửa dữ liệu và hoàn thành lại Step 3 trước khi chạy AI Review. Vì vậy, mismatch là điều kiện chặn chứ không phải khoản trừ điểm: Step 4 không nên chạy khi còn mismatch.

**Analysis completeness score** ở Step 4 là chỉ số xử lý được tính theo quy tắc cố định. Điểm này không do LLM tạo ra và không phải xác suất claim hợp lệ hay được duyệt. Mỗi review đủ điều kiện bắt đầu từ 100 điểm và trừ 5 điểm cho mỗi warning trong analysis snapshot đã lưu. Kết quả không thể thấp hơn 0:

```text
điểm = max(0, 100 - (số warning × 5))
```

Ví dụ: không có warning = 100 điểm; 1 warning = 95 điểm; 2 warning = 90 điểm; từ 20 warning trở lên = 0 điểm. Tài liệu bắt buộc có trạng thái `FAILED` không bị quy đổi thành khoản trừ điểm vì Step 3 chặn workflow trước khi điểm được tạo.

Warning còn lại trong snapshot đã sẵn sàng làm giảm điểm; hãy kiểm tra phần phân tích liên quan khi có warning. Điểm này không trực tiếp đánh giá các field trên giấy tờ match hay không, mức độ hư hại, nội dung review của LLM hay quyết định của adjuster. LLM tạo phần review riêng; việc LLM chạy fallback tự nó không làm thay đổi điểm. Các review lịch sử vẫn giữ nguyên điểm đã lưu. Đây chỉ là tín hiệu giới hạn về quá trình xử lý tài liệu, cần adjuster xem xét và không thay thế điều kiện match ở Step 3.

## Quyền truy cập

- `ADMIN` được dùng tất cả API cần đăng nhập, quản lý hồ sơ và cấu hình, đồng thời có thể tạo tài khoản.
- `ADJUSTER` được chạy Analysis, AI Review và Human Review. Adjuster cũng có thể đọc chi tiết hồ sơ và chứng cứ cần thiết cho các bước này; tạo/liệt kê hồ sơ, thay đổi chứng cứ, quản lý tài khoản và cấu hình chỉ dành cho admin.

## Package DeepDoc

Package riêng tư `deepdoc_vietocr` hỗ trợ OCR tối ưu cho CPU, nhận dạng bố cục tài liệu và trích xuất cấu trúc bảng, có tích hợp VietOCR và ONNX để nhận dạng tiếng Việt. Wheel không nằm trong Git. Tải từ [đường dẫn package của dự án](https://drive.google.com/file/d/1LBGigUwhSzncbh4uMpkq5kZzU1JETlQz/view?usp=sharing) và đặt vào `backend/package/` trước khi cài requirements backend.

Ví dụ sử dụng:

```python
from deepdoc_vietocr import DocumentReader

reader = DocumentReader()
result = reader.extract("sample.pdf")

print(result.text)
print(result.markdown)

layouts = reader.detect_layout("sample.pdf")
tables = reader.extract_tables("sample.pdf")
```

Xem [`backend/package/THIRD_PARTY_NOTICES.md`](backend/package/THIRD_PARTY_NOTICES.md) để biết thông tin tải package và thông báo bản quyền bên thứ ba.

## Kiểm tra tự động

Kiểm tra backend:

```powershell
cd backend
pytest
python scripts/check_health.py
python scripts/check_database.py
```

Kiểm tra frontend:

```powershell
cd frontend
npm test
npm run build
```

`check_database.py` cần PostgreSQL truy cập được theo cấu hình `DATABASE_URL`.

## File và dữ liệu local

- Chứng cứ tải lên được lưu trong `UPLOAD_ROOT` (mặc định: `uploads` tại thư mục gốc repository).
- Dữ liệu PostgreSQL được lưu trong Docker Compose volume `postgres-data`.
- Wheel DeepDoc là riêng tư, cần tải riêng và không được commit.
- Không đưa `.env`, chứng cứ tải lên hoặc dữ liệu nhạy cảm khác vào source control.

## Bản quyền bên thứ ba

Xem [`backend/package/THIRD_PARTY_NOTICES.md`](backend/package/THIRD_PARTY_NOTICES.md) để biết thông tin ghi nhận tác giả và license của DeepDoc/RAGFlow, VietOCR và package riêng tư.
