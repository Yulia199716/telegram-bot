import os
import requests
from datetime import datetime, time
import pytz
from ics import Calendar

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)

TOKEN = os.getenv("TOKEN")

ADMIN_IDS = {444694124, 7850041157}
SPECIAL_USER_ID = 7850041157

BIRTHDAY_CAL_URL = "https://calendar.google.com/calendar/ical/93effe2024ad7a4c10958ba8b9a712c26ee644057b258ffc72fd2332acd24c0f%40group.calendar.google.com/public/basic.ics"
EVENT_CAL_URL = "https://calendar.google.com/calendar/ical/59cbd500efaa00ff43f350199960a488bd4923ea3ecc3014274714c509e379f8%40group.calendar.google.com/public/basic.ics"

users = set()
start_counter = 0
waiting_broadcast_text = False
waiting_time_input = False

TZ = pytz.timezone("Europe/Moscow")
current_send_time = time(10, 0)  # по умолчанию 10:00
job = None


def get_today_events(url):
    r = requests.get(url)
    cal = Calendar(r.text)
    today = datetime.now(TZ).date()
    result = []

    for event in cal.events:
        if event.begin.astimezone(TZ).date() == today:
            result.append(event.name)

    return result


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

    for user_id in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=text)
        except:
            pass


def schedule_job(app):
    global job
    if job:
        job.schedule_removal()

    job = app.job_queue.run_daily(
        morning_digest,
        time=current_send_time,
        days=(0, 1, 2, 3, 4)
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global start_counter
    user_id = update.effective_user.id
    users.add(user_id)
    start_counter += 1

    keyboard = [
        [InlineKeyboardButton("Календарь", url="https://clck.ru/3MscXu")],
        [InlineKeyboardButton("Добавить мероприятие", url="https://clck.ru/3MrvFT")],
        [InlineKeyboardButton("Заявка на вход", url="https://forms.yandex.ru/cloud/697743ab068ff06061e8a02e")],
        [InlineKeyboardButton("Заявка", url="https://forms.yandex.ru/cloud/65cc7cb92530c22a292928c9/?page=1")],
        [InlineKeyboardButton("Телефонный справочник", url="https://sks-bot.ru/employee")]
    ]

    if user_id == SPECIAL_USER_ID:
        keyboard.append([InlineKeyboardButton("МОИ МЕРОПРИЯТИЯ", url="https://clck.ru/3Ms33K")])

    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("⚙ Админ-панель", callback_data="admin_panel")])

    await update.message.reply_text(
        "Добрый день! Вы как всегда прекрасны :)",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in ADMIN_IDS:
        return

    keyboard = [
        [InlineKeyboardButton("📢 Сделать рассылку", callback_data="broadcast")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("⏰ Время рассылки", callback_data="set_time")]
    ]

    await query.message.reply_text("Админ-панель:", reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_set_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global waiting_time_input
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in ADMIN_IDS:
        return

    waiting_time_input = True
    await query.message.reply_text("Введи новое время рассылки в формате HH:MM (например 09:30)")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global waiting_broadcast_text, waiting_time_input, current_send_time

    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in ADMIN_IDS:
        return

    if waiting_time_input:
        try:
            new_time = datetime.strptime(text, "%H:%M").time()
            current_send_time = new_time
            schedule_job(context.application)
            waiting_time_input = False
            await update.message.reply_text(f"✅ Время рассылки изменено на {text}")
        except:
            await update.message.reply_text("❌ Неверный формат. Введи так: 10:30")
        return

    if not waiting_broadcast_text:
        return

    sent = 0
    for uid in users:
        try:
            await context.bot.send_message(chat_id=uid, text=text)
            sent += 1
        except:
            pass

    waiting_broadcast_text = False
    await update.message.reply_text(f"✅ Рассылка отправлена {sent} пользователям.")


async def handle_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in ADMIN_IDS:
        return

    await query.message.reply_text(
        f"📊 Статистика:\n"
        f"Пользователей: {len(users)}\n"
        f"Нажатий /start: {start_counter}\n"
        f"Время рассылки: {current_send_time.strftime('%H:%M')}"
    )


async def handle_broadcast_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global waiting_broadcast_text
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in ADMIN_IDS:
        return

    waiting_broadcast_text = True
    await query.message.reply_text("Напиши текст рассылки одним сообщением.")


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(admin_panel, pattern="admin_panel"))
app.add_handler(CallbackQueryHandler(handle_broadcast_button, pattern="broadcast"))
app.add_handler(CallbackQueryHandler(handle_stats, pattern="stats"))
app.add_handler(CallbackQueryHandler(handle_set_time, pattern="set_time"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

schedule_job(app)

app.run_polling()
