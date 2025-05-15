import json
import os
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
import asyncio
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
USER_DATA_FILE = "user_data.json"
BACKUP_DATA_FILE = "user_data_backup.json"
MAX_USERNAME_LENGTH = 32
MAX_ADS_PER_DAY = 10

class UserDataManager:
    @staticmethod
    def load_user_data() -> dict:
        """Load user data from JSON file with error handling."""
        try:
            with open(USER_DATA_FILE, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Try to restore from backup if main file is corrupted
            try:
                with open(BACKUP_DATA_FILE, "r") as f:
                    data = json.load(f)
                    # Save back to main file if backup is good
                    with open(USER_DATA_FILE, "w") as out_f:
                        json.dump(data, out_f, indent=4)
                    return data
            except (FileNotFoundError, json.JSONDecodeError):
                return {}

    @staticmethod
    def save_user_data(data: dict) -> None:
        """Save user data with backup system."""
        try:
            # First write to backup
            with open(BACKUP_DATA_FILE, "w") as f:
                json.dump(data, f, indent=4)
            # Then write to main file
            with open(USER_DATA_FILE, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save user data: {e}")

    @staticmethod
    def get_month_str() -> str:
        """Get current month in YYYY-MM format."""
        return datetime.datetime.now().strftime("%Y-%m")

    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate username input."""
        if not username or len(username) > MAX_USERNAME_LENGTH:
            return False
        # Add more validation as needed
        return True

async def send_disclaimer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the initial disclaimer message."""
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    await send_disclaimer(update, context)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries from buttons."""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    user_data = UserDataManager.load_user_data()

    if query.data == "agree":
        if user_id not in user_data:
            user_data[user_id] = {
                "username": None,
                "credits": 5,
                "month_joined": UserDataManager.get_month_str(),
                "last_reset": UserDataManager.get_month_str(),
                "subscribed": False,
                "ads_used_today": 0,
                "last_ad_day": None
            }
            UserDataManager.save_user_data(user_data)
        await query.edit_message_text(
            "🎉 Welcome to FaceGenie! 🧞‍♂️✨ I generate 100% AI-created faces. Let's begin!\n\n"
            "Please type a custom username (this is just for our records, no connection with Telegram username)."
        )
    elif query.data == "disagree":
        await query.edit_message_text(
            "⚠️ You disagreed with the terms. The bot will now end interaction. To use the bot, please start again and agree to the disclaimer."
        )

async def receive_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle username input from user."""
    user_id = str(update.message.from_user.id)
    user_data = UserDataManager.load_user_data()

    if user_id in user_data and user_data[user_id]["username"] is None:
        username = update.message.text.strip()
        if not UserDataManager.validate_username(username):
            await update.message.reply_text(
                f"⚠️ Invalid username. Please use a name shorter than {MAX_USERNAME_LENGTH} characters."
            )
            return
            
        user_data[user_id]["username"] = username
        UserDataManager.save_user_data(user_data)
        await update.message.reply_text(
            f"✅ Username set to: {username}\n\n"
            "You have *5 free credits* to generate AI faces this month.\nUse /generate to get your first AI face!",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("Please use /generate to get AI faces or /help for commands.")

def reset_monthly_credits(user: dict) -> None:
    """Reset monthly credits if needed."""
    today = datetime.datetime.now()
    last_reset = datetime.datetime.strptime(user["last_reset"], "%Y-%m")
    
    if today.year > last_reset.year or today.month > last_reset.month:
        months_passed = (today.year - last_reset.year) * 12 + (today.month - last_reset.month)
        user["credits"] += 5 * months_passed
        user["last_reset"] = today.strftime("%Y-%m")

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle image generation requests."""
    user_id = str(update.message.from_user.id)
    user_data = UserDataManager.load_user_data()
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")

    if user_id not in user_data or user_data[user_id]["username"] is None:
        await update.message.reply_text("Please start the bot with /start and agree to the disclaimer first.")
        return

    user = user_data[user_id]
    reset_monthly_credits(user)

    # Reset daily ad count if new day
    if user.get("last_ad_day") != today_str:
        user["ads_used_today"] = 0
        user["last_ad_day"] = today_str

    if user.get("subscribed", False):
        await send_ai_image(update)
        UserDataManager.save_user_data(user_data)
        return

    if user["credits"] > 0:
        user["credits"] -= 1
        await send_ai_image(update)
        UserDataManager.save_user_data(user_data)
        return

    keyboard = [
        [InlineKeyboardButton("▶️ Watch Ad to get 1 credit", callback_data="watch_ad")],
        [InlineKeyboardButton("💳 Buy Subscription ($3/month)", callback_data="buy_sub")]
    ]
    await update.message.reply_text(
        "🕐 Your free credits are over for this month!\n"
        "🔁 You'll get +5 more credits next month — and it increases by 5 every month you stay active! 🎁\n"
        "💡 Watch an ad to continue now, or\n"
        "🔓 Unlock unlimited access with just $3/month.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    UserDataManager.save_user_data(user_data)

async def send_ai_image(update: Update) -> None:
    """Send AI-generated image to user."""
    try:
        img_url = "https://thispersondoesnotexist.com/image"
        await update.message.reply_photo(
            photo=img_url, 
            caption="🖼️ Here is your AI-generated face! These images are AI-generated."
        )
    except Exception as e:
        logger.error(f"Failed to send image: {e}")
        await update.message.reply_text("⚠️ Sorry, I couldn't generate an image right now. Please try again later.")

async def watch_ad_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ad watching callback."""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    user_data = UserDataManager.load_user_data()

    if user_id not in user_data:
        await query.edit_message_text("Please start the bot first using /start.")
        return

    user = user_data[user_id]
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")

    if user.get("last_ad_day") != today_str:
        user["ads_used_today"] = 0
        user["last_ad_day"] = today_str

    if user["ads_used_today"] >= MAX_ADS_PER_DAY:
        await query.edit_message_text(
            f"⚠️ You have reached the max ad-earned credits for today ({MAX_ADS_PER_DAY}). "
            "Please wait until tomorrow or subscribe for unlimited access."
        )
        return

    await query.edit_message_text("▶️ Playing ad... Please wait a moment.")
    await asyncio.sleep(3)  # Simulate ad watching

    user["credits"] += 1
    user["ads_used_today"] += 1
    UserDataManager.save_user_data(user_data)

    await query.message.reply_text(
        "✅ Thanks for watching the ad! You have been awarded 1 credit. Use /generate to get your AI face."
    )

async def buy_sub_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle subscription purchase callback."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "💳 Subscribe for just $3/month via crypto.\n"
        "🎁 Get unlimited AI face generations instantly!\n"
        "Contact @yourtelegramhandle for payment and subscription activation."
    )

async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats command."""
    user_id = str(update.message.from_user.id)
    user_data = UserDataManager.load_user_data()

    if user_id not in user_data:
        await update.message.reply_text("Please start the bot with /start.")
        return

    user = user_data[user_id]
    last_reset_date = datetime.datetime.strptime(user["last_reset"], "%Y-%m")
    
    if last_reset_date.month == 12:
        next_reset = datetime.datetime(year=last_reset_date.year + 1, month=1, day=1)
    else:
        next_reset = datetime.datetime(year=last_reset_date.year, month=last_reset_date.month + 1, day=1)

    subscribed = "✅" if user.get("subscribed", False) else "❌"

    stats_text = (
        f"👤 Username: {user.get('username', 'N/A')}\n"
        f"💳 Credits left: {user.get('credits', 0)}\n"
        f"🔔 Subscribed: {subscribed}\n"
        f"📅 Next monthly reset: {next_reset.strftime('%Y-%m-%d')}\n"
        f"▶️ Ads watched today: {user.get('ads_used_today', 0)}/{MAX_ADS_PER_DAY}"
    )
    await update.message.reply_text(stats_text)

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unknown commands."""
    await update.message.reply_text("❓ Unknown command. Please use /start, /generate, /stats, or other valid commands.")

async def post_init(application: Application) -> None:
    """Post-initialization tasks."""
    await application.bot.set_my_commands([
        ("start", "Start the bot"),
        ("generate", "Generate an AI face"),
        ("stats", "View your statistics")
    ])

def setup_handlers(application: Application) -> None:
    """Set up all handlers."""
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler, pattern="^(agree|disagree)$"))
    application.add_handler(CallbackQueryHandler(watch_ad_handler, pattern="^watch_ad$"))
    application.add_handler(CallbackQueryHandler(buy_sub_handler, pattern="^buy_sub$"))
    application.add_handler(CommandHandler("generate", generate_image))
    application.add_handler(CommandHandler("stats", stats_handler))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), receive_username))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

