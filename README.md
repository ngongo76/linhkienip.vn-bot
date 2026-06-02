# Linhkienip.vn Panic Bot

Bot Telegram tra cứu mã lỗi panic log iPhone cho thợ sửa main của **Linhkienip.vn**.

🌐 Website: [linhkienip.vn](https://linhkienip.vn)

## Tính năng

- 🔍 **Tìm kiếm tự do**: gõ mã lỗi (`AOP`, `0x80000`, `i2c0`) hoặc từ khóa Việt (`pin`, `màn hình`)
- 📂 **Menu phân loại**: AOP Panic, SMC/Sensor Array, i2c, Watchdog, A–Z
- 📱 **Phân loại theo dòng CPU**: với lỗi i2c, hiển thị chip cụ thể theo dòng iPhone (A8 → A12)
- 🇻🇳 **199+ mã lỗi đã việt hóa** cho thợ Việt
- 📷 **OCR ảnh panic log**: thợ chụp ảnh panic log → bot tự đọc text → tra mã lỗi tự động
- 🎨 **Giao diện đẹp**: HTML formatting, divider, branding rõ ràng

## Cấu trúc file

```
linhkienip_bot/
├── linhkienip_bot.py        # Code chính của bot
├── panic_data.json          # Database 199 mã lỗi
├── Bot_Linhkienip_VN.xlsx   # File Excel để review/chỉnh sửa
├── build_data.py            # Script tạo lại Excel + JSON
├── requirements.txt         # Thư viện Python cần cài
├── Procfile                 # Cho Railway biết cách khởi động
├── runtime.txt              # Phiên bản Python
└── README.md                # File này
```

## Cài đặt (Lần đầu)

### Bước 1: Tạo bot trên Telegram

1. Chat với [@BotFather](https://t.me/BotFather) → `/newbot`
2. Đặt tên: `Linhkienip.vn`
3. Đặt username: `linhkienipvn_bot` (phải kết thúc bằng `bot`)
4. Lưu **BOT_TOKEN** trả về

### Bước 2: Đăng ký OCR API Key (miễn phí, cần cho tính năng OCR)

1. Vào [https://ocr.space/ocrapi](https://ocr.space/ocrapi)
2. Bấm **Register for FREE API Key**
3. Nhập email → bấm Subscribe
4. OCR.space gửi email chứa API key cho Kevin (dạng `K1234567890ABC`)
5. Lưu key này thành **OCR_API_KEY**

> **Free tier**: 500 OCR calls/ngày, file ≤ 1MB. Đủ dùng cho nội bộ Fix Mobile/Linhkienip.vn.
> Nếu không đăng ký, bot vẫn chạy được nhưng dùng key mặc định `helloworld` với rate limit thấp (~10 calls/phút) — chỉ phù hợp để test.

### Bước 3: Cài Python + thư viện

Yêu cầu Python 3.9+ (khuyến nghị 3.12):

```bash
pip install -r requirements.txt
```

### Bước 4: Chạy bot

**Máy local (test):**

```bash
# Windows (CMD)
set BOT_TOKEN=token_từ_botfather
set OCR_API_KEY=key_từ_ocr.space
python linhkienip_bot.py

# Linux/Mac
export BOT_TOKEN="token_từ_botfather"
export OCR_API_KEY="key_từ_ocr.space"
python linhkienip_bot.py
```

**Railway.app (chạy 24/7):**

1. Push code lên GitHub (private repo)
2. [railway.app](https://railway.app) → đăng nhập GitHub
3. **+ New Project → Deploy from GitHub** → chọn repo
4. Tab **Variables** → thêm **2 biến**:
   - `BOT_TOKEN` = token từ BotFather
   - `OCR_API_KEY` = key từ OCR.space
5. Railway tự deploy + chạy 24/7

**VPS Việt Nam:**

File `/etc/systemd/system/linhkienip-bot.service`:

```ini
[Unit]
Description=Linhkienip.vn Panic Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/ubuntu/linhkienip_bot
Environment="BOT_TOKEN=your_token"
Environment="OCR_API_KEY=your_ocr_key"
ExecStart=/usr/bin/python3 linhkienip_bot.py
Restart=always
User=ubuntu

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable linhkienip-bot
sudo systemctl start linhkienip-bot
```

## Cách dùng bot

### Tra cứu bằng text
- `/start` → menu chính
- Gõ vào chat: `AOP`, `0x80000`, `i2c0`, `pin`, `màn hình`...

### Tra cứu bằng ảnh OCR
1. Chụp/screenshot panic log từ máy (Apple Configurator, Console.app, hoặc panic-full file)
2. Gửi ảnh vào bot
3. Bot tự đọc text → trích xuất mã hex + từ khóa → tra database
4. Trả về danh sách mã lỗi khớp

**Tip cho OCR chính xác:**
- Ảnh rõ nét, không mờ, không nghiêng
- Crop sát text panic log nếu có thể
- Ảnh sáng đều, không phản chiếu

## Cập nhật nội dung database

Sửa data trong `build_data.py` → chạy:
```bash
python build_data.py
```
→ Tạo lại Excel + JSON → restart bot (Railway tự deploy lại sau khi push GitHub).

## Lệnh BotFather hữu ích

| Lệnh | Tác dụng |
|---|---|
| `/setname` | Đổi tên hiển thị |
| `/setdescription` | Mô tả khi user mới mở chat |
| `/setuserpic` | Avatar (logo Linhkienip.vn 512×512) |
| `/setcommands` | Menu lệnh hiển thị |
| `/setprivacy` | Cho phép bot đọc tin nhắn trong nhóm |

**Setup `/setcommands`** (paste vào BotFather):
```
start - Mở menu chính
help - Hướng dẫn dùng bot
```

## Hướng phát triển tiếp

- [ ] Thêm hình ảnh sơ đồ vị trí chip cho mỗi lỗi
- [ ] Lọc kết quả theo dòng máy iPhone
- [ ] Thống kê: lỗi nào hay tra nhất
- [ ] Admin web panel để sửa data dễ hơn

---

**Linhkienip.vn** — 199 mã lỗi panic log iPhone đã việt hóa cho thợ Việt
