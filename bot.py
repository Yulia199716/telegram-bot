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

# роли
ADMIN_IDS = {444694124, 7850041157}
USER_SHABELNIK = 63158924
USER_ADMIN_WITH_TWO = 7850041157

REQUEST_CHAT_ID = -1003772017080  # ЧАТ ДЛЯ ЗАЯВОК ВКС

EVENT_CAL_URL = "https://calendar.google.com/calendar/ical/59cbd500efaa00ff43f350199960a488bd4923ea3ecc3014274714c509e379f8%40group.calendar.google.com/public/basic.ics"
BIRTHDAY_CAL_URL = "https://calendar.google.com/calendar/ical/93effe2024ad7a4c10958ba8b9a712c26ee644057b258ffc72fd2332acd24c0f%40group.calendar.google.com/public/basic.ics"

TZ = pytz.timezone("Europe/Moscow")

users = {}

waiting_broadcast = False
waiting_time = False

vks_requests = {}
waiting_vks_step = {}

current_send_time = time(10, 0, tzinfo=TZ)
job = None


def get_user_name(user):
    if user.username:
        return f"@{user.username}"
    return f"{user.first_name or ''} {user.last_name or ''}".strip()


def get_today_events(url):
    try:
        r = requests.get(url, timeout=10)
        cal = Calendar(r.text)
        today = datetime.now(TZ).date()
        result = []

        for event in cal.events:
            event_dt = event.begin.astimezone(TZ)
            if event_dt.date() == today:
                event_time = event_dt.strftime("%H:%M")
                result.append(f"{event_time} — {event.name}")

        return result
    except:
        return []


