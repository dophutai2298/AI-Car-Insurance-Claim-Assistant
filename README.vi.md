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

Khi `DATABASE_MIGRATE_ON_STARTUP=true`, API chạy Alembic migration rồi tạo tài khoản demo và danh sách hãng xe nếu chưa có. Ứng dụng không dùng SQLAlchemy `create_all` thay cho migration. Database development cũ chưa có Alembic sẽ được đánh dấu tại baseline và nâng cấp tự động; hãy sao lưu trước khi nâng cấp dữ liệu dùng chung. Tài khoản hiện hữu không tự đổi mật khẩu khi cập nhật biến môi trường.

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

### 3.1 Chạy migration và workflow worker

Mọi thay đổi schema được quản lý bằng Alembic:

```powershell
cd backend
alembic upgrade head
alembic current
alembic downgrade -1
```

Analysis và AI Review được lưu thành job trong PostgreSQL và xử lý ngoài API process. Giữ lệnh sau chạy ở một terminal riêng:

```powershell
cd backend
python -m app.worker
```

`WORKFLOW_WORKER_EAGER=true` chỉ dành cho test xác định. Khi development hoặc deploy bình thường, worker cần chạy riêng để job tồn tại qua các lần API reload hoặc restart.

Để chạy PostgreSQL, migration, API và worker bằng các container riêng:

```powershell
docker compose up --build
```

Wheel DeepDoc riêng tư phải có trong `backend/package/` trước khi build image.

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

## Quyền truy cập

- `ADMIN` được dùng tất cả API cần đăng nhập, quản lý hồ sơ và cấu hình, đồng thời có thể tạo tài khoản.
- `ADJUSTER` chỉ được chạy Analysis, AI Review và Human Review trên hồ sơ được gán trực tiếp cho tài khoản đó. Adjuster cũng có thể đọc chi tiết và chứng cứ của các hồ sơ được gán; tạo/liệt kê hồ sơ, gán hồ sơ, thay đổi chứng cứ, quản lý tài khoản và cấu hình chỉ dành cho admin.

Trong migration của Task 23, hồ sơ cũ chưa được gán sẽ được gán cho tài khoản `ADJUSTER` đang active có ID nhỏ nhất nếu tài khoản đó tồn tại. Hồ sơ mới mặc định dùng adjuster đang active đầu tiên; admin có thể đổi người phụ trách qua `PATCH /api/claims/{claim_number}/assignment`. Hồ sơ còn chưa được gán chỉ admin mới xem được.

Access token có thời hạn ngắn. `POST /api/auth/refresh` xoay vòng refresh token dạng opaque được lưu hash trong database, còn `POST /api/auth/logout` thu hồi cả token family. Đổi mật khẩu hoặc vô hiệu hóa tài khoản sẽ làm mất hiệu lực session đang hoạt động. Login, refresh và MFA challenge dùng rate limit chung được lưu trong database. TOTP secret của MFA được mã hóa và recovery code chỉ trả về một lần.

Các collection API dùng thứ tự ổn định cùng tham số `page`/`page_size` có giới hạn. Metadata phân trang nằm trong các response header `X-Page`, `X-Page-Size`, `X-Total-Count` và `X-Total-Pages`.

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
