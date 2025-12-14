import sqlite3
import random
from datetime import datetime, timedelta

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

# ================== TOKEN ==================
TOKEN = "8492081360:AAFYWijP2qJf_-QkCeO36pyVP7xhzhM2af0"

# ================== METİNLER ==================
MOTIVE_SOZLER = [
    "Yavaş ol. Kontrol sende.",
    "Acele eden kaybeder.",
    "Bugün refleks değil, sen varsın.",
    "Nefes yavaş, beden sakin.",
    "Kontrol güçtür."
]

# ================== PLAN ==================
PLAN = {
    1:  {"sure":5,  "durma":"20 saniye"},
    3:  {"sure":6,  "durma":"20–25 saniye"},
    5:  {"sure":7,  "durma":"25 saniye"},
    7:  {"sure":8,  "durma":"25–30 saniye"},
    9:  {"sure":9,  "durma":"30 saniye"},
    11: {"sure":10, "durma":"30 saniye"},
    13: {"sure":11, "durma":"30–35 saniye"},
    15: {"sure":12, "durma":"35 saniye"},
    17: {"sure":13, "durma":"35–40 saniye"},
    19: {"sure":14, "durma":"40 saniye"},
    21: {"sure":15, "durma":"40 saniye"},
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

# --- MIGRATION ---
try:
    cur.execute("ALTER TABLE users ADD COLUMN timer_start TEXT")
except:
    pass

try:
    cur.execute("ALTER TABLE users ADD COLUMN target_minutes INTEGER")
except:
    pass

conn.commit()

# ================== DB HELPERS ==================
def get_user(chat_id):
    cur.execute("SELECT * FROM users WHERE chat_id=?", (chat_id,))
    return cur.fetchone()

def create_user(chat_id):
    cur.execute(
        "INSERT INTO users (chat_id, current_day, timer_start, target_minutes) VALUES (?,?,?,?)",
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

# ================== START ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not get_user(chat_id):
        create_user(chat_id)

    await update.message.reply_text(
        "🔥 Start–Stop Bot Aktif\n\n"
        "Bugünkü görevi görmek için:\n"
        "/bugun"
    )

# ================== BUGÜN ==================
async def bugun(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = get_user(chat_id)
    day = user[1]

    if day > 21:
        await update.message.reply_text(
            "🎉 21 gün tamamlandı.\nKontrol artık sende."
        )
        return

    if day not in PLAN:
        advance_day(chat_id)
        await update.message.reply_text(
            "🧘‍♂️ Bugün dinlenme günü.\nYarın devam."
        )
        return

    sure = PLAN[day]["sure"]
    durma = PLAN[day]["durma"]

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Zamanı Başlat", callback_data=f"basla_{sure}")]
    ])

    await update.message.reply_text(
        f"""
━━━━━━━━━━━━━━━━
🔥 START–STOP GÜNÜ
━━━━━━━━━━━━━━━━

📅 Gün: {day} / 21
⏱ Toplam süre: {sure} dakika

🧠 Ne yapacaksın?
1️⃣ Yavaşça uyarılmayı başlat  
2️⃣ Yaklaşınca TAMAMEN DUR  
3️⃣ {durma} bekle  
4️⃣ Nefesini yavaşlat  
5️⃣ Tekrar devam et  
6️⃣ Süre bitene kadar döngüyü sürdür  

🚫 Porno yok
🫁 Acele yok

“{random.choice(MOTIVE_SOZLER)}”

Hazırsan başlat 👇
""",
        reply_markup=keyboard
    )

# ================== BUTTON HANDLER ==================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id

    # ▶️ BAŞLAT
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
            f"▶️ Sayaç başladı.\n"
            f"{sure} dakika boyunca çalışacak.\n\n"
            "Acele yok. Nefes yavaş."
        )

        context.job_queue.run_once(
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
⏹ GÜN TAMAMLANDI

⏱ Geçen süre:
{elapsed} dakika

Bugün kontrol sendeydi.
"""
        )

# ================== TIMER BİTTİ ==================
async def timer_bitti(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    user = get_user(chat_id)

    if not user or not user[2]:
        return

    start_time = datetime.fromisoformat(user[2])
    elapsed = int((datetime.now() - start_time).total_seconds() / 60)

    await context.bot.send_message(
        chat_id=chat_id,
        text=
        f"""
⏰ SÜRE BİTTİ

⏱ Toplam süre:
{elapsed} dakika

Yavaşça bırak.
Hazırsan bitir 👇
""",
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