async def morning_digest(context: ContextTypes.DEFAULT_TYPE):
    events = get_today_events(EVENT_CAL_URL)
    birthdays = get_today_events(BIRTHDAY_CAL_URL)

    events_text = "\n".join(f"- {e}" for e in events) if events else "нет мероприятий"
    birthday_text = "\n".join(f"- {b}" for b in birthdays) if birthdays else "нет"

    text = (
        "☀ Доброе утро!\n"
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
        days=(0, 1, 2, 3, 4),
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    users[user.id] = get_user_name(user)

    keyboard = [
        [InlineKeyboardButton("📅 Календарь", url="https://clck.ru/3MscXu")],
        [InlineKeyboardButton("➕ Добавить мероприятие", url="https://clck.ru/3MrvFT")],
        [InlineKeyboardButton("🎥 Заявка на ВКС", callback_data="vks_request")],
        [InlineKeyboardButton("📝 Заявка на вход", url="https://forms.yandex.ru/cloud/697743ab068ff06061e8a02e")],
        [InlineKeyboardButton("📝 Заявка", url="https://forms.yandex.ru/cloud/65cc7cb92530c22a292928c9/?page=1")],
        [InlineKeyboardButton("📞 Телефонный справочник", url="https://sks-bot.ru/employee")],
        [InlineKeyboardButton("📎 План работы", url="https://clck.ru/3RWwS3")],
    ]

    if user.id == USER_SHABELNIK:
        keyboard.append([InlineKeyboardButton("Мероприятия Шабельник В.В.", url="https://clck.ru/3Ms2mH")])

    if user.id == USER_ADMIN_WITH_TWO:
        keyboard.append([InlineKeyboardButton("Мероприятия Шабельник В.В.", url="https://clck.ru/3Ms2mH")])
        keyboard.append([InlineKeyboardButton("Мероприятия Солодилова Л.А.", url="https://clck.ru/3Ms33K")])

    if user.id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("⚙ Админ-панель", callback_data="admin_panel")])

    await update.message.reply_text(
        "Добрый день! Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# -------- ЗАЯВКА ВКС --------

VKS_FIELDS = [
    "Дата мероприятия",
    "Время начала",
    "Продолжительность",
    "Название мероприятия",
    "Платформа (Толк / Сферум)",
    "Место проведения",
    "Количество ведущих",
    "Количество участников",
    "Нужна ли трансляция (да/нет)",
    "Нужен ли показ презентации (да/нет)",
    "Нужен ли показ видео (да/нет)",
    "Нужно ли голосование (да/нет)",
    "Название департамента",
    "Email ответственного",
    "Телефон ответственного",
]


async def start_vks_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    waiting_vks_step[user_id] = 0
    vks_requests[user_id] = {}

    await query.message.reply_text(f"Введите: {VKS_FIELDS[0]}")


async def handle_vks_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.message.chat.id != REQUEST_CHAT_ID:
        return

    data = query.data

    if data.startswith("vks_accept_"):
        user_id = int(data.replace("vks_accept_", ""))
        await context.bot.send_message(chat_id=user_id, text="✅ Ваша заявка ВКС ПРИНЯТА.")
        await query.message.reply_text("Заявка принята.")

    elif data.startswith("vks_reject_"):
        user_id = int(data.replace("vks_reject_", ""))
        await context.bot.send_message(chat_id=user_id, text="❌ Ваша заявка ВКС ОТКЛОНЕНА.")
        await query.message.reply_text("Заявка отклонена.")


# -------- АДМИНКА --------

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in ADMIN_IDS:
        return

    keyboard = [
        [InlineKeyboardButton("📢 Сделать рассылку", callback_data="broadcast")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("⏰ Изменить время рассылки", callback_data="set_time")],
    ]

    await query.message.reply_text("Админ-панель:", reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_broadcast_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global waiting_broadcast
    query = update.callback_query
    await query.answer()
    waiting_broadcast = True
    await query.message.reply_text("Напиши текст рассылки одним сообщением.")


async def handle_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = "📊 Пользователи:\n"
    for uid, name in users.items():
        text += f"- {name}\n"

    text += f"\nВсего: {len(users)}\nВремя рассылки: {current_send_time.strftime('%H:%M')}"
    await query.message.reply_text(text)


async def handle_set_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global waiting_time
    query = update.callback_query
    await query.answer()
    waiting_time = True
    await query.message.reply_text("Введи время в формате HH:MM (например 09:30)")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global waiting_broadcast, waiting_time, current_send_time

    user_id = update.effective_user.id
    text = update.message.text.strip()

    # ---- заявка ВКС ----
    if user_id in waiting_vks_step:
        step = waiting_vks_step[user_id]
        field = VKS_FIELDS[step]
        vks_requests[user_id][field] = text
        step += 1

        if step < len(VKS_FIELDS):
            waiting_vks_step[user_id] = step
            await update.message.reply_text(f"Введите: {VKS_FIELDS[step]}")
            return
        else:
            data = vks_requests[user_id]
            msg = "🎥 Новая заявка ВКС:\n\n"
            for k, v in data.items():
                msg += f"{k}: {v}\n"

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Принять", callback_data=f"vks_accept_{user_id}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"vks_reject_{user_id}")
                ]
            ])

            await context.bot.send_message(chat_id=REQUEST_CHAT_ID, text=msg, reply_markup=keyboard)
            await update.message.reply_text("✅ Ваша заявка отправлена.")

            del waiting_vks_step[user_id]
            del vks_requests[user_id]
            return

    # ---- админка ----
    if user_id not in ADMIN_IDS:
        return

    if waiting_time:
        try:
            new_time = datetime.strptime(text, "%H:%M").time()
            current_send_time = time(new_time.hour, new_time.minute, tzinfo=TZ)
            schedule_job(context.application)
            waiting_time = False
            await update.message.reply_text(f"✅ Время изменено на {text}")
        except:
            await update.message.reply_text("❌ Формат неверный. Пример: 10:30")
        return

    if waiting_broadcast:
        sent = 0
        for uid in users:
            try:
                await context.bot.send_message(chat_id=uid, text=text)
                sent += 1
            except:
                pass

        waiting_broadcast = False
        await update.message.reply_text(f"✅ Отправлено {sent} пользователям.")


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(start_vks_request, pattern="^vks_request$"))
    app.add_handler(CallbackQueryHandler(handle_vks_decision, pattern="^vks_accept_"))
    app.add_handler(CallbackQueryHandler(handle_vks_decision, pattern="^vks_reject_"))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(handle_broadcast_button, pattern="^broadcast$"))
    app.add_handler(CallbackQueryHandler(handle_stats, pattern="^stats$"))
    app.add_handler(CallbackQueryHandler(handle_set_time, pattern="^set_time$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    schedule_job(app)
    app.run_polling()


if __name__ == "__main__":
    main()
