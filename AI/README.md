# 🚗 AI Car Damage & Part Detection Module

Mô-đun AI đóng vai trò cốt lõi trong hệ thống **AI Car Insurance Claim Assistant**, chịu trách nhiệm tự động phát hiện, phân đoạn (Instance Segmentation) các bộ phận xe ô tô và phân tích thiệt hại thực tế từ hình ảnh hiện trường để hỗ trợ giám định viên tính toán chi phí bồi thường.

---

## 📌 Tính năng chính

- **Mô hình kép (Dual YOLO Segmentation)**:
  - Nhận diện phân đoạn **21 bộ phận xe ô tô** (`car_part.pt`).
  - Nhận diện phân đoạn **7 loại tổn thất/hư hại xe** (`car_damage.pt`).
- **Tính toán tỷ lệ phần trăm thiệt hại (Damage Percentage)**:
  - Phân tích diện tích giao thoa pixel (Mask Intersection) giữa vùng hư hỏng và từng bộ phận tương ứng:
    $$\text{Tỷ lệ hư hại (\%)} = \frac{\text{Diện tích giao thoa (Damage} \cap \text{Part)}}{\text{Tổng diện tích bộ phận (Part)}} \times 100$$
- **Phân tách chi tiết loại hư hại (Damage Types Breakdown)**:
  - Liệt kê các loại hư hỏng trên từng bộ phận kèm tỷ lệ cụ thể.
  - Tự động xác định loại hư hỏng nghiêm trọng/chính nhất (`main_damage`).
- **Lọc nhiễu & Hư hại nhỏ (`min_damage_percent`)**:
  - Bỏ qua các vết xước hoặc hư hại không đáng kể (mặc định `< 3.0%`).
- **Trực quan hóa nâng cao (HUD Visualization)**:
  - Phủ màu bán trong suốt (semi-transparent overlay) phân biệt từng bộ phận.
  - Phủ mặt nạ đỏ và vẽ viền contour cho vùng hư hỏng.
  - Tự động scale cỡ chữ theo độ phân giải ảnh, gắn bảng thông số (badge) kèm đường chỉ tâm (leader line) trỏ trực tiếp vào bộ phận bị thiệt hại.

---

## 📂 Cấu trúc thư mục

```text
AI/
├── models/
│   ├── car_part.pt           # Model YOLO nhận diện 21 bộ phận xe
│   └── car_damage.pt         # Model YOLO nhận diện 7 loại hư hỏng
├── images/                   # Thư mục đặt ảnh đầu vào cần phân tích
├── outputs/                  # Thư mục xuất ảnh kết quả (đã vẽ mask & nhãn)
├── car_damage_detector.py    # Class CarDamageDetector xử lý thuật toán chính
├── main.py                   # Script chạy thử nghiệm / Demo
├── requirements.txt          # Danh sách thư viện Python cần thiết
└── README.md                 # Tài liệu hướng dẫn mô-đun AI
```

---

## 🏷️ Danh mục nhãn nhận diện (Classes)

### 1. 21 Bộ phận xe (`car_part.pt`)
| ID | Tên bộ phận | Mô tả tiếng Việt | ID | Tên bộ phận | Mô tả tiếng Việt |
|:--:|:---|:---|:--:|:---|:---|
| **0** | `Quarter-panel` | Tấm ốp hông sau xe | **11** | `Back-wheel` | Bánh sau |
| **1** | `Front-wheel` | Bánh trước | **12** | `Back-windshield`| Kính chắn gió sau |
| **2** | `Back-window` | Cửa sổ kính sau | **13** | `Hood` | Nắp capo trước |
| **3** | `Trunk` | Cốp xe sau | **14** | `Fender` | Ốp chắn bùn (tai xe) |
| **4** | `Front-door` | Cửa trước | **15** | `Tail-light` | Đèn hậu sau |
| **5** | `Rocker-panel` | Bệ bước / gầm viền sườn | **16** | `License-plate` | Biển số xe |
| **6** | `Grille` | Lưới tản nhiệt | **17** | `Front-bumper` | Cản trước (Ba-đờ-sốc trước) |
| **7** | `Windshield` | Kính chắn gió trước | **18** | `Back-bumper` | Cản sau (Ba-đờ-sốc sau) |
| **8** | `Front-window` | Cửa sổ kính trước | **19** | `Mirror` | Gương chiếu hậu |
| **9** | `Back-door` | Cửa sau | **20** | `Roof` | Mui xe / nóc xe |
| **10**| `Headlight` | Đèn pha trước | | | |

### 2. 7 Dạng hư hại (`car_damage.pt`)
| ID | Tên hư hại | Mô tả |
|:--:|:---|:---|
| **0** | `corrosion` | Rỉ sét / Ăn mòn kim loại |
| **1** | `crack` | Vết nứt vỡ |
| **2** | `dent` | Vết móp / Lõm kim loại |
| **3** | `glass shatter` | Vỡ kính rạn nứt |
| **4** | `lamp broken` | Bể / Vỡ đèn xe |
| **5** | `scratch` | Vết cào / Trầy xước sơn |
| **6** | `tire flat` | Xẹp lốp / Thủng lốp |

---

## 🛠️ Cài đặt & Chuẩn bị môi trường

### Yêu cầu
- **Python**: 3.10 trở lên
- **Hệ điều hành**: Windows / Linux / macOS
- **Phần cứng**: Hỗ trợ chạy trên cả CPU (`device="cpu"`) hoặc GPU NVIDIA CUDA (`device="0"`).

