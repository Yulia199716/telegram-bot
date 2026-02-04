import os
import logging
import httpx
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
    PicklePersistence,
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TOKEN")

# ID администраторов
ADMIN_IDS = {444694124, 7850041157}
REQUEST_CHAT_ID = -1003772017080

EVENT_CAL_URL = "https://calendar.google.com/calendar/ical/59cbd500efaa00ff43f350199960a488bd4923ea3ecc3014274714c509e379f8%40group.calendar.google.com/public/basic.ics"
BIRTHDAY_CAL_URL = "https://calendar.google.com/calendar/ical/93effe2024ad7a4c10958ba8b9a712c26ee644057b258ffc72fd2332acd24c0f%40group.calendar.google.com/public/basic.ics"

TZ = pytz.timezone("Europe/Moscow")

# Константы состояний
STATE_WAITING_BROADCAST = "waiting_broadcast"
STATE_WAITING_TIME = "waiting_time"
STATE_WAITING_REQUEST = "waiting_request"

REQUEST_FORMS = {
    "vks": [
        "Дата мероприятия", "Время начала", "Продолжительность", "Название мероприятия",
        "Платформа (Толк / Сферум)", "Место проведения", "Количество ведущих",
        "Количество участников", "Нужна ли трансляция", "Нужен ли показ презентации",
        "Нужен ли показ видео", "Нужно ли голосование", "Название департамента",
        "Email ответственного", "Телефон ответственного",
    ],
    "pass": [
        "Дата визита", "ФИО гостя", "Номер и марка автомобиля (или не нужно)",
        "Временной интервал парковки (или не нужно)", "ФИО ответственного", "Телефон ответственного",
    ],
    "carry": [
        "Внос или вынос", "Дата", "ФИО ответственного", "Телефон ответственного",
    ],
    "buy": [
        "ФИО ответственного", "Телефон ответственного", "Ссылка на корзину в Комусе",
    ],
}

REQUEST_TITLES = {
    "vks": "🎥 Заявка на ВКС",
    "pass": "🚗 Заявка на ПРОПУСК",
    "carry": "📦 Заявка на ВНОС/ВЫНОС",
    "buy": "🛒 Заявка на ПОКУПКУ",
}


