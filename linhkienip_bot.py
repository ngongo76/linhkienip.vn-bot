"""
Linhkienip.vn Panic Bot - Tra cứu mã lỗi panic log iPhone
Dùng cho thợ sửa main của Linhkienip.vn

Cài đặt:
    pip install -r requirements.txt

Chạy:
    export BOT_TOKEN="your_token_from_botfather"
    python linhkienip_bot.py
"""
import html
import json
import logging
import os
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
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
    """Grid of A-Z letters, 6 per row for compact look."""
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
    "• <b>i2c</b> - Bus giao tiếp giữa chip (theo dòng A8–A12)\n"
    "• <b>Watchdog timeout</b> - Treo tiến trình\n"
    "• <b>A–Z</b> - Theo chữ cái đầu của mã lỗi\n\n"
    "<b>2️⃣  Tìm kiếm nhanh</b>\n"
    "Gõ trực tiếp vào ô chat:\n"
    "• Mã lỗi EN: <code>AOP PANIC</code>\n"
    "• Mã hex: <code>0x80000</code>, <code>0x41</code>\n"
    "• Từ khóa Việt: <code>pin</code>, <code>màn hình</code>, <code>camera</code>\n\n"
    "<b>3️⃣  Lệnh hệ thống</b>\n"
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
            "• Từ khóa Việt (vd: <code>pin</code>, <code>màn hình</code>)"
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
            "<i>(Số sau dấu · là số lượng mã lỗi trong chữ cái đó)</i>"
        )
        await query.edit_message_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=alphabet_keyboard(),
        )
        return

    # Category list: c:CATEGORY
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

    # Entry detail: e:CATEGORY:INDEX
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

    # Alphabet letter: a:LETTER
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

    # Alphabet entry: ae:LETTER:INDEX
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

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_message))

    logger.info(f"Bot {BRAND_NAME} khởi động...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
