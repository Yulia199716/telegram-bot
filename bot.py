import os
import json
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

ADMIN_IDS = {444694124, 7850041157}
REQUEST_CHAT_ID = -1003772017080

EVENT_CAL_URL = "https://calendar.google.com/calendar/ical/59cbd500efaa00ff43f350199960a488bd4923ea3ecc3014274714c509e379f8%40group.calendar.google.com/public/basic.ics"
BIRTHDAY_CAL_URL = "https://calendar.google.com/calendar/ical/93effe2024ad7a4c10958ba8b9a712c26ee644057b258ffc72fd2332acd24c0f%40group.calendar.google.com/public/basic.ics"

TZ = pytz.timezone("Europe/Moscow")
current_send_time = time(10, 0, tzinfo=TZ)

USERS_FILE = "users.json"

if os.path.exists(USERS_FILE):
    with open(USERS_FILE, "r") as f:
        users = json.load(f)
else:
    users = {}

pending_requests = {}
job = None

waiting_broadcast = False
waiting_time_change = False

REQUEST_FORMS = {
    "vks": [
        "Дата мероприятия",
        "Время начала",
        "Продолжительность",
        "Название мероприятия",
        "Платформа (Толк / Сферум)",
        "Место проведения",
        "Количество ведущих",
        "Количество участников",
        "Нужна ли трансляция",
        "Нужен ли показ презентации",
        "Нужен ли показ видео",
        "Нужно ли голосование",
        "Название департамента",
        "Email ответственного",
        "Телефон ответственного",
    ],
    "pass": [
        "Дата визита",
        "ФИО гостя",
        "Номер и марка автомобиля (или не нужно)",
        "Временной интервал парковки (или не нужно)",
        "ФИО ответственного",
        "Телефон ответственного",
    ],
    "carry": [
        "Внос или вынос",
        "Дата",
        "ФИО ответственного",
        "Телефон ответственного",
    ],
    "buy": [
        "ФИО ответственного",
        "Телефон ответственного",
        "Ссылка на корзину в Комусе",
    ],
}

REQUEST_TITLES = {
    "vks": "🎥 Заявка на ВКС",
    "pass": "🚗 Заявка на ПРОПУСК",
    "carry": "📦 Заявка на ВНОС/ВЫНОС",
    "buy": "🛒 Заявка на ПОКУПКУ",
}


def save_users():
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)


def get_today_events(url):
    try:
        r = requests.get(url, timeout=15)
        cal = Calendar(r.text)
        today = datetime.now(TZ).date()
        result = []

        for event in cal.events:
            dt = event.begin.astimezone(TZ)
            if dt.date() == today:
                if event.begin.time() == time(0, 0):
                    result.append(event.name)
                else:
                    result.append(f"{dt.strftime('%H:%M')} — {event.name}")

        return result
    except:
        return []


async def morning_digest(context):
    events = get_today_events(EVENT_CAL_URL)
    birthdays = get_today_events(BIRTHDAY_CAL_URL)

    text = (
        "☀ Доброе утро!\n"
        "Сегодня в календаре:\n"
        + ("\n".join(f"- {e}" for e in events) if events else "нет мероприятий")
        + "\n\nСегодня день рождения:\n"
        + ("\n".join(f"- {b}" for b in birthdays) if birthdays else "нет")
    )

    for uid in users:
        try:
            await context.bot.send_message(chat_id=int(uid), text=text)
        except:
            pass


def schedule_job(app):
    global job
    if job:
        job.schedule_removal()

    job = app.job_queue.run_daily(
        morning_digest,
        time=current_send_time,
        days=(0, 1, 2, 3, 4)  # ПН-ПТ
    )


def main_menu_keyboard(user_id):
    keyboard = [
        [InlineKeyboardButton("📅 Календарь", url="https://clck.ru/3MscXu")],
        [InlineKeyboardButton("➕ Добавить мероприятие", url="https://clck.ru/3MrvFT")],
        [InlineKeyboardButton("📨 Заявки", callback_data="requests_menu")],
        [InlineKeyboardButton("📎 План работы", url="https://clck.ru/3RWwS3")],
        [InlineKeyboardButton("📞 Телефонный справочник", url="https://www.sks-bot.ru/prof_employee/employee")],
    ]
    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("⚙ Админ-панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    users[str(user.id)] = user.full_name
    save_users()
    await update.message.reply_text(
        "Вы подписаны на рассылку мероприятий 📅\nСообщения приходят по будням в 10:00.",
        reply_markup=main_menu_keyboard(user.id),
    )


async def requests_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("🎥 ВКС", callback_data="req_vks")],
        [InlineKeyboardButton("🚗 ПРОПУСК", callback_data="req_pass")],
        [InlineKeyboardButton("📦 ВНОС/ВЫНОС", callback_data="req_carry")],
        [InlineKeyboardButton("🛒 ПОКУПКА", callback_data="req_buy")],
        [InlineKeyboardButton("⬅ Назад", callback_data="back_main")],
    ]

    await query.message.edit_text("Тип заявки:", reply_markup=InlineKeyboardMarkup(keyboard))


async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.edit_text("Выберите действие:", reply_markup=main_menu_keyboard(query.from_user.id))


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(requests_menu, pattern="^requests_menu$"))
    app.add_handler(CallbackQueryHandler(back_main, pattern="^back_main$"))

    schedule_job(app)
    app.run_polling()


if __name__ == "__main__":
    main()
