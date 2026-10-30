# Quản Lý Nhà Xe — VIDATEX JSC

Phần mềm ghi nhận xe vào / ra bằng 2 camera Imou (cổng vào, cổng ra) và thẻ giữ xe đánh số.

## Cách chạy

**Giao cho khách file `CaiDat_QuanLyNhaXe.exe`** — chạy là cài, không cần Python hay thư viện gì.

| File | Làm gì |
|---|---|
| `ban_phat_hanh\CaiDat_QuanLyNhaXe.exe` | **Bộ cài đặt** — đưa cho khách file này |
| `ban_phat_hanh\QuanLyNhaXe.exe` | Bản chạy thẳng, không cài (chép vào USB mang đi) |
| `run.bat` | Chạy từ mã nguồn (để sửa code). Lần đầu tự cài Python và thư viện. |
| `dong_goi.bat` | Đóng gói lại cả 2 file trên sau khi sửa code |
| `tao_shortcut.bat` | Tạo shortcut cho bản chạy từ mã nguồn |

### Bộ cài đặt
Chạy `CaiDat_QuanLyNhaXe.exe`, các bước:

1. **Chọn thư mục cài** — mặc định `C:\QuanLyNhaXe`, bấm **Chọn...** để đổi.
   Có ô tích tạo biểu tượng ngoài Desktop.
2. **Đang cài** — chép chương trình, tạo shortcut Start Menu và Desktop,
   ghi vào **Apps & features** của Windows để gỡ được như phần mềm bình thường.
3. **Hoàn tất** — 2 ô tích: *Chạy ngay bây giờ* và *Xem thông tin người tạo phần mềm*.

Không cần quyền Administrator. Cài đặt và dữ liệu nằm trong thư mục cài, nên **đừng chọn
`C:\Program Files`** (Windows chặn ghi dữ liệu vào đó).

### Gỡ cài đặt
Settings → Apps → **Quản Lý Nhà Xe** → Uninstall, hoặc chạy `GoCaiDat.exe` trong thư mục cài.
Mặc định **giữ lại** thư mục `data` và `config.ini`; muốn xóa sạch thì tích ô trong cửa sổ gỡ.

Cả bộ cài và chương trình đều có logo VIDATEX, tên và thông tin công ty
(chuột phải → Properties → Details).

### Kết nối camera
Lần đầu chạy, nếu chưa cấu hình camera, phần mềm **tự dò cả dải mạng** và hiện danh sách camera tìm được
(thiết bị nào mở cổng 554 thì là camera). Hai camera đầu được gán sẵn cổng vào / cổng ra, bạn chỉ cần nhập
**Safety Code** in trên tem dán dưới đáy mỗi camera rồi bấm **Kiểm tra và lưu**.

Mã này không dò tự động được — nó chỉ in trên thân máy, không có trong vỏ hộp và không suy ra được từ S/N.

Khi kiểm tra, phần mềm hỏi thẳng camera bằng giao thức RTSP nên báo đúng việc cần sửa:

| Báo lỗi | Phải làm gì |
|---|---|
| Sai Safety Code | Xem lại tem dán dưới đáy camera, phân biệt chữ hoa / thường |
| Camera không hỗ trợ RTSP / không có đường dẫn này | Mở app Imou Life → camera → ⚙ Cài đặt → bật **RTSP** |
| Camera không trả lời | Camera mất điện, hoặc không cùng mạng với máy tính |
| Camera đã hết chỗ cho máy xem | Thoát app Imou Life trên điện thoại rồi thử lại |

Phần mềm tự thử nhiều kiểu địa chỉ RTSP khác nhau và lưu lại kiểu chạy được, nên không phải tra đời camera.
Mở lại cửa sổ này bất cứ lúc nào bằng **⚙ Cài đặt → Camera → Tự tìm camera trong mạng**.

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
| **F11** | Thu nhỏ cửa sổ / trở lại toàn màn hình (không cần mật khẩu) |
| **Esc** | Hủy / đóng |

Phần mềm luôn mở **toàn màn hình**, che cả thanh tác vụ. `Esc` và `F11` không gán lại được.

### Khóa màn hình
Nút **🔒** trên thanh đầu (cạnh nút Cài đặt) khóa màn hình giống nút ổ khóa của Zalo: phủ kín cửa sổ,
mọi phím tắt ngừng ăn, phải nhập **mật khẩu quản lý** mới dùng tiếp. Dùng khi người giữ xe rời chỗ.

**Bấm vào ảnh** xe vào / xe ra ở màn hình chính hoặc trong Tra cứu là ảnh phóng to hết cỡ màn hình,
kèm nút mở bằng trình xem ảnh của Windows.

Xe đang gửi có nút **↑ Cho xe này ra** — bấm là mở luôn cửa sổ xe ra với **số thẻ điền sẵn**,
chỉ việc nhấn Enter. Nút này có ở hai chỗ:

- Khung **Lượt vừa ghi nhận** ở màn hình chính
- Tab **Xe đang gửi** (F3): chọn một xe trong bảng, nút nằm ở khung chi tiết bên phải.
  Bấm xong cửa sổ tra cứu tự đóng để nhường chỗ cho cửa sổ xe ra.

