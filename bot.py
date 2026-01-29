import os
import requests
from datetime import datetime, time
import pytz
from ics import Calendar

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

TOKEN = os.getenv("TOKEN")

ADMIN_IDS = {444694124, 7850041157}  # твои админы

EVENT_CAL_URL = "https://calendar.google.com/calendar/ical/59cbd500efaa00ff43f350199960a488bd4923ea3ecc3014274714c509e379f8%40group.calendar.google.com/public/basic.ics"
BIRTHDAY_CAL_URL = "https://calendar.google.com/calendar/ical/93effe2024ad7a4c10958ba8b9a712c26ee644057b258ffc72fd2332acd24c0f%40group.calendar.google.com/public/basic.ics"

TZ = pytz.timezone("Europe/Moscow")

users = set()
waiting_time_input = False
current_send_time = time(10, 0)
job = None


def get_today_events(url):
    try:
        r = requests.get(url, timeout=10)
        cal = Calendar(r.text)
        today = datetime.now(TZ).date()
        result = []

        for event in cal.events:
            if event.begin.astimezone(TZ).date() == today:
                result.append(event.name)

        return result
    except Exception as e:
        print("Ошибка календаря:", e)
        return []


async def morning_digest(context: ContextTypes.DEFAULT_TYPE):
    events = get_today_events(EVENT_CAL_URL)
    birthdays = get_today_events(BIRTHDAY_CAL_URL)

    events_text = "\n".join(f"- {e}" for e in events) if events else "нет мероприятий"
    birthday_text = "\n".join(f"- {b}" for b in birthdays) if birthdays else "нет"

    text = (
        "☀Доброе утро!\n"
        "Сегодня в календаре:\n"
        f"{events_text}\n\n"
        "Сегодня день рождения:\n"
        f"{birthday_text}"
    )

    for uid in users:
        try:
            await context.bot.send_message(chat_id=uid, text=text)
        except:
            pass


def schedule_job(app):
    global job
    if job:
        job.schedule_removal()

    job = app.job_queue.run_daily(
        morning_digest,
        time=current_send_time,
        days=(0, 1, 2, 3, 4),  # пн–пт
        tzinfo=TZ
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users.add(user_id)

    keyboard = []

    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("⚙ Админ-панель", callback_data="admin_panel")])

    await update.message.reply_text(
        "Добрый день!",
        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
    )


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in ADMIN_IDS:
        return

    keyboard = [
        [InlineKeyboardButton("⏰ Изменить время рассылки", callback_data="set_time")]
    ]

    await query.message.reply_text("Админ-панель:", reply_markup=InlineKeyboardMarkup(keyboard))


async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global waiting_time_input
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in ADMIN_IDS:
        return

    waiting_time_input = True
    await query.message.reply_text("Введи время в формате HH:MM (например 09:30)")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global waiting_time_input, current_send_time

    if update.effective_user.id not in ADMIN_IDS:
        return

    if not waiting_time_input:
        return

    try:
        new_time = datetime.strptime(update.message.text, "%H:%M").time()
        current_send_time = new_time
        schedule_job(context.application)
        waiting_time_input = False
        await update.message.reply_text(f"✅ Время рассылки изменено на {new_time.strftime('%H:%M')}")
    except:
        await update.message.reply_text("❌ Неверный формат. Пример: 10:30")


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(admin_panel, pattern="admin_panel"))
app.add_handler(CallbackQueryHandler(set_time, pattern="set_time"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

schedule_job(app)

app.run_polling()
