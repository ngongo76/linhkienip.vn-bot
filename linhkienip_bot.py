"""
Linhkienip.vn Panic Bot - Tra cứu mã lỗi panic log iPhone
Dùng cho thợ sửa main của Linhkienip.vn

Tính năng:
- Menu phân loại + search text
- 📷 OCR: thợ gửi ảnh panic log → bot tự đọc mã + tra cứu

Cài đặt:
    pip install -r requirements.txt

Chạy:
    export BOT_TOKEN="your_token_from_botfather"
    export OCR_API_KEY="your_key_from_ocr.space"  # optional, dùng "helloworld" nếu trống
    python linhkienip_bot.py
"""
import html
import json
import logging
import os
import re
from pathlib import Path

import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ============================================================
# LOAD DATA
# ============================================================
DATA_FILE = Path(__file__).parent / "panic_data.json"
with open(DATA_FILE, encoding="utf-8") as f:
    DATA = json.load(f)

CATEGORIES = DATA["categories"]
ALPHABET_DATA = DATA["alphabet"]
ALPHABET_LETTERS = sorted(ALPHABET_DATA.keys())

# Build a flat set of all panic code names (for OCR matching)
ALL_PANIC_CODES = set()
for _cat in CATEGORIES.values():
    for _entry in _cat["entries"]:
        ALL_PANIC_CODES.add(_entry["code"])
for _entries in ALPHABET_DATA.values():
    for _entry in _entries:
        ALL_PANIC_CODES.add(_entry["code"])

# ============================================================
# BRAND & STYLING
# ============================================================
BRAND_NAME = "LINHKIENIP.VN"
BRAND_URL = "linhkienip.vn"
BRAND_TAGLINE = "Bot tra cứu Panic Log iPhone"
DIVIDER = "━━━━━━━━━━━━━━━━━━━━"

WELCOME_TEXT = (
    f"🔧 <b>{BRAND_NAME}</b>\n"
    f"<i>{BRAND_TAGLINE}</i>\n"
    f"{DIVIDER}\n\n"
    "👋 Chào thợ! Bot giúp tra cứu mã lỗi <b>panic log iPhone</b> "
    "để xác định chip hỏng nhanh chóng.\n\n"
    "📌 <b>Cách dùng:</b>\n"
    "• Chọn nhóm lỗi bên dưới\n"
    "• Hoặc gõ trực tiếp mã lỗi vào ô chat\n"
    "    (vd: <code>AOP</code>, <code>SMC</code>, <code>0x80000</code>)\n"
    "• 📷 <b>Hoặc gửi ảnh panic log</b> - bot tự đọc & tra cứu\n"
    "• Hoặc tra theo chữ cái A–Z\n\n"
    "📚 <i>199+ mã lỗi đã việt hóa</i>\n"
    f"🌐 <i>{BRAND_URL}</i>"
)


def footer() -> str:
    return f"\n\n{DIVIDER}\n<i>🌐 {BRAND_URL}</i>"


# ============================================================
# KEYBOARDS
# ============================================================
def main_menu_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("⚡  AOP Panic  ·  Vi xử lý luôn bật", callback_data="c:aop")],
        [InlineKeyboardButton("🌡  SMC Sensor Array (1)", callback_data="c:sensor_1")],
        [InlineKeyboardButton("🌡  SMC Sensor Array (2)", callback_data="c:sensor_2")],
        [InlineKeyboardButton("🔌  i2c  ·  Bus giao tiếp giữa chip", callback_data="c:i2c")],
        [InlineKeyboardButton("⏱  Userspace Watchdog Timeout", callback_data="c:watchdog")],
        [InlineKeyboardButton("🔤  Tra cứu theo chữ cái A–Z", callback_data="alpha")],
        [InlineKeyboardButton("ℹ️  Hướng dẫn dùng bot", callback_data="help")],
    ]
    return InlineKeyboardMarkup(rows)


def nav_buttons(back_data: str = "main") -> list:
    return [
        InlineKeyboardButton("◀ Quay lại", callback_data=back_data),
        InlineKeyboardButton("🏠 Menu chính", callback_data="main"),
    ]


def category_list_keyboard(cat_key: str) -> InlineKeyboardMarkup:
    entries = CATEGORIES[cat_key]["entries"]
    rows = []
    for i, entry in enumerate(entries):
        label = entry["code"]
        if cat_key == "i2c":
            label = f"{entry['code']}  ·  {entry['cpu']}"
        if len(label) > 55:
            label = label[:52] + "…"
        rows.append([InlineKeyboardButton(label, callback_data=f"e:{cat_key}:{i}")])
    rows.append(nav_buttons())
    return InlineKeyboardMarkup(rows)