Xe đã ra rồi thì không có nút này; thay vào đó lượt vừa cho ra có nút **↶ Hoàn tác lượt ra**.

**Số thẻ chỉ nhập được chữ số** (tối đa 20 chữ số). Gõ chữ hay ký tự lạ thì ô nhập không nhận,
nên không sợ ghi nhầm thẻ. Các ô tìm kiếm theo số thẻ cũng vậy.

Nút **⚙ Cài đặt** cần mật khẩu quản lý (mặc định `Nha@123`, đổi bằng nút **Đổi mật khẩu** trong Cài đặt).
Trong đó: đổi phím, nhập IP / mật khẩu camera, **giá gửi xe**, **giọng nói**, số ngày giữ ảnh.

### Giọng nói
Xe vào máy đọc **“Xin mời vào”**, xe ra đọc tiền gửi của lượt đó kèm **“Hẹn gặp lại”**
(mặc định: “Phí gửi xe {tien}. Hẹn gặp lại” → “Phí gửi xe mười nghìn đồng. Hẹn gặp lại”).
Sửa câu đọc, chọn giọng, âm lượng, bật / tắt trong **⚙ Cài đặt → Giọng nói**, có nút **▶ Nghe thử**.
Trong câu dùng được `{tien}` (tiền gửi, đọc thành chữ), `{the}` (số thẻ), `{thoi_gian}` (thời gian đã gửi).

Có 3 nguồn giọng Tiếng Việt, chọn trong ô **Giọng đọc** (mặc định **Tự động**):

| Giọng | Cần mạng | Ghi chú |
|---|---|---|
| **Edge** – HoaiMy (nữ) / NamMinh (nam) | Có | Giọng tự nhiên nhất (thư viện `edge-tts`, dịch vụ không chính thức của Microsoft) |
| **Piper** | Không | Chạy trong máy, nằm ở thư mục `giong_doc` (~100 MB), giọng rõ nhưng hơi máy |
| **Windows** – Microsoft An | Không | Chỉ có khi Windows cài được gói giọng Tiếng Việt (nút **⬇ Cài giọng Tiếng Việt**) |

**Tự động** = có mạng dùng Edge, mất mạng dùng Piper. Edge tạo một câu mất vài giây nên câu đã đọc được lưu
vào `data/am_thanh` và lần sau phát ngay. Lúc mở chương trình máy tạo sẵn câu chào và câu báo các mức tiền hay gặp.
Câu chưa có sẵn (vd. vừa đổi lời) thì Piper đọc trước, giọng Edge tải ngầm cho những lần sau.
Không có giọng Tiếng Việt nào thì máy im lặng (giọng tiếng Anh đọc tiếng Việt nghe không hiểu được).

Chép sang máy khác / bản `QuanLyNhaXe.exe` chạy trực tiếp: nhớ chép kèm thư mục `giong_doc` cạnh file exe
(bộ cài `CaiDat_QuanLyNhaXe.exe` tự chép sẵn).

Thư mục `giong_doc` không nằm trong git (quá nặng). Máy mới muốn đóng gói thì tải về:
- [piper_windows_amd64.zip](https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip) → giải nén thành `giong_doc/piper/`
- [vi_VN-vais1000-medium.onnx](https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/vi/vi_VN/vais1000/medium/vi_VN-vais1000-medium.onnx)
  và [file .onnx.json](https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/vi/vi_VN/vais1000/medium/vi_VN-vais1000-medium.onnx.json) → đặt vào `giong_doc/`

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
├── run.bat               chạy từ mã nguồn
├── dong_goi.bat          đóng gói thành file .exe
├── tao_shortcut.bat      tạo shortcut ngoài Desktop
├── QuanLyNhaXe.py        điểm khởi động của bản đóng gói
├── config.ini            cài đặt (camera, phím tắt, giá vé, lưu trữ) — sửa trong nút Cài đặt
├── requirements.txt      thư viện Python cần cài
├── assets/               logo, biểu tượng công ty
├── ban_phat_hanh/        CaiDat_QuanLyNhaXe.exe (bộ cài) + QuanLyNhaXe.exe (bản chạy thẳng)
├── cong_cu/              mã nguồn bộ cài, thông tin phiên bản, file tạm lúc đóng gói
├── app/                  mã nguồn
│   ├── core/             camera, dò camera, RTSP, lưu trữ, phím tắt, giá vé, cài đặt
│   └── ui/               giao diện: màn hình chính, nhập thẻ, tra cứu, xem ảnh, cài đặt
└── data/                 dữ liệu (tự tạo khi chạy)
    ├── nhaxe.db          thông tin các lượt gửi xe
    ├── anh/<ngày>/       ảnh xe: SốThẻ_ngày_giờ_IN/OUT.jpg, ví dụ 111_28-10-2026_21h44m35_IN.jpg
    ├── xuat_file/        file Excel (CSV) đã xuất
    ├── sao_luu/          bản sao lưu tự tạo mỗi lần reset dữ liệu
    └── loi.log           nhật ký lỗi (nếu có)
```

Ảnh tự xóa sau số ngày cài đặt (mặc định 30 ngày); ảnh của xe còn đang gửi luôn được giữ lại.
Sao lưu dữ liệu: chép cả thư mục `data`.
