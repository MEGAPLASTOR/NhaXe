# Quản Lý Nhà Xe — VIDATEX JSC

Phần mềm ghi nhận xe vào / ra bằng 2 camera Imou (cổng vào, cổng ra) và thẻ giữ xe đánh số.

## Cách chạy

| Cách | Làm gì |
|---|---|
| `run.bat` | Nhấp đúp để chạy. Lần đầu tự cài Python và thư viện (cần Internet). |
| `tao_shortcut.bat` | Tạo biểu tượng **Quan ly nha xe** (logo VIDATEX) ngoài Desktop, mở không hiện cửa sổ đen. Chạy `run.bat` ít nhất 1 lần trước. |

### Chép sang máy khác
Chép cả thư mục `NhaXe` rồi chạy `run.bat`. Máy chưa có Python thì nó tự tải và cài (cần Internet, khoảng 26 MB).

Thư mục `.venv` chỉ chạy được trên máy đã tạo ra nó, chép sang máy khác là hỏng — `run.bat` tự nhận ra và dựng lại,
nên **không cần** chép `.venv`. Bỏ nó ra cho nhẹ (khoảng 200 MB).
Muốn chuyển luôn dữ liệu cũ thì chép kèm thư mục `data` và file `config.ini`.

## Sử dụng

| Phím (mặc định) | Chức năng |
|---|---|
| **Shift trái** | Xe vào: chụp ảnh camera cổng vào → nhập số thẻ → Enter |
| **Enter** / **Shift phải** | Xe ra: chụp ảnh camera cổng ra → nhập số thẻ (hiện giờ vào + tiền gửi) → Enter |
| **F3** | Danh sách xe đang gửi |
| **F4** | Lịch sử gửi xe (tìm theo số thẻ, ngày, xuất Excel) — tab **Theo từng ngày** xem xe trong bãi từng ngày |
| **Ctrl + Delete** | Reset dữ liệu: nhập mật khẩu, gõ `XOA` để xác nhận (mặc định sao lưu vào `data/sao_luu`) |
| **Esc** | Hủy / đóng |

Nút **⚙ Cài đặt** cần mật khẩu quản lý (mặc định `Nha@123`, đổi bằng nút **Đổi mật khẩu** trong Cài đặt).
Trong đó: đổi phím, nhập IP / mật khẩu camera, **giá gửi xe**, số ngày giữ ảnh.

### Tính tiền gửi xe
Có 2 khung giờ, mỗi khung có giờ bắt đầu, giờ kết thúc và giá 1 lượt (mặc định Ban ngày 06:00–18:00, Ban đêm 18:00–06:00).
Xe chạm khung nào thì tính tiền khung đó, gửi qua nhiều khung hoặc qua ngày hôm sau thì **cộng dồn**:
vào 17:00 ra 07:00 hôm sau = Ngày + Đêm + Ngày. Tiền được chốt lúc xe ra; đổi bảng giá sau không ảnh hưởng lượt đã ra.

### Lịch sử theo từng ngày
Chọn 1 ngày để xem mọi xe có mặt trong bãi ngày đó: xe vào, xe ra, và xe gửi từ hôm trước sang.
Xe còn đang gửi hiện ở mọi ngày cho đến hôm nay; xe đã ra chỉ hiện đến ngày ra, các ngày sau không còn.

## Thư mục

```
NhaXe/
├── run.bat               chạy chương trình
├── tao_shortcut.bat      tạo shortcut ngoài Desktop
├── config.ini            cài đặt (camera, phím tắt, lưu trữ) — sửa trong nút Cài đặt
├── requirements.txt      thư viện Python cần cài
├── assets/               logo, biểu tượng công ty
├── app/                  mã nguồn
│   ├── core/             camera, lưu trữ dữ liệu, phím tắt, cài đặt
│   └── ui/               giao diện: màn hình chính, nhập thẻ, tra cứu, cài đặt
└── data/                 dữ liệu (tự tạo khi chạy)
    ├── nhaxe.db          thông tin các lượt gửi xe
    ├── anh/<ngày>/       ảnh xe: SốThẻ_ngày_giờ_IN/OUT.jpg, ví dụ 111_28-10-2026_21h44m35_IN.jpg
    ├── xuat_file/        file Excel (CSV) đã xuất
    ├── sao_luu/          bản sao lưu tự tạo mỗi lần reset dữ liệu
    └── loi.log           nhật ký lỗi (nếu có)
```

Ảnh tự xóa sau số ngày cài đặt (mặc định 30 ngày); ảnh của xe còn đang gửi luôn được giữ lại.
Sao lưu dữ liệu: chép cả thư mục `data`.