async def run_webhook(application: Application) -> None:
    """Run the bot in webhook mode for Render."""
    port = int(os.environ.get("PORT", 5000))
    webhook_url = os.environ.get("WEBHOOK_URL")
    
    if not webhook_url:
        logger.warning("WEBHOOK_URL not set, using polling instead")
        await application.run_polling()
        return

    await application.bot.set_webhook(
        url=f"{webhook_url}/{os.environ.get('BOT_TOKEN')}",
        secret_token=os.environ.get("WEBHOOK_SECRET")
    )
    
    async with application:
        await application.start()
        await application.updater.start_webhook(
            listen="0.0.0.0",
            port=port,
            webhook_url=f"{webhook_url}/{os.environ.get('BOT_TOKEN')}",
            secret_token=os.environ.get("WEBHOOK_SECRET")
        )
        
        logger.info(f"Bot running in webhook mode on port {port}")
        await asyncio.Event().wait()  # Run forever

async def run_polling(application: Application) -> None:
    """Run the bot in polling mode (for local development)."""
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    logger.info("Bot running in polling mode")
    await asyncio.Event().wait()  # Run forever

async def main() -> None:
    """Main entry point."""
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN environment variable not set")

    application = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .build()
    )
    
    setup_handlers(application)
    
    # Choose between webhook (Render) and polling (local) mode
    if os.environ.get("RENDER"):
        await run_webhook(application)
    else:
        await run_polling(application)

if __name__ == "__main__":
    asyncio.run(main())