def alphabet_keyboard() -> InlineKeyboardMarkup:
    rows = []
    row = []
    for letter in ALPHABET_LETTERS:
        count = len(ALPHABET_DATA[letter])
        row.append(InlineKeyboardButton(f"{letter} · {count}", callback_data=f"a:{letter}"))
        if len(row) == 6:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append(nav_buttons())
    return InlineKeyboardMarkup(rows)


def alphabet_letter_keyboard(letter: str) -> InlineKeyboardMarkup:
    entries = ALPHABET_DATA[letter]
    rows = []
    for i, entry in enumerate(entries):
        label = entry["code"]
        if len(label) > 60:
            label = label[:57] + "…"
        rows.append([InlineKeyboardButton(label, callback_data=f"ae:{letter}:{i}")])
    rows.append([
        InlineKeyboardButton("◀ Quay lại A–Z", callback_data="alpha"),
        InlineKeyboardButton("🏠 Menu chính", callback_data="main"),
    ])
    return InlineKeyboardMarkup(rows)


# ============================================================
# FORMATTING
# ============================================================
def format_entry(entry: dict, category_title: str) -> str:
    code = html.escape(entry["code"])
    vi = html.escape(entry.get("vi", ""))
    en = html.escape(entry.get("en", ""))
    cpu = html.escape(entry.get("cpu", ""))

    text = f"📂 <b>{html.escape(category_title)}</b>\n"
    text += f"{DIVIDER}\n\n"
    text += f"🔖 <b>Mã lỗi:</b>\n<code>{code}</code>\n\n"

    if cpu:
        text += f"📱 <b>Dòng máy / CPU:</b>\n{cpu}\n\n"
        text += f"🔧 <b>Chip / Linh kiện cần kiểm tra:</b>\n<i>{vi}</i>"
    else:
        text += f"🇻🇳 <b>Ý nghĩa:</b>\n<i>{vi}</i>"
        if en and en.lower() != vi.lower():
            text += f"\n\n📝 <b>Nguyên văn (EN):</b>\n<code>{en}</code>"

    text += footer()
    return text


HELP_TEXT = (
    f"🔧 <b>{BRAND_NAME}</b>\n"
    f"<i>Hướng dẫn dùng bot</i>\n"
    f"{DIVIDER}\n\n"
    "<b>1️⃣  Tra cứu theo nhóm</b>\n"
    "• <b>AOP Panic</b> - Vi xử lý luôn bật\n"
    "• <b>SMC Sensor Array</b> - Mã hex cảm biến\n"
    "• <b>i2c</b> - Bus giao tiếp (dòng A8–A12)\n"
    "• <b>Watchdog timeout</b> - Treo tiến trình\n"
    "• <b>A–Z</b> - Theo chữ cái đầu\n\n"
    "<b>2️⃣  Tìm kiếm bằng text</b>\n"
    "Gõ trực tiếp vào ô chat:\n"
    "• Mã EN: <code>AOP PANIC</code>\n"
    "• Mã hex: <code>0x80000</code>, <code>0x41</code>\n"
    "• Từ khóa Việt: <code>pin</code>, <code>màn hình</code>\n\n"
    "<b>3️⃣  📷 Tìm kiếm bằng ảnh (OCR)</b>\n"
    "• Chụp/screenshot panic log từ máy\n"
    "• Gửi ảnh vào bot\n"
    "• Bot tự đọc text + tra cứu mã lỗi\n"
    "<i>Tip: ảnh rõ, không bị mờ sẽ đọc tốt hơn</i>\n\n"
    "<b>4️⃣  Lệnh hệ thống</b>\n"
    "• <code>/start</code> - Mở menu chính\n"
    "• <code>/help</code> - Hướng dẫn này"
    f"{footer()}"
)


# ============================================================
# COMMAND HANDLERS
# ============================================================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        WELCOME_TEXT,
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard(),
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.HTML)


# ============================================================
# SEARCH
# ============================================================
def search_all(query: str) -> list:
    """Search across all entries. Returns list of (label, callback_data, category_label)."""
    q = query.lower().strip()
    if len(q) < 2:
        return []
    results = []

    for cat_key, cat in CATEGORIES.items():
        for i, entry in enumerate(cat["entries"]):
            haystack = " ".join([
                entry.get("code", ""),
                entry.get("en", ""),
                entry.get("vi", ""),
                entry.get("cpu", ""),
            ]).lower()
            if q in haystack:
                label = entry["code"]
                if cat_key == "i2c":
                    label = f"{entry['code']}  ·  {entry['cpu']}"
                results.append((label, f"e:{cat_key}:{i}", cat["title_vi"]))

    for letter, entries in ALPHABET_DATA.items():
        for i, entry in enumerate(entries):
            haystack = " ".join([
                entry.get("code", ""),
                entry.get("en", ""),
                entry.get("vi", ""),
            ]).lower()
            if q in haystack:
                results.append((entry["code"], f"ae:{letter}:{i}", f"Chữ cái {letter}"))

    return results


