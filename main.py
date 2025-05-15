import os
import logging
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from telegram import (
    Update,
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

import httpx  # Async HTTP client instead of requests

# Logging config
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token from env
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    logger.error("BOT_TOKEN environment variable not set!")
    exit(1)

# In-memory user data (replace with DB in production)
user_data = {}  # Structure: {user_id: {'credits': int, 'unlimited': bool}}

# Async command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = {"credits": 0, "unlimited": False}

    keyboard = [
        [InlineKeyboardButton("🔁 $1 = More Credits", callback_data="buy_credits")],
        [InlineKeyboardButton("💎 $3 = Unlimited Faces", callback_data="buy_unlimited")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 Welcome to the *AI Face Generator Bot!*\n\n"
        "💬 Use /generate to get an AI-generated human face.\n\n"
        "💰 Pricing:\n"
        "- $1 = Extra Credits (per image)\n"
        "- $3 = Unlimited Usage\n\n"
        "👇 Choose a plan to proceed:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = user_data.get(user_id, {"credits": 0, "unlimited": False})

    # Credit check
    if not user["unlimited"] and user["credits"] <= 0:
        await update.message.reply_text(
            "⚠️ You don't have enough credits.\n\n"
            "Use /start and buy credits or unlimited access."
        )
        return

    url = "https://thispersondoesnotexist.com/image"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            if response.status_code == 200:
                if not user["unlimited"]:
                    user_data[user_id]["credits"] -= 1
                await update.message.reply_photo(photo=response.content, caption="Here's your AI-generated face 👤")
            else:
                await update.message.reply_text("⚠️ Failed to generate face. Please try again.")
    except Exception as e:
        logger.error(f"Error generating face: {e}")
        await update.message.reply_text("⚠️ An error occurred while generating the face.")

# Payment option handler (simulate purchase)
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "buy_credits":
        user_data[user_id]["credits"] += 5  # Simulated purchase
        await query.edit_message_text("✅ You've purchased *5 image credits*.\nUse /generate to try now!", parse_mode="Markdown")

    elif query.data == "buy_unlimited":
        user_data[user_id]["unlimited"] = True
        await query.edit_message_text("✅ You've unlocked *unlimited access*!\nUse /generate anytime.", parse_mode="Markdown")

# Error handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    if isinstance(update, Update) and update.message:
        await update.message.reply_text("⚠️ Oops! Something went wrong. Please try again later.")

# Keep-alive HTTP server
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_keepalive_server():
    port = int(os.getenv("PORT", "8080"))
    server = HTTPServer(("", port), KeepAliveHandler)
    logger.info(f"Starting keep-alive server on port {port}")
    server.serve_forever()

# Main bot startup
async def main():
    app = Application.builder().token(TOKEN).build()

    commands = [
        BotCommand("start", "Start the bot and view pricing"),
        BotCommand("generate", "Generate a new AI face"),
    ]
    await app.bot.set_my_commands(commands)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("generate", generate))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_error_handler(error_handler)

    logger.info("Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_keepalive_server, daemon=True).start()
    asyncio.run(main())
