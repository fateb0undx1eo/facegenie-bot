import os
import logging
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes

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

# Async command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the AI Face Generator Bot! Type /generate to get a face.")

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = "https://thispersondoesnotexist.com/image"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            if response.status_code == 200:
                await update.message.reply_photo(photo=response.content, caption="Here is a new AI-generated face!")
            else:
                await update.message.reply_text("Failed to generate face. Please try again later.")
    except Exception as e:
        logger.error(f"Error generating face: {e}")
        await update.message.reply_text("An error occurred while generating the face.")

# Error handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    if isinstance(update, Update) and update.message:
        await update.message.reply_text("Oops! Something went wrong. Please try again later.")

# Keep-alive HTTP server for platforms like Replit or Render
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

async def main():
    # Build application
    app = Application.builder().token(TOKEN).build()

    # Register commands for Telegram UI
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("generate", "Generate a new AI face"),
    ]
    await app.bot.set_my_commands(commands)

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("generate", generate))
    app.add_error_handler(error_handler)

    # Start the bot
    logger.info("Starting bot...")
    await app.run_polling()

if __name__ == "__main__":
    # Run keepalive server in daemon thread so it doesn't block shutdown
    threading.Thread(target=run_keepalive_server, daemon=True).start()

    # Run main async bot loop
    asyncio.run(main())
import asyncio
import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Use environment variable for bot token
TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Welcome to the AI Face Generator Bot! Type /generate to get a face.')

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.get("https://thispersondoesnotexist.com", headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code == 200:
            with open("face.jpg", "wb") as f:
                f.write(response.content)
            with open("face.jpg", "rb") as photo:
                await update.message.reply_photo(photo=photo, caption="Here is a new AI-generated face!")
        else:
            await update.message.reply_text("Failed to generate face. Please try again later.")
    except Exception as e:
        logging.error(f"Error generating face: {e}")
        await update.message.reply_text("An error occurred while generating the face.")

# Dummy server to keep Render's or Replit’s web service alive
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is alive!')

def run_keepalive_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('', port), KeepAliveHandler)
    server.serve_forever()

async def run_bot():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("generate", generate))
    await app.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_keepalive_server).start()
    
    # Use this instead of asyncio.run to avoid 'event loop is running' error
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_bot())
