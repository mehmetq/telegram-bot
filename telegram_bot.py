import sqlite3
import random
from datetime import datetime, timedelta
import logging
import os

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ================== TOKEN ==================
TOKEN = os.getenv("8492081360:AAFYWijP2qJf_-QkCeO36pyVP7xhzhM2af0")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing")

# ================== LOG ==================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ================== MOTİVASYON ==================
MOTIVE_SOZLER = [
    "Yavaş ol. Kontrol sende.",
    "Acele eden kaybeder.",
    "Bugün refleks değil, sen varsın.",
    "Nefes yavaş, beden sakin.",
    "Kontrol güçtür."
]

# ================== PLAN ==================
PLAN = {
    1:  {"sure": 5,  "durma": "20 saniye"},
    3:  {"sure": 6,  "durma": "20–25 saniye"},
    5:  {"sure": 7,  "durma": "25 saniye"},
    7:  {"sure": 8,  "durma": "25–30 saniye"},
    9:  {"sure": 9,  "durma": "30 saniye"},
    11: {"sure": 10, "durma": "30 saniye"},
    13: {"sure": 11, "durma": "30–35 saniye"},
    15: {"sure": 12, "durma": "35 saniye"},
    17: {"sure": 13, "durma": "35–40 saniye"},
    19: {"sure": 14, "durma": "40 saniye"},
    21: {"sure": 15, "durma": "40 saniye"},
}

# ================== DATABASE ==================
conn = sqlite3.connect("progress.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    chat_id INTEGER PRIMARY KEY,
    current_day INTEGER,
    timer_start TEXT,
    target_minutes INTEGER
)
""")
conn.commit()

# ================== DB HELPERS ==================
def get_user(chat_id):
    cur.execute("SELECT * FROM users WHERE chat_id=?", (chat_id,))
    return cur.fetchone()

def create_user(chat_id):
    cur.execute(
        "INSERT INTO users VALUES (?,?,?,?)",
        (chat_id, 1, None, None)
    )
    conn.commit()

def advance_day(chat_id):
    cur.execute("""
        UPDATE users
        SET current_day = current_day + 1,
            timer_start = NULL,
            target_minutes = NULL
        WHERE chat_id=?
    """, (chat_id,))
    conn.commit()

# ================== /start ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not get_user(chat_id):
        create_user(chat_id)

    await update.message.reply_text(
        "🔥 *Start–Stop aktif*\n\n"
        "Bugünkü görev için:\n"
        "/bugun",
        parse_mode="Markdown"
    )

# ================== /bugun ==================
async def bugun(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = get_user(chat_id)
    day = user[1]

    if day > 21:
        await update.message.reply_text("🎉 21 gün tamamlandı. Kontrol artık sende.")
        return

    if day not in PLAN:
        advance_day(chat_id)
        await update.message.reply_text("🧘 Bugün dinlenme günü. Yarın devam.")
        return

    sure = PLAN[day]["sure"]
    durma = PLAN[day]["durma"]

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Başlıyorum", callback_data=f"basla_{sure}")]
    ])

    await update.message.reply_text(
        f"""
━━━━━━━━━━━━━━
🔥 *START–STOP*
━━━━━━━━━━━━━━

📅 Gün: *{day}/21*
⏱ Süre: *{sure} dakika*

Ne yapacaksın:
• Yaklaş → *TAM DUR*
• *{durma}* bekle
• Nefesi yavaşlat
• Devam et

🚫 Porno yok  
🫁 Acele yok  

_{random.choice(MOTIVE_SOZLER)}_

Hazırsan başla 👇
""",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

# ================== BUTTON ==================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id

    # ▶️ BAŞLA
    if query.data.startswith("basla"):
        sure = int(query.data.split("_")[1])
        start_time = datetime.now()

        cur.execute("""
            UPDATE users
            SET timer_start=?, target_minutes=?
            WHERE chat_id=?
        """, (start_time.isoformat(), sure, chat_id))
        conn.commit()

        await query.edit_message_text(
            f"▶️ Sayaç başladı\n\n"
            f"⏱ *{sure} dakika*\n"
            "Yavaş ol. Kontrol sende.",
            parse_mode="Markdown"
        )

        context.application.job_queue.run_once(
            timer_bitti,
            when=timedelta(minutes=sure),
            chat_id=chat_id,
            name=f"timer_{chat_id}"
        )

    # ⏹ BİTİR
    elif query.data == "bitir":
        user = get_user(chat_id)
        start_time = datetime.fromisoformat(user[2])
        elapsed = int((datetime.now() - start_time).total_seconds() / 60)

        advance_day(chat_id)

        await query.edit_message_text(
            f"""
⏹ *GÜN TAMAMLANDI*

⏱ Süre: *{elapsed} dakika*

Bugün ipler sendeydi 😌
""",
            parse_mode="Markdown"
        )

# ================== TIMER BİTTİ ==================
async def timer_bitti(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id

    await context.bot.send_message(
        chat_id=chat_id,
        text="⏰ *Süre bitti*\n\nYavaşça bırak.\nHazırsan bitir 👇",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⏹ Bitir", callback_data="bitir")]
        ])
    )

# ================== MAIN ==================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bugun", bugun))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