async def on_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    if not query:
        return

    results = search_all(query)
    safe_q = html.escape(query)

    if not results:
        text = (
            f"❌ <b>Không tìm thấy</b>\n"
            f"{DIVIDER}\n\n"
            f"Không có mã lỗi nào khớp với <code>{safe_q}</code>\n\n"
            "<b>Thử lại với:</b>\n"
            "• Một phần của mã lỗi (vd: <code>AOP</code>, <code>SMC</code>)\n"
            "• Mã hex (vd: <code>0x80000</code>, <code>0x41</code>)\n"
            "• Từ khóa Việt (vd: <code>pin</code>, <code>màn hình</code>)\n"
            "• 📷 Hoặc gửi ảnh panic log"
            f"{footer()}"
        )
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([nav_buttons()]),
        )
        return

    MAX_RESULTS = 30
    shown = results[:MAX_RESULTS]
    rows = []
    for label, cb_data, category in shown:
        text_label = label if len(label) < 50 else label[:47] + "…"
        rows.append([InlineKeyboardButton(f"{text_label}  ·  {category}", callback_data=cb_data)])
    rows.append(nav_buttons())

    header = (
        f"🔍 <b>Kết quả tìm kiếm</b>\n"
        f"{DIVIDER}\n\n"
        f"Tìm thấy <b>{len(results)}</b> mã lỗi khớp với <code>{safe_q}</code>"
    )
    if len(results) > MAX_RESULTS:
        header += f"\n<i>(hiển thị {MAX_RESULTS} kết quả đầu tiên)</i>"
    header += "\n\nChọn để xem chi tiết:"

    await update.message.reply_text(
        header,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(rows),
    )


# ============================================================
# OCR: Photo → Panic Codes
# ============================================================
OCR_API_KEY = os.environ.get("OCR_API_KEY", "helloworld")
OCR_API_URL = "https://api.ocr.space/parse/image"
OCR_TIMEOUT = 60

# Regex để tìm mã hex (0x..., 0X...)
HEX_PATTERN = re.compile(r"0[xX][0-9a-fA-F]{2,8}")

# Từ khóa nhận diện loại panic phổ biến (case-insensitive)
PANIC_KEYWORDS = [
    "AOP PANIC", "AOP DATA ABORT", "AOP NMI",
    "SMC PANIC", "SMC DATA ABORT",
    "SEP PANIC", "SEP ROM", "Sep memory",
    "DCP PANIC", "Dart-disp",
    "AMCC ERROR", "Apple PMGR", "Apple PPM", "AppleBCMWLAN",
    "AppleHIDTransport", "AGXK", "APFS", "apcie",
    "ANS", "Anc-postnand",
    "i2c0", "i2c1", "i2c2", "i2c3", "i2c4", "i2c5",
    "Nvme", "NVMe",
    "Userspace watchdog", "Systick watchdog", "Mbuf_watchdog", "WDT timeout",
    "Kernel data abort", "Firmware fatal",
    "Baseband", "Iokit", "Initproc", "IOMFB",
    "SpringBoard", "PressureController",
    "PMP NMI", "Pmap_enter",
    "Halt", "Spmi timeout", "Sleep",
    "Coherency point", "Reset sequence",
    "AOP", "SMC", "SEP", "DCP",
]


async def ocr_image(image_bytes: bytes) -> str:
    """Send image to OCR.space API, return extracted text."""
    async with httpx.AsyncClient(timeout=OCR_TIMEOUT) as client:
        files = {"file": ("panic.jpg", image_bytes, "image/jpeg")}
        data = {
            "apikey": OCR_API_KEY,
            "language": "eng",
            "isOverlayRequired": "false",
            "detectOrientation": "true",
            "scale": "true",
            "OCREngine": "2",  # Engine 2 tốt hơn cho screenshot/text rõ
        }
        r = await client.post(OCR_API_URL, files=files, data=data)
        r.raise_for_status()
        result = r.json()

        if result.get("IsErroredOnProcessing"):
            err = result.get("ErrorMessage", ["OCR error"])
            if isinstance(err, list):
                err = " ".join(str(e) for e in err)
            raise RuntimeError(str(err))

        parsed = result.get("ParsedResults") or []
        if not parsed:
            return ""
        return parsed[0].get("ParsedText", "") or ""


