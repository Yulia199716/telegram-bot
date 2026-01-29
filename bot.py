mport os
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

users = {}
current_send_time = time(10, 0, tzinfo=TZ)

pending_requests = {}

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


def get_today_events(url):
    try:
        r = requests.get(url, timeout=10)
        cal = Calendar(r.text)
        today = datetime.now(TZ).date()
        result = []

        for event in cal.events:
            event_dt = event.begin.astimezone(TZ)
            if event_dt.date() == today:
                if event.begin.time() == time(0, 0):
                    result.append(event.name)
                else:
                    result.append(f"{event_dt.strftime('%H:%M')} — {event.name}")

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
            await context.bot.send_message(chat_id=uid, text=text)
        except:
            pass


def schedule_job(app):
    app.job_queue.run_daily(morning_digest, time=current_send_time, days=(0, 1, 2, 3, 4))


# ---------- ГЛАВНОЕ МЕНЮ ----------

def main_menu_keyboard(user_id):
    keyboard = [
        [InlineKeyboardButton("📅 Календарь", url="https://clck.ru/3MscXu")],
        [InlineKeyboardButton("➕ Добавить мероприятие", url="https://clck.ru/3MrvFT")],
        [InlineKeyboardButton("📨 Заявки", callback_data="requests_menu")],
        [InlineKeyboardButton("📎 План работы", url="https://clck.ru/3RWwS3")],
        [InlineKeyboardButton("📞 Телефонный справочник", url="https://sks-bot.ru/employee")],
    ]

    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("⚙ Админ-панель", callback_data="admin_panel")])

    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    users[user.id] = user.full_name

    await update.message.reply_text(
        "Выберите действие:",
        reply_markup=main_menu_keyboard(user.id),
    )


# ---------- МЕНЮ ЗАЯВОК ----------

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

    await query.message.edit_message_text(
        "Тип заявки:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def start_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    rtype = query.data.replace("req_", "")
    fields = REQUEST_FORMS[rtype]

    text = "Заполните заявку одним сообщением:\n\n"
    for i, f in enumerate(fields, 1):
        text += f"{i}. {f}\n"

    pending_requests[query.from_user.id] = rtype
    await query.message.edit_message_text(text)


# ---------- ПРИЁМ ЗАЯВОК ----------

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in pending_requests:
        return

    msg = "📨 Новая заявка:\n\n" + text

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Все готово", callback_data=f"ok_{user_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"no_{user_id}")
        ]
    ])

    await context.bot.send_message(chat_id=REQUEST_CHAT_ID, text=msg, reply_markup=keyboard)
    await update.message.reply_text("✅ Заявка отправлена. Мы сообщим, когда всё будет готово.")

    del pending_requests[user_id]


# ---------- РЕШЕНИЕ В ЧАТЕ ----------

async def decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.message.chat.id != REQUEST_CHAT_ID:
        return

    if query.data.startswith("ok_"):
        uid = int(query.data.replace("ok_", ""))
        await context.bot.send_message(chat_id=uid, text="✅ Ваша заявка готова.")
        await query.message.reply_text("Отмечено как выполнено.")

    elif query.data.startswith("no_"):
        uid = int(query.data.replace("no_", ""))
        await context.bot.send_message(chat_id=uid, text="❌ Ваша заявка отклонена.")
        await query.message.reply_text("Заявка отклонена.")


async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.edit_message_text(
        "Выберите действие:",
        reply_markup=main_menu_keyboard(query.from_user.id),
    )


# ---------- АДМИН ПАНЕЛЬ ----------

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("⬅ Назад", callback_data="back_main")]
    ]

    await query.message.edit_message_text("Админ-панель", reply_markup=InlineKeyboardMarkup(keyboard))


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(requests_menu, pattern="^requests_menu$"))
    app.add_handler(CallbackQueryHandler(start_request, pattern="^req_"))
    app.add_handler(CallbackQueryHandler(decision, pattern="^(ok_|no_)"))
    app.add_handler(CallbackQueryHandler(back_main, pattern="^back_main$"))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    schedule_job(app)
    app.run_polling()


if __name__ == "__main__":
    main()
