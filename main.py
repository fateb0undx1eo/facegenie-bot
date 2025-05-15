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