### 1. Tạo và kích hoạt môi trường ảo (Virtual Environment)

```bash
# Điều hướng vào thư mục AI
cd AI

# Tạo virtual environment
python -m venv .venv

# Kích hoạt trên Windows (PowerShell/CMD):
.venv\Scripts\activate

# Hoặc kích hoạt trên Linux/macOS:
source .venv/bin/activate
```

### 2. Cài đặt các thư viện cần thiết

```bash
pip install -r requirements.txt
```

> **Lưu ý với GPU (NVIDIA CUDA):** Nếu muốn tăng tốc suy luận trên GPU, hãy cài bản PyTorch tương thích CUDA từ [pytorch.org](https://pytorch.org/get-started/locally/).

---

## 🚀 Hướng dẫn sử dụng

### 1. Chạy nhanh qua script `main.py`

Đặt ảnh xe cần đánh giá vào thư mục `AI/images/` (ví dụ: `AI/images/sample_car.jpg`), sau đó sửa đường dẫn trong `main.py` và chạy:

```bash
python main.py
```

### 2. Sử dụng trực tiếp trong code Python

```python
from car_damage_detector import CarDamageDetector

# 1. Khởi tạo detector
detector = CarDamageDetector(
    part_model_path="models/car_part.pt",
    damage_model_path="models/car_damage.pt",
    output_dir="outputs",
    part_conf=0.25,             # Ngưỡng tin cậy nhận diện bộ phận
    damage_conf=0.15,           # Ngưỡng tin cậy nhận diện hư hại
    min_damage_percent=3.0,     # Bỏ qua hư hại < 3%
    imgsz=640,                  # Kích thước ảnh resize suy luận YOLO
    device="cpu"                # "cpu" hoặc "0" (GPU)
)

# 2. Thực hiện dự đoán
annotated_image, final_result = detector.predict("images/car_incident.jpg")

# 3. Kết quả phân tích dạng cấu trúc
for item in final_result:
    print(f"Bộ phận: {item['part']}")
    print(f" - Thiệt hại chính: {item['main_damage']}")
    print(f" - Tổng mức hư hại: {item['damage_percent']}%")
    print(f" - Chi tiết các vết hư hại: {item['damage_types']}")
```

---

## ⚙️ Các tham số cấu hình (`CarDamageDetector`)

| Tham số | Kiểu dữ liệu | Mặc định | Mô tả |
|:---|:---:|:---:|:---|
| `part_model_path` | `str` | *Bắt buộc* | Đường dẫn tới file trọng số mô hình bộ phận xe (`car_part.pt`). |
| `damage_model_path` | `str` | *Bắt buộc* | Đường dẫn tới file trọng số mô hình hư hại xe (`car_damage.pt`). |
| `output_dir` | `str` | `"output"` | Thư mục lưu ảnh phân tích kết quả sau khi vẽ mask và nhãn. |
| `part_conf` | `float` | `0.25` | Ngưỡng tự tin (confidence threshold) tối thiểu để nhận diện bộ phận. |
| `damage_conf` | `float` | `0.20` | Ngưỡng tự tin tối thiểu để nhận diện vết hư hại. |
| `min_damage_percent` | `float` | `3.0` | Ngưỡng phần trăm tổn thất tối thiểu (%) trên bộ phận để được ghi nhận vào báo cáo. |
| `imgsz` | `int` | `640` | Kích thước ảnh đầu vào khi đưa qua mô hình YOLOv8. |
| `device` | `str` | `"cpu"` | Thiết bị tính toán: `"cpu"` cho vi xử lý thông thường hoặc `"0"`, `"cuda"` nếu có GPU. |

---

## 📊 Định dạng dữ liệu đầu ra (Output Schema)

Hàm `detector.predict(...)` trả về 2 giá trị:
1. `annotated_image`: Ma trận ảnh OpenCV (`numpy.ndarray`) với đầy đủ mặt nạ trực quan, contour và nhãn HUD. Ảnh này cũng được tự động lưu vào `output_dir/<tên_gốc>_result.jpg`.
2. `final_result`: Danh sách `list[dict]` chứa chi tiết tổn thất, sắp xếp giảm dần theo mức độ thiệt hại:

```json
[
  {
    "part": "Front-door",
    "main_damage": "dent",
    "damage_percent": 24.85,
    "damage_types": [
      {
        "type": "dent",
        "percent": 18.20
      },
      {
        "type": "scratch",
        "percent": 6.65
      }
    ]
  },
  {
    "part": "Fender",
    "main_damage": "scratch",
    "damage_percent": 8.40,
    "damage_types": [
      {
        "type": "scratch",
        "percent": 8.40
      }
    ]
  }
]
```

---

## 🔗 Liên kết hệ thống (System Architecture)

Module này được thiết kế theo dạng độc lập, có thể dễ dàng:
- Đóng gói thành Microservice (FastAPI REST service) để kết nối với `backend/app/services/damage_model.py` qua cấu hình `DAMAGE_MODEL_MODE=http` và `DAMAGE_MODEL_URL`.
- Tích hợp trực tiếp vào quy trình giám định bồi thường xe cơ giới tự động, giúp đối chiếu tổn thất thực tế với chi phí phụ tùng (`part_search`) và điều khoản hợp đồng bảo hiểm (`insurance_policy`).