async def get_today_events(url):
    """Асинхронное получение событий календаря"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            
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
    except Exception as e:
        logger.error(f"Ошибка календаря: {e}")
        return []


async def morning_digest(context: ContextTypes.DEFAULT_TYPE):
    """Рассылка утреннего дайджеста"""
    events = await get_today_events(EVENT_CAL_URL)
    birthdays = await get_today_events(BIRTHDAY_CAL_URL)

    text = (
        "☀ Доброе утро!\n"
        "Сегодня в календаре:\n"
        + ("\n".join(f"- {e}" for e in events) if events else "нет мероприятий")
        + "\n\nСегодня день рождения:\n"
        + ("\n".join(f"- {b}" for b in birthdays) if birthdays else "нет")
    )

    # Получаем пользователей из сохраненной базы
    users = context.bot_data.get("users", {})
    
    for uid in users:
        try:
            await context.bot.send_message(chat_id=uid, text=text)
        except Exception:
            # Пользователь мог заблокировать бота
            continue


def update_schedule_job(job_queue, trigger_time):
    """Обновляет задачу рассылки, удаляя старую"""
    current_jobs = job_queue.get_jobs_by_name("morning_digest")
    for job in current_jobs:
        job.schedule_removal()
    
    job_queue.run_daily(morning_digest, time=trigger_time, days=(0,1,2,3,4), name="morning_digest")


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
    
    # Инициализация хранилища пользователей
    if "users" not in context.bot_data:
        context.bot_data["users"] = {}
        
    context.bot_data["users"][user.id] = user.full_name
    await update.message.reply_text("Выберите действие:", reply_markup=main_menu_keyboard(user.id))


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


async def start_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    rtype = query.data.replace("req_", "")
    fields = REQUEST_FORMS[rtype]

    text = "Заполните заявку одним сообщением:\n\n"
    for i, f in enumerate(fields, 1):
        text += f"{i}. {f}\n"

    # Сохраняем состояние пользователя
    context.user_data["state"] = STATE_WAITING_REQUEST
    context.user_data["req_type"] = rtype
    
    await query.message.edit_text(text)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Получаем текущее состояние пользователя
    state = context.user_data.get("state")

    # --- Обработка рассылки (Админ) ---
    if state == STATE_WAITING_BROADCAST and user_id in ADMIN_IDS:
        users = context.bot_data.get("users", {})
        count = 0
        for uid in users:
            try:
                await context.bot.send_message(chat_id=uid, text=text)
                count += 1
            except Exception:
                pass
        
        context.user_data["state"] = None
        await update.message.reply_text(f"✅ Рассылка отправлена ({count} получ.).")
        return

    # --- Обработка смены времени (Админ) ---
    if state == STATE_WAITING_TIME and user_id in ADMIN_IDS:
        try:
            new_time_dt = datetime.strptime(text, "%H:%M")
            new_time = time(new_time_dt.hour, new_time_dt.minute, tzinfo=TZ)
            
            # Сохраняем время в БД
            context.bot_data["broadcast_time_str"] = text
            
            # Обновляем задачу
            update_schedule_job(context.application.job_queue, new_time)
            
            context.user_data["state"] = None
            await update.message.reply_text(f"✅ Новое время рассылки: {text}")
        except ValueError:
            await update.message.reply_text("❌ Введите в формате HH:MM")
        return

    # --- Обработка заявки ---
    if state == STATE_WAITING_REQUEST:
        rtype = context.user_data.get("req_type")
        if not rtype:
            context.user_data["state"] = None
            return

        title = REQUEST_TITLES[rtype]
        user_name = update.effective_user.full_name
        username = update.effective_user.username
        
        msg = f"{title}\n👤 {user_name} (@{username})\n\n{text}"

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Все готово", callback_data=f"ok_{user_id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"no_{user_id}")
            ]
        ])

        try:
            sent = await context.bot.send_message(chat_id=REQUEST_CHAT_ID, text=msg, reply_markup=keyboard)
            try:
                await context.bot.pin_chat_message(chat_id=REQUEST_CHAT_ID, message_id=sent.message_id, disable_notification=True)
            except Exception:
                pass
            
            await update.message.reply_text("✅ Заявка отправлена. Мы сообщим, когда все будет готово.")
        except Exception as e:
            logger.error(f"Ошибка отправки заявки: {e}")
            await update.message.reply_text("❌ Ошибка отправки заявки администратору.")

        # Сброс состояния
        context.user_data["state"] = None
        context.user_data.pop("req_type", None)
        return


async def decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, uid_str = query.data.split("_")
    uid = int(uid_str)

    try:
        if action == "ok":
            await context.bot.send_message(chat_id=uid, text="✅ Ваша заявка готова.")
            new_text = f"{query.message.text}\n\n✅ ВЫПОЛНЕНО"
        else:
            await context.bot.send_message(chat_id=uid, text="❌ Ваша заявка отклонена.")
            new_text = f"{query.message.text}\n\n❌ ОТКЛОНЕНО"

        await query.message.edit_text(text=new_text, reply_markup=None)
        try:
            await context.bot.unpin_chat_message(REQUEST_CHAT_ID, query.message.message_id)
        except Exception:
            pass
    except Exception as e:
        await query.message.reply_text(f"Ошибка (возможно пользователь заблокировал бота): {e}")


async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Сбрасываем состояния при выходе в меню
    context.user_data["state"] = None
    
    await query.message.edit_text("Выберите действие:", reply_markup=main_menu_keyboard(query.from_user.id))


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("⏰ Изменить время рассылки", callback_data="admin_time")],
        [InlineKeyboardButton("📊 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton("⬅ Назад", callback_data="back_main")],
    ]

    await query.message.edit_text("Админ-панель:", reply_markup=InlineKeyboardMarkup(keyboard))


async def admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "admin_broadcast":
        context.user_data["state"] = STATE_WAITING_BROADCAST
        await query.message.edit_text("Введите текст рассылки:")
        
    elif query.data == "admin_time":
        context.user_data["state"] = STATE_WAITING_TIME
        current = context.bot_data.get("broadcast_time_str", "10:00")
        await query.message.edit_text(f"Текущее время: {current}\nВведите новое время в формате HH:MM")
        
    elif query.data == "admin_users":
        users = context.bot_data.get("users", {})
        text = f"👥 Пользователи ({len(users)}):\n"
        # Ограничим вывод, чтобы не превысить лимит сообщения
        count = 0
        for name in users.values():
            text += f"- {name}\n"
            count += 1
            if count >= 40:
                text += "... и другие"
                break
        await query.message.edit_text(text)


def main():
    if not TOKEN:
        print("ОШИБКА: Не задан TOKEN в переменных окружения")
        return

    # Настройка Persistence (сохранение данных в файл)
    persistence = PicklePersistence(filepath="bot_data.pickle")
    
    app = ApplicationBuilder().token(TOKEN).persistence(persistence).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(requests_menu, pattern="^requests_menu$"))
    app.add_handler(CallbackQueryHandler(start_request, pattern="^req_(vks|pass|carry|buy)$"))
    app.add_handler(CallbackQueryHandler(decision, pattern="^(ok_|no_)"))
    app.add_handler(CallbackQueryHandler(back_main, pattern="^back_main$"))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(admin_actions, pattern="^admin_"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Восстановление задачи рассылки при запуске
    # Пытаемся получить сохраненное время, иначе используем 10:00
    saved_time_str = app.bot_data.get("broadcast_time_str", "10:00")
    try:
        t_struct = datetime.strptime(saved_time_str, "%H:%M").time()
        send_time = time(t_struct.hour, t_struct.minute, tzinfo=TZ)
    except ValueError:
        send_time = time(10, 0, tzinfo=TZ)

    update_schedule_job(app.job_queue, send_time)

    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
