import sqlite3
import random
from datetime import datetime, time

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ================== AYARLAR ==================

TOKEN = "8492081360:AAFYWijP2qJf_-QkCeO36pyVP7xhzhM2af0"

# ================== MOTİVASYON METİNLERİ ==================

MOTIVE_SOZLER = [
    "Yavaş ol… kontrol sende 😏",
    "Acele eden kaybeder.",
    "Bugün refleks değil, sen varsın.",
    "Nefesi yavaşlat. Patron sensin.",
    "Kontrol = güç. Güç çekicidir.",
    "Bugün bedenine hükmeden adamsın."
]

SABAH_SOZLERI = [
    "🌅 Günaydın\nBugün acele yok.\nBugün kontrol var 😏",
    "Uyan.\nYavaş olan kazanır.",
    "Bugün disiplin günü.",
    "Hazırsan güç sende."
]

# ================== 21 GÜNLÜK PLAN ==================

PLAN = {
    1:  {"sure":5,  "tur":2,   "durma":"20 sn"},
    3:  {"sure":6,  "tur":2,   "durma":"20–25 sn"},
    5:  {"sure":7,  "tur":3,   "durma":"25 sn"},
    7:  {"sure":8,  "tur":3,   "durma":"25–30 sn"},
    9:  {"sure":9,  "tur":3,   "durma":"30 sn"},
    11: {"sure":10, "tur":"3–4","durma":"30 sn"},
    13: {"sure":11, "tur":4,   "durma":"30–35 sn"},
    15: {"sure":12, "tur":4,   "durma":"35 sn"},
    17: {"sure":13, "tur":4,   "durma":"35–40 sn"},
    19: {"sure":14, "tur":"4–5","durma":"40 sn"},
    21: {"sure":15, "tur":5,   "durma":"40 sn"},
}

# ================== DATABASE ==================

conn = sqlite3.connect("progress.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    chat_id INTEGER PRIMARY KEY,
    current_day INTEGER
)
""")
conn.commit()

# ================== YARDIMCILAR ==================

def get_user(chat_id):
    cur.execute("SELECT current_day FROM users WHERE chat_id=?", (chat_id,))
    row = cur.fetchone()
    return row[0] if row else None

def create_user(chat_id):
    cur.execute("INSERT INTO users VALUES (?,?)", (chat_id, 1))
    conn.commit()

def advance_day(chat_id):
    cur.execute(
        "UPDATE users SET current_day = current_day + 1 WHERE chat_id=?",
        (chat_id,)
    )
    conn.commit()

def gunluk_mesaj(day, p):
    return f"""
━━━━━━━━━━━━━━━━
🔥  START–STOP GÜNÜ
━━━━━━━━━━━━━━━━

📅 Gün: {day} / 21

⏱ Süre
• {p['sure']} dakika

🔁 Kontrol
• {p['tur']} tur

⏸ Dur
• {p['durma']}

🫁 Tempo
• Yavaş
• Nefes derin

🚫 Porno
• Yasak

━━━━━━━━━━━━━━━━
😏 Bugün mesajın:
“{random.choice(MOTIVE_SOZLER)}”
━━━━━━━━━━━━━━━━

👇 Bitince seç
"""

def dinlenme_mesaji(day):
    return f"""
━━━━━━━━━━━━━━━━
🧘‍♂️ DİNLENME GÜNÜ
━━━━━━━━━━━━━━━━

📅 Gün: {day} / 21

Bugün çalışma yok.
Vücudu rahat bırak.

😌
“Zorlama yok, istikrar var.”
━━━━━━━━━━━━━━━━
"""

# ================== KOMUTLAR ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if get_user(chat_id) is None:
        create_user(chat_id)

    await update.message.reply_text(
        "🔥 START–STOP BOT AKTİF 🔥\n\n"
        "• Pornosuz\n"
        "• Acele yok\n"
        "• Kontrol öğreniyoruz\n\n"
        "Hazırsan /bugun yaz 😏"
    )

async def bugun(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    day = get_user(chat_id)

    if day is None:
        await start(update, context)
        return

    if day > 21:
        await update.message.reply_text(
            "🎉 21 GÜN TAMAMLANDI 🎉\n\n"
            "Kontrol artık sende.\n"
            "Bu refleks senin."
        )
        return

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yaptım", callback_data="yaptim"),
            InlineKeyboardButton("⏭ Geç", callback_data="yapmadim")
        ],
        [
            InlineKeyboardButton("🔥 Gaz ver", callback_data="motive")
        ]
    ])

    if day in PLAN:
        text = gunluk_mesaj(day, PLAN[day])
    else:
        text = dinlenme_mesaji(day)

    await update.message.reply_text(text, reply_markup=keyboard)

# ================== BUTONLAR ==================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id

    if query.data == "yaptim":
        advance_day(chat_id)
        await query.edit_message_text(
            "✅ Not alındı.\n"
            "Disiplin çekicidir 😏\n"
            "Yarın devam."
        )

    elif query.data == "yapmadim":
        advance_day(chat_id)
        await query.edit_message_text(
            "⏭ Bugün geçildi.\n"
            "Sorun yok.\n"
            "Yarın devam."
        )

    elif query.data == "motive":
        await query.answer(
            random.choice(MOTIVE_SOZLER),
            show_alert=True
        )

# ================== SABAH MESAJI ==================

async def sabah_job(context: ContextTypes.DEFAULT_TYPE):
    cur.execute("SELECT chat_id FROM users")
    for (chat_id,) in cur.fetchall():
        await context.bot.send_message(
            chat_id=chat_id,
            text=random.choice(SABAH_SOZLERI)
        )

# ================== MAIN ==================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bugun", bugun))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.job_queue.run_daily(
        sabah_job,
        time=time(hour=9, minute=0)
    )

    app.run_polling()

if __name__ == "__main__":
    main()
