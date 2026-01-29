import os
from datetime import datetime, time
import pytz

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

ADMIN_IDS = {444694124, 7850041157}
SPECIAL_USER_ID = 63158924  # ← пользователь с кнопкой "МОИ МЕРОПРИЯТИЯ"

TZ = pytz.timezone("Europe/Moscow")

users = set()
waiting_time_input = False
current_send_time = time(10, 0)
job = None


async def morning_message(context: ContextTypes.DEFAULT_TYPE):
    text = (
        "☀Доброе утро!\n"
        "Сегодня в календаре:\n"
        "нет мероприятий\n\n"
        "Сегодня день рождения:\n"
        "нет"
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
        morning_message,
        time=current_send_time,
        days=(0, 1, 2, 3, 4),
        tzinfo=TZ
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users.add(user_id)

    keyboard = [
        [InlineKeyboardButton("Календарь", url="https://clck.ru/3MscXu")],
        [InlineKeyboardButton("Добавить мероприятие", url="https://clck.ru/3MrvFT")],
        [InlineKeyboardButton("Заявка на вход", url="https://forms.yandex.ru/cloud/697743ab068ff06061e8a02e")],
        [InlineKeyboardButton("Заявка", url="https://forms.yandex.ru/cloud/65cc7cb92530c22a292928c9/?page=1")],
        [InlineKeyboardButton("Телефонный справочник", url="https://sks-bot.ru/employee")]
    ]

    # кнопка ТОЛЬКО для пользователя 63158924
    if user_id == SPECIAL_USER_ID:
        keyboard.append(
            [InlineKeyboardButton("МОИ МЕРОПРИЯТИЯ", url="https://clck.ru/3Ms2mH")]
        )

    # админ-кнопка
    if user_id in ADMIN_IDS:
        keyboard.append(
            [InlineKeyboardButton("⚙ Админ-панель", callback_data="admin_panel")]
        )

    await update.message.reply_text(
        "Добрый день!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in ADMIN_IDS:
        return

    keyboard = [
        [InlineKeyboardButton("⏰ Изменить время рассылки", callback_data="set_time")]
    ]

    await query.message.reply_text(
        "Админ-панель:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


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
        await update.message.reply_text(
            f"✅ Время рассылки изменено на {new_time.strftime('%H:%M')}"
        )
    except:
        await update.message.reply_text("❌ Неверный формат. Пример: 10:30")


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(admin_panel, pattern="admin_panel"))
app.add_handler(CallbackQueryHandler(set_time, pattern="set_time"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

schedule_job(app)

app.run_polling()
