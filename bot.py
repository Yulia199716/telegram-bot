import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)

TOKEN = os.getenv("8219826850:AAEnU6GZBD8NNaaN_uO7znBsOVuRa3RKAJU")

ADMIN_ID = 444694124  # твой ID администратора

users = set()
start_counter = 0
waiting_broadcast_text = False


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

    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("⚙ Админ-панель", callback_data="admin_panel")])

    await update.message.reply_text(
        "Добрый день! Вы как всегда прекрасны :)",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("📢 Сделать рассылку", callback_data="broadcast")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")]
    ]

    await query.message.reply_text(
        "Админ-панель:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    text = (
        f"📊 Статистика:\n"
        f"Пользователей: {len(users)}\n"
        f"Нажатий /start: {start_counter}"
    )

    await query.message.reply_text(text)


async def handle_broadcast_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global waiting_broadcast_text
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    waiting_broadcast_text = True
    await query.message.reply_text("Напиши текст рассылки одним сообщением.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global waiting_broadcast_text

    if update.effective_user.id != ADMIN_ID:
        return

    if not waiting_broadcast_text:
        return

    text = update.message.text
    sent = 0

    for user_id in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=text)
            sent += 1
        except:
            pass

    waiting_broadcast_text = False
    await update.message.reply_text(f"✅ Рассылка отправлена {sent} пользователям.")


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(admin_panel, pattern="admin_panel"))
app.add_handler(CallbackQueryHandler(handle_broadcast_button, pattern="broadcast"))
app.add_handler(CallbackQueryHandler(handle_stats, pattern="stats"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

app.run_polling()