def extract_panic_signals(text: str) -> dict:
    """Tìm các dấu hiệu panic từ text OCR."""
    text_upper = text.upper()

    # Mã hex
    hex_codes = list(dict.fromkeys(HEX_PATTERN.findall(text)))

    # Khớp tên panic code đầy đủ từ database (substring match)
    exact_matches = []
    for code in ALL_PANIC_CODES:
        if len(code) >= 5 and code.upper() in text_upper:
            exact_matches.append(code)
    # Sort by length desc - longer matches are more specific
    exact_matches.sort(key=len, reverse=True)

    # Khớp từ khóa category
    keyword_matches = []
    seen_kw = set()
    for kw in PANIC_KEYWORDS:
        if kw.upper() in text_upper and kw.lower() not in seen_kw:
            keyword_matches.append(kw)
            seen_kw.add(kw.lower())

    return {
        "hex_codes": hex_codes[:8],
        "exact_matches": exact_matches[:8],
        "keywords": keyword_matches[:8],
    }


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo uploads: OCR + search."""
    msg = update.message

    # Show typing/processing indicator
    await context.bot.send_chat_action(
        chat_id=msg.chat_id, action=ChatAction.TYPING
    )

    status = await msg.reply_text(
        "📷 <i>Đang tải ảnh...</i>",
        parse_mode=ParseMode.HTML,
    )

    try:
        # Tải ảnh lớn nhất
        photo = msg.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_bytes = bytes(await file.download_as_bytearray())

        # OCR
        await status.edit_text(
            "🔍 <i>Đang nhận diện text trong ảnh...</i>",
            parse_mode=ParseMode.HTML,
        )

        ocr_text = await ocr_image(image_bytes)

        if not ocr_text.strip():
            await status.edit_text(
                f"❌ <b>Không đọc được text trong ảnh</b>\n"
                f"{DIVIDER}\n\n"
                "Thử lại với:\n"
                "• Ảnh rõ hơn, không bị mờ\n"
                "• Chụp gần để chữ to hơn\n"
                "• Hoặc gõ trực tiếp mã lỗi vào ô chat",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([nav_buttons()]),
            )
            return

        # Trích xuất dấu hiệu panic
        signals = extract_panic_signals(ocr_text)

        # Search database với các signals
        all_results = []
        seen_keys = set()

        # Ưu tiên: exact matches > hex codes > keywords
        for term in signals["exact_matches"]:
            for r in search_all(term):
                if r[1] not in seen_keys:
                    seen_keys.add(r[1])
                    all_results.append(r)

        for hex_code in signals["hex_codes"]:
            for r in search_all(hex_code):
                if r[1] not in seen_keys:
                    seen_keys.add(r[1])
                    all_results.append(r)

        for kw in signals["keywords"]:
            for r in search_all(kw):
                if r[1] not in seen_keys:
                    seen_keys.add(r[1])
                    all_results.append(r)

        # Không tìm thấy gì
        if not all_results:
            preview = ocr_text[:200] + "…" if len(ocr_text) > 200 else ocr_text
            preview = html.escape(preview)
            await status.edit_text(
                f"📷 <b>Đã đọc ảnh</b> nhưng không tìm thấy mã lỗi nào khớp database.\n"
                f"{DIVIDER}\n\n"
                f"<b>Text đọc được:</b>\n<code>{preview}</code>\n\n"
                "💡 Thử gõ trực tiếp mã lỗi từ text trên vào ô chat.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([nav_buttons()]),
            )
            return

        # Build response với kết quả
        MAX = 15
        shown = all_results[:MAX]
        rows = []
        for label, cb_data, category in shown:
            text_label = label if len(label) < 50 else label[:47] + "…"
            rows.append([InlineKeyboardButton(
                f"{text_label}  ·  {category}", callback_data=cb_data
            )])
        rows.append(nav_buttons())

        # Phần header tóm tắt signals tìm được
        signals_lines = []
        if signals["hex_codes"]:
            codes_str = ", ".join(f"<code>{html.escape(c)}</code>"
                                  for c in signals["hex_codes"][:5])
            signals_lines.append(f"🔖 <b>Mã hex:</b> {codes_str}")
        if signals["keywords"]:
            kw_str = ", ".join(f"<code>{html.escape(k)}</code>"
                               for k in signals["keywords"][:5])
            signals_lines.append(f"🏷 <b>Từ khóa:</b> {kw_str}")

        signals_text = "\n".join(signals_lines)
        if signals_text:
            signals_text = "\n" + signals_text + "\n"

        header = (
            f"📷 <b>Đọc ảnh panic log thành công</b>\n"
            f"{DIVIDER}\n"
            f"{signals_text}\n"
            f"Tìm thấy <b>{len(all_results)}</b> mã lỗi khớp"
        )
        if len(all_results) > MAX:
            header += f" <i>(hiển thị {MAX} đầu)</i>"
        header += ":\n"

        await status.edit_text(
            header,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(rows),
        )

    except httpx.TimeoutException:
        await status.edit_text(
            "⏱ <b>OCR quá tải / timeout</b>\n\nThử lại sau 30 giây hoặc gõ mã lỗi trực tiếp.",
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        logger.exception("OCR error")
        await status.edit_text(
            f"❌ <b>Lỗi khi xử lý ảnh</b>\n\n"
            f"<code>{html.escape(str(e)[:200])}</code>\n\n"
            "Thử lại hoặc gõ trực tiếp mã lỗi vào chat.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([nav_buttons()]),
        )


# ============================================================
# CALLBACK HANDLER (button clicks)
# ============================================================
async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "main":
        await query.edit_message_text(
            WELCOME_TEXT,
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_keyboard(),
        )
        return

    if data == "help":
        await query.edit_message_text(
            HELP_TEXT,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([nav_buttons()]),
        )
        return

    if data == "alpha":
        text = (
            f"🔤 <b>Tra cứu theo chữ cái</b>\n"
            f"{DIVIDER}\n\n"
            "Chọn chữ cái đầu của mã lỗi.\n"
            "<i>(Số sau dấu · là số lượng mã lỗi)</i>"
        )
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=alphabet_keyboard(),
        )
        return

    if data.startswith("c:"):
        cat_key = data[2:]
        if cat_key not in CATEGORIES:
            await query.edit_message_text(
                "Lỗi: nhóm không tồn tại.",
                reply_markup=main_menu_keyboard(),
            )
            return
        title = CATEGORIES[cat_key]["title_vi"]
        count = len(CATEGORIES[cat_key]["entries"])
        text = (
            f"📂 <b>{html.escape(title)}</b>\n"
            f"{DIVIDER}\n\n"
            f"<i>{count} mã lỗi trong nhóm này</i>\n\n"
            "Chọn mã lỗi để xem chi tiết:"
        )
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=category_list_keyboard(cat_key),
        )
        return

    if data.startswith("e:"):
        _, cat_key, idx = data.split(":", 2)
        idx = int(idx)
        cat = CATEGORIES[cat_key]
        entry = cat["entries"][idx]
        text = format_entry(entry, cat["title_vi"])
        rows = [[
            InlineKeyboardButton("◀ Danh sách", callback_data=f"c:{cat_key}"),
            InlineKeyboardButton("🏠 Menu chính", callback_data="main"),
        ]]
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(rows),
        )
        return

    if data.startswith("a:"):
        letter = data[2:]
        if letter not in ALPHABET_DATA:
            await query.edit_message_text(
                "Chữ cái không có dữ liệu.",
                reply_markup=main_menu_keyboard(),
            )
            return
        count = len(ALPHABET_DATA[letter])
        text = (
            f"🔤 <b>Chữ cái: {letter}</b>\n"
            f"{DIVIDER}\n\n"
            f"<i>{count} mã lỗi bắt đầu bằng chữ {letter}</i>\n\n"
            "Chọn mã lỗi để xem chi tiết:"
        )
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=alphabet_letter_keyboard(letter),
        )
        return

    if data.startswith("ae:"):
        _, letter, idx = data.split(":", 2)
        idx = int(idx)
        entry = ALPHABET_DATA[letter][idx]
        text = format_entry(entry, f"Chữ cái {letter}")
        rows = [[
            InlineKeyboardButton("◀ Quay lại", callback_data=f"a:{letter}"),
            InlineKeyboardButton("🏠 Menu chính", callback_data="main"),
        ]]
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(rows),
        )
        return


# ============================================================
# MAIN
# ============================================================
def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "Chưa có BOT_TOKEN. Đặt biến môi trường:\n"
            "  export BOT_TOKEN='your_token_from_botfather'"
        )

    if OCR_API_KEY == "helloworld":
        logger.warning(
            "⚠ Đang dùng OCR_API_KEY mặc định (rate limit thấp). "
            "Đăng ký key miễn phí tại https://ocr.space/ocrapi"
        )

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_message))

    logger.info(f"Bot {BRAND_NAME} khởi động...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
