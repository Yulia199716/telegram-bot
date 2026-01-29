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
)

TOKEN = os.getenv("TOKEN")

# роли
ADMIN_IDS = {444694124, 7850041157}
USER_SHABELNIK = 63158924
USER_ADMIN_WITH_TWO = 7850041157

EVENT_CAL_URL = "https://calendar.google.com/calendar/ical/59cbd500efaa00ff43f350199960a488bd4923ea3ecc3014274714c509e379f8%40group.calendar.google.com/public/basic.ics"
BIRTHDAY_CAL_URL = "https://calendar.google.com/calendar/ical/93effe2024ad7a4c10958ba8b9a712c26ee644057b258ffc72fd2332acd24c0f%40group.calendar.google.com/public/basic.ics"

TZ = pytz.timezone("Europe/Moscow")

users = set()


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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users.add(user_id)

    keyboard = [
        [InlineKeyboardButton("📅 Календарь", url="https://clck.ru/3MscXu")],
        [InlineKeyboardButton("➕ Добавить мероприятие", url="https://clck.ru/3MrvFT")],
        [InlineKeyboardButton("📝 Заявка на вход", url="https://forms.yandex.ru/cloud/697743ab068ff06061e8a02e")],
        [InlineKeyboardButton("📝 Заявка", url="https://forms.yandex.ru/cloud/65cc7cb92530c22a292928c9/?page=1")],
        [InlineKeyboardButton("📞 Телефонный справочник", url="https://sks-bot.ru/employee")]
    ]

    # Шабельник
    if user_id == USER_SHABELNIK:
        keyboard.append([
            InlineKeyboardButton("Мероприятия Шабельник В.В.", url="https://clck.ru/3Ms2mH")
        ])

    # админ с двумя кнопками
    if user_id == USER_ADMIN_WITH_TWO:
        keyboard.append([
            InlineKeyboardButton("Мероприятия Шабельник В.В.", url="https://clck.ru/3Ms2mH")
        ])
        keyboard.append([
            InlineKeyboardButton("Мероприятия Солодилова Л.А.", url="https://clck.ru/3Ms33K")
        ])

    # админка
    if user_id in ADMIN_IDS:
        keyboard.append([
            InlineKeyboardButton("⚙ Админ-панель", callback_data="admin_panel")
        ])

    await update.message.reply_text(
        "Добрый день! Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in ADMIN_IDS:
        return

    await query.message.reply_text("Админ-панель (пока пусто)")


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="admin_panel"))

    send_time = time(10, 0, tzinfo=TZ)

    if app.job_queue:
        app.job_queue.run_daily(
            morning_digest,
            time=send_time,
            days=(0, 1, 2, 3, 4)
        )
    else:
        print("❌ JobQueue не инициализирован")

    app.run_polling()


if __name__ == "__main__":
    main()
