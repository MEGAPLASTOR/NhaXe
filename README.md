# Quản Lý Nhà Xe — VIDATEX JSC

Phần mềm ghi nhận xe vào / ra bằng 2 camera Imou (cổng vào, cổng ra) và thẻ giữ xe đánh số.

## Cách chạy

**Giao cho khách file `CaiDat_QuanLyNhaXe.exe`** — chạy là cài, không cần Python hay thư viện gì.

| File | Làm gì |
|---|---|
| `ban_phat_hanh\CaiDat_QuanLyNhaXe.exe` | **Bộ cài đặt** — đưa cho khách file này |
| `ban_phat_hanh\CapNhat_QuanLyNhaXe.exe` | **Bản cập nhật** — gửi cho máy đang dùng bản cũ, giữ nguyên dữ liệu |
| `ban_phat_hanh\QuanLyNhaXe.exe` | Bản chạy thẳng, không cài (chép vào USB mang đi) |
| `run.bat` | Chạy từ mã nguồn (để sửa code). Lần đầu tự cài Python và thư viện. |
| `dong_goi.bat` | Đóng gói lại cả 3 file trên sau khi sửa code |
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

### Cập nhật máy đang dùng bản cũ
Gửi file `CapNhat_QuanLyNhaXe.exe` (mã nguồn: `cong_cu/cap_nhat.py`), chạy rồi bấm **Cập nhật**:

1. Tự tìm thư mục đã cài (Apps & features → bản đang chạy → `C:\QuanLyNhaXe`); không thấy thì bấm **Chọn...**
   (bản chạy thẳng `QuanLyNhaXe.exe` cũng cập nhật được, chỉ cần chọn đúng thư mục).
2. Phần mềm đang mở thì hỏi rồi tự đóng (nhờ phần mềm tự tắt trước, quá 12 giây mới buộc tắt).
3. Sao lưu `config.ini` vào `data/sao_luu/truoc_cap_nhat_<ngày giờ>/`, thay `QuanLyNhaXe.exe`
   (chép ra file tạm rồi đổi tên, hỏng giữa chừng thì bản cũ vẫn còn), thư mục `giong_doc`, `GoCaiDat.exe`,
   sửa số phiên bản trong Apps & features.
4. **Giữ nguyên** thư mục `data` (xe, ảnh, tiền) và `config.ini` (mật khẩu, camera, giá, lời đọc).
   Webhook / bot Discord mặc định nằm sẵn trong chương trình mới nên có ngay sau khi cập nhật.

Nâng phiên bản thì sửa cả `app/__init__.py`, `cong_cu/trinh_cai_dat.py` và 3 file
`cong_cu/thong_tin_*.txt` (phiên bản, bộ cài, bản cập nhật).

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
Trong đó: đổi phím, nhập IP / mật khẩu camera, **giá gửi xe**, **giọng nói**, **Discord**, số ngày giữ ảnh.

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

### Discord: báo cáo 00:00 và tra cứu
Cài trong **⚙ Cài đặt → Discord**, có 2 phần độc lập:

**1. Báo cáo hằng ngày qua webhook** (chỉ gửi một chiều). Lấy webhook: chuột phải kênh → Chỉnh sửa kênh →
Tích hợp → Webhook → Webhook mới → Sao chép URL webhook, dán vào ô **Địa chỉ webhook**, bấm **Gửi thử**.
Đúng 00:00 mỗi ngày phần mềm gửi ảnh thẻ thống kê ngày vừa qua (xe trong ngày, vào, ra, còn trong bãi,
tiền thu, đang gửi), không kèm file danh sách. Máy tắt lúc 00:00 thì lần mở sau gửi bù (tối đa 7 ngày);
mất mạng thì 5 phút sau thử lại. Ngày đã gửi ghi trong `data/discord.json`.

**2. Tra cứu bằng bot** (thư viện `discord.py`). Tạo bot: [discord.com/developers](https://discord.com/developers/applications)
→ New Application → Bot → Reset Token, dán token vào ô **Token bot**. Mời bot vào server: OAuth2 → URL Generator →
tích `bot` và `applications.commands`, quyền Send Messages / Embed Links / Attach Files → mở link, chọn server.
Ô **ID kênh** (bật Developer Mode rồi chuột phải kênh → Sao chép ID) giới hạn lệnh chỉ dùng trong kênh đó.

| Lệnh | Trả về |
|---|---|
| `/thongke [ngay]` | Thống kê 1 ngày (mặc định hôm nay). Ngày gõ `31/10/2026`, `31/10`, `hôm qua` |
| `/lichsu [ngay]` | Danh sách từng lượt trong ngày (đang gửi / gửi qua đêm / đã ra) |
| `/tracuu the [so_luot]` | Các lượt gần nhất của 1 số thẻ + ảnh vào / ra của lượt mới nhất |
| `/danggui` | Các xe đang gửi trong bãi |

Báo cáo và câu trả lời của bot là **ảnh thẻ thống kê** nền tối (vẽ bằng Pillow trong `app/core/discord_card.py`):
thẻ ngày có tiền thu, xe vào / ra, biểu đồ xe theo giờ, bãi xe, giờ cao điểm; thẻ tra cứu có ảnh camera
lượt gần nhất; thẻ danh sách cho `/lichsu` và `/danggui` (tối đa 20 dòng, còn lại xem trong phần mềm bằng F4). Tin nhắn Discord chỉ có ảnh, không kèm file.

Bot chỉ chạy khi phần mềm đang mở và máy có mạng.

**Webhook / token mặc định gắn sẵn:** file `assets/mac_dinh.ini` (mục `[discord]`, cùng dạng với `config.ini`)
được đóng gói vào exe, nên cài ở máy nào cũng tự có webhook và bot. Ô nào trong `config.ini` để trống thì dùng
giá trị mặc định; lưu mà trùng mặc định thì `config.ini` không ghi lại token. File này nằm trong `.gitignore`,
**không đưa lên git**. Muốn đổi bản mặc định: sửa file đó rồi chạy lại `dong_goi.bat`.
Tab Discord khóa sẵn (che địa chỉ webhook), bấm **Mở khóa để thay đổi** mới sửa được; có nút **Khôi phục mặc định**.
Lưu ý: ai có file exe đều có thể lấy được token / webhook bên trong — đừng phát exe cho người lạ; lộ thì
Reset Token bot, tạo webhook mới, sửa `assets/mac_dinh.ini` và đóng gói lại.

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
├── config.ini            cài đặt (camera, phím tắt, giá vé, giọng nói, Discord) — sửa trong nút Cài đặt
├── requirements.txt      thư viện Python cần cài
├── assets/               logo, biểu tượng công ty
├── ban_phat_hanh/        CaiDat_QuanLyNhaXe.exe (bộ cài) + QuanLyNhaXe.exe (bản chạy thẳng)
├── cong_cu/              mã nguồn bộ cài, thông tin phiên bản, file tạm lúc đóng gói
├── app/                  mã nguồn
│   ├── core/             camera, RTSP, lưu trữ, phím tắt, giá vé, giọng nói, thống kê, Discord, cài đặt
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
