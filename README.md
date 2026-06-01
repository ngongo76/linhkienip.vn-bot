# Linhkienip.vn Panic Bot

Bot Telegram tra cứu mã lỗi panic log iPhone cho thợ sửa main của **Linhkienip.vn**.

🌐 Website: [linhkienip.vn](https://linhkienip.vn)

## Tính năng

- 🔍 **Tìm kiếm tự do**: gõ trực tiếp mã lỗi (vd: `AOP`, `0x80000`, `i2c0`) hoặc từ khóa Việt (`pin`, `màn hình`)
- 📂 **Menu phân loại**: AOP Panic, SMC/Sensor Array, i2c, Watchdog, A–Z
- 📱 **Phân loại theo dòng CPU**: với lỗi i2c, hiển thị chip cụ thể theo dòng iPhone (A8 → A12)
- 🇻🇳 **199+ mã lỗi đã việt hóa** sẵn sàng cho thợ Việt
- 🎨 **Giao diện đẹp**: HTML formatting, divider, branding rõ ràng

## Cấu trúc file

```
linhkienip_bot/
├── linhkienip_bot.py        # Code chính của bot
├── panic_data.json          # Database 199 mã lỗi
├── Bot_Linhkienip_VN.xlsx   # File Excel để review/chỉnh sửa thủ công
├── build_data.py            # Script tạo lại Excel + JSON khi cần
├── requirements.txt         # Thư viện Python cần cài
├── Procfile                 # Cho Railway biết cách khởi động
├── runtime.txt              # Chỉ định phiên bản Python
└── README.md                # File này
```

## Cài đặt (Lần đầu)

### Bước 1: Tạo bot trên Telegram

1. Mở Telegram, chat với [@BotFather](https://t.me/BotFather)
2. Gõ `/newbot`
3. Đặt tên hiển thị: vd. `Linhkienip.vn`
4. Đặt username: vd. `linhkienipvn_bot` (phải kết thúc bằng `bot`, không có dấu chấm)
5. BotFather trả về **API Token** dạng: `1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ`
6. **Lưu token này** — chìa khóa của bot

### Bước 2: Cài Python và thư viện

Yêu cầu: Python 3.9+ (khuyến nghị 3.12)

```bash
pip install -r requirements.txt
```

### Bước 3: Chạy bot

**Trên máy local (test):**

```bash
# Windows (CMD)
set BOT_TOKEN=dán_token_BotFather_vào_đây
python linhkienip_bot.py

# Linux/Mac
export BOT_TOKEN="dán_token_BotFather_vào_đây"
python linhkienip_bot.py
```

**Trên Railway.app (production - chạy 24/7):**

1. Push code lên GitHub repo (private)
2. Đăng nhập [railway.app](https://railway.app) bằng GitHub
3. **+ New Project → Deploy from GitHub repo** → chọn repo
4. Vào tab **Variables** → thêm `BOT_TOKEN` = token từ BotFather
5. Railway tự deploy + chạy bot 24/7

**Trên VPS Việt Nam (Vietnix/Tinohost - thanh toán VND):**

Tạo file `/etc/systemd/system/linhkienip-bot.service`:

```ini
[Unit]
Description=Linhkienip.vn Panic Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/ubuntu/linhkienip_bot
Environment="BOT_TOKEN=token_của_bạn"
ExecStart=/usr/bin/python3 linhkienip_bot.py
Restart=always
User=ubuntu

[Install]
WantedBy=multi-user.target
```

Enable + start:
```bash
sudo systemctl enable linhkienip-bot
sudo systemctl start linhkienip-bot
sudo systemctl status linhkienip-bot
```

## Cập nhật nội dung database

### Sửa nội dung mã lỗi

1. Mở `build_data.py`, sửa data trong các list `SENSOR_ARRAY_1`, `AOP_PANIC`, `ALPHABET`...
2. Chạy lại: `python build_data.py` → tạo lại Excel + JSON
3. Restart bot (hoặc push lên GitHub → Railway tự deploy lại)

### Hoặc sửa trực tiếp `panic_data.json`

```json
{
  "categories": {
    "aop": {
      "title_vi": "Lỗi AOP (vi xử lý luôn bật)",
      "entries": [
        {"code": "AOP PANIC", "en": "...", "vi": "..."}
      ]
    }
  }
}
```

## Thêm bot vào nhóm Telegram của Linhkienip.vn

1. Mở nhóm Telegram
2. Bấm tên nhóm → **Add Member**
3. Gõ username bot → Add

**Lưu ý:** Trong nhóm, bot mặc định chỉ phản hồi lệnh `/`. Muốn bot search được trong nhóm: vào BotFather → `/setprivacy` → chọn bot → **Disable**.

## Lệnh BotFather hữu ích

| Lệnh | Tác dụng |
|---|---|
| `/setname` | Đổi tên hiển thị bot |
| `/setdescription` | Đổi mô tả (hiện khi user mới mở chat) |
| `/setuserpic` | Đổi avatar (nên dùng logo Linhkienip.vn 512×512) |
| `/setcommands` | Đặt danh sách lệnh hiển thị trong menu |
| `/setprivacy` | Bật/tắt bot đọc tin nhắn trong nhóm |

### Setup `/setcommands` gợi ý

Paste vào BotFather:
```
start - Mở menu chính
help - Hướng dẫn dùng bot
```

## Hướng phát triển tiếp

- [ ] Thêm hình ảnh sơ đồ vị trí chip cho mỗi lỗi
- [ ] Lọc kết quả theo dòng máy (iPhone X, 11, 12...)
- [ ] OCR: thợ chụp ảnh panic log → bot tự đọc mã
- [ ] Thống kê: lỗi nào hay tra nhất

---

**Linhkienip.vn** — Database 199 mã lỗi panic log iPhone đã việt hóa cho thợ Việt
