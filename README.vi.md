# AI Car Insurance Claim Assistant

Proof of concept full-stack hỗ trợ xử lý hồ sơ bảo hiểm ô tô, từ tiếp nhận hồ sơ và tải chứng cứ đến trích xuất tài liệu, phân tích hư hỏng xe, hỗ trợ bằng AI và kiểm duyệt của con người.

**Ngôn ngữ:** [English](README.md) | Tiếng Việt

## Tổng quan

- Quy trình theo vai trò `ADMIN`, `ADJUSTER` và khách hàng `USER`.
- Frontend dùng React, TypeScript, Vite, HeroUI và Tailwind CSS.
- Backend dùng FastAPI, PostgreSQL và lưu chứng cứ trên máy chủ.
- OCR tài liệu bằng DeepDoc, nhận diện hư hỏng xe và tích hợp LangChain/OpenAI tùy chọn.
- AI hỗ trợ tham khảo; điều chỉnh viên có thẩm quyền đưa ra quyết định cuối cùng.

## Yêu cầu

- Python 3.10 hoặc 3.11
- Node.js 20.19+ hoặc 22.12+
- Docker Desktop hoặc runtime tương thích Docker Compose
- Wheel riêng tư `deepdoc_vietocr` và model weights nhận diện hư hỏng xe để dùng các tích hợp AI cục bộ

## Khởi động local trên một port

Chạy lệnh từ thư mục gốc repository, trừ khi lệnh `cd` thay đổi thư mục.

Build frontend một lần. FastAPI sẽ phục vụ giao diện đã build và `/api` cùng một origin, nên khi sử dụng thông thường chỉ cần chạy backend. Khởi động PostgreSQL. Trước khi cài requirements backend, tải wheel riêng tư từ [đường dẫn tải package](https://drive.google.com/file/d/1LBGigUwhSzncbh4uMpkq5kZzU1JETlQz/view?usp=sharing) và đặt tại `backend/package/deepdoc_vietocr-0.1.0-py3-none-any.whl`. Thêm model weights nhận diện hư hỏng xe vào `AI/models/` nếu dùng chức năng phân tích hư hỏng.

```powershell
Copy-Item .env.example .env
docker compose up -d postgres

# Tải wheel riêng tư và đặt tại:
# backend/package/deepdoc_vietocr-0.1.0-py3-none-any.whl

Push-Location frontend
npm ci
npm run build
Pop-Location

Push-Location backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --reload-dir app
```

Mở `http://localhost:8000` để dùng giao diện và API. Swagger ở `http://localhost:8000/docs`. Uvicorn mặc định dùng port `8000`; truyền `--port <port>` nếu cần port khác. Khi chạy Docker Compose, `APP_PORT` (mặc định `8000`) chọn host port. Chỉ dùng `npm run dev` khi đang phát triển frontend và cần Vite tự reload.

### Triển khai bằng Docker

Docker image tự build frontend và để FastAPI phục vụ giao diện. Trước khi build, tải wheel DeepDoc riêng tư vào `backend/package/deepdoc_vietocr-0.1.0-py3-none-any.whl` từ [đường dẫn tải package](https://drive.google.com/file/d/1LBGigUwhSzncbh4uMpkq5kZzU1JETlQz/view?usp=sharing).

```powershell
Copy-Item .env.example .env
docker compose up --build -d
```

Mở `http://localhost:8000`. Đặt `APP_PORT` trong `.env` để publish một host port khác. PostgreSQL cũng mở port `5432` để dùng công cụ quản trị database. Chạy `docker compose down` để dừng service mà vẫn giữ dữ liệu database và file upload.

### Chạy Frontend riêng bằng Vite

Để frontend tự reload khi sửa code, chạy `npm run dev` trong `frontend/` và chạy backend riêng. Vite ở `http://localhost:5173` và dùng `FRONTEND_ORIGIN` trong `.env` để gọi API.

Cấu hình credential tài khoản demo trong `.env` trước lần khởi động backend đầu tiên. Xem [Hướng dẫn dự án](backend/package/PROJECT_GUIDE.vi.md) để biết thêm về cấu hình, chế độ chạy, workflow, giá, phân quyền, migration và kiểm tra. Xem [Thông báo bên thứ ba](backend/package/THIRD_PARTY_NOTICES.md) để biết cách tải package và thông tin license.

## Tài liệu

- [Hướng dẫn dự án: cấu hình, workflow, giá, phân quyền, migration và kiểm tra](backend/package/PROJECT_GUIDE.md)
- [Thông báo bên thứ ba và tải package riêng OCR](backend/package/THIRD_PARTY_NOTICES.md)
