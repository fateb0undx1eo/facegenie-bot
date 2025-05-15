import json
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
import asyncio

USER_DATA_FILE = "user_data.json"

def load_user_data():
    try:
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_user_data(data):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_month_str():
    return datetime.datetime.now().strftime("%Y-%m")

async def send_disclaimer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("✅ Agree", callback_data="agree"),
         InlineKeyboardButton("❌ Disagree", callback_data="disagree")]
    ]
    disclaimer_text = (
        "🤖 *FaceGenie Bot Disclaimer*\n\n"
        "This bot generates *AI-created faces*. Some images may look very real but are entirely AI-generated.\n\n"
        "By clicking *Agree* you accept our terms, privacy policy, and the credit rules.\n\n"
        "Please choose to Agree or Disagree."
    )
    await update.message.reply_text(
        disclaimer_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_disclaimer(update, context)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    user_data = load_user_data()

    if query.data == "agree":
        if user_id not in user_data:
            user_data[user_id] = {
                "username": None,
                "credits": 5,
                "month_joined": get_month_str(),
                "last_reset": get_month_str(),
                "subscribed": False,
                "ads_used_today": 0,
                "last_ad_day": None
            }
            save_user_data(user_data)
        await query.edit_message_text(
            "🎉 Welcome to FaceGenie! 🧞‍♂️✨ I generate 100% AI-created faces. Let's begin!\n\n"
            "Please type a custom username (this is just for our records, no connection with Telegram username)."
        )
        return
    elif query.data == "disagree":
        await query.edit_message_text(
            "⚠️ You disagreed with the terms. The bot will now end interaction. To use the bot, please start again and agree to the disclaimer."
        )
        return

async def receive_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    user_data = load_user_data()

    if user_id in user_data and user_data[user_id]["username"] is None:
        username = update.message.text.strip()
        user_data[user_id]["username"] = username
        save_user_data(user_data)
        await update.message.reply_text(
            f"✅ Username set to: {username}\n\n"
            "You have *5 free credits* to generate AI faces this month.\nUse /generate to get your first AI face!",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("Please use /generate to get AI faces or /help for commands.")

def reset_monthly_credits(user):
    today = datetime.datetime.now()
    last_reset = datetime.datetime.strptime(user["last_reset"], "%Y-%m")
    if today.year > last_reset.year or today.month > last_reset.month:
        months_passed = (today.year - last_reset.year) * 12 + (today.month - last_reset.month)
        user["credits"] += 5 * months_passed
        user["last_reset"] = today.strftime("%Y-%m")

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    user_data = load_user_data()
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")

    if user_id not in user_data or user_data[user_id]["username"] is None:
        await update.message.reply_text("Please start the bot with /start and agree to the disclaimer first.")
        return

    user = user_data[user_id]

    reset_monthly_credits(user)

    if user.get("last_ad_day") != today_str:
        user["ads_used_today"] = 0
        user["last_ad_day"] = today_str

    if user.get("subscribed", False):
        await send_ai_image(update)
        save_user_data(user_data)
        return

    if user["credits"] > 0:
        user["credits"] -= 1
        await send_ai_image(update)
        save_user_data(user_data)
        return

    keyboard = [
        [InlineKeyboardButton("▶️ Watch Ad to get 1 credit", callback_data="watch_ad")],
        [InlineKeyboardButton("💳 Buy Subscription ($3/month)", callback_data="buy_sub")]
    ]
    await update.message.reply_text(
        "🕐 Your free credits are over for this month!\n"
        "🔁 You’ll get +5 more credits next month — and it increases by 5 every month you stay active! 🎁\n"
        "💡 Watch an ad to continue now, or\n"
        "🔓 Unlock unlimited access with just $3/month.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    save_user_data(user_data)

async def send_ai_image(update: Update):
    img_url = "https://thispersondoesnotexist.com/image"
    await update.message.reply_photo(photo=img_url, caption="🖼️ Here is your AI-generated face! These images are AI-generated.")

async def watch_ad_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    user_data = load_user_data()

    if user_id not in user_data:
        await query.edit_message_text("Please start the bot first using /start.")
        return

    user = user_data[user_id]
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")

    if user.get("last_ad_day") != today_str:
        user["ads_used_today"] = 0
        user["last_ad_day"] = today_str

    if user["ads_used_today"] >= 10:
        await query.edit_message_text("⚠️ You have reached the max ad-earned credits for today (10). Please wait until tomorrow or subscribe for unlimited access.")
        return

    await query.edit_message_text("▶️ Playing ad... Please wait a moment.")

    user["credits"] += 1
    user["ads_used_today"] += 1
    save_user_data(user_data)

    await query.message.reply_text("✅ Thanks for watching the ad! You have been awarded 1 credit. Use /generate to get your AI face.")

async def buy_sub_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "💳 Subscribe for just $3/month via crypto.\n"
        "🎁 Get unlimited AI face generations instantly!\n"
        "Contact @yourtelegramhandle for payment and subscription activation."
    )

async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    user_data = load_user_data()

    if user_id not in user_data:
        await update.message.reply_text("Please start the bot with /start.")
        return

    user = user_data[user_id]
    next_reset = (datetime.datetime.strptime(user["last_reset"], "%Y-%m") + datetime.timedelta(days=31)).strftime("%Y-%m")
    subscribed = "✅" if user.get("subscribed", False) else "❌"

    stats_text = (
        f"👤 Username: {user.get('username', 'N/A')}\n"
        f"💳 Credits left: {user.get('credits', 0)}\n"
        f"🔔 Subscribed: {subscribed}\n"
        f"📅 Next monthly reset: {next_reset}\n"
        f"▶️ Ads watched today: {user.get('ads_used_today', 0)}"
    )
    await update.message.reply_text(stats_text)

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ Unknown command. Please use /start, /generate, /stats, or other valid commands.")

async def delete_webhook(bot):
    await bot.delete_webhook(drop_pending_updates=True)

def main():
    TOKEN = "7870088297:AAHqUayOSDbrZXv4iwdWkV3V5_ulC_mBdMg"
    bot = Bot(token=TOKEN)
    app = Application.builder().token(TOKEN).build()

    # Delete webhook properly with asyncio
    asyncio.run(delete_webhook(bot))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(agree|disagree)$"))
    app.add_handler(CallbackQueryHandler(watch_ad_handler, pattern="^watch_ad$"))
    app.add_handler(CallbackQueryHandler(buy_sub_handler, pattern="^buy_sub$"))
    app.add_handler(CommandHandler("generate", generate_image))
    app.add_handler(CommandHandler("stats", stats_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), receive_username))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
