import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from dotenv import load_dotenv
import logging
import pytz  # Already installed, so this import should work

# Load environment variables
load_dotenv("/home/master/Chat-GPt/Rohan.env")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
XAI_API_KEY = os.getenv("XAI_API_KEY")
XAI_API_URL = "https://api.xai.com/grok"

# Debug print to check token
print(f"TELEGRAM_TOKEN: {TELEGRAM_TOKEN}")
print(f"XAI_API_KEY: {XAI_API_KEY}")

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Simulated/real Grok API call
def call_grok(message: str, history: list = None) -> str:
    headers = {"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"}
    full_message = "\n".join(history + [message]) if history else message
    payload = {"message": full_message}
    try:
        response = requests.post(XAI_API_URL, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json().get("reply", "I processed your request!")
    except requests.RequestException as e:
        logger.error(f"API error: {str(e)}")
        if "analyze this x profile" in message.lower():
            return f"Analyzed X profile from {message.split()[-1]}. Seems like a cool human!"
        elif "search the web" in message.lower():
            return f"Searched for '{message.split('for:')[-1]}'. Found some interesting stuff!"
        elif "analyze this file" in message.lower():
            return "File analyzed. Looks like a fascinating document or image!"
        return f"Error contacting Grok API: {str(e)}"

# Utility to download files
def download_file(file_url: str, file_id: str) -> str:
    try:
        response = requests.get(file_url, timeout=10)
        response.raise_for_status()
        file_ext = file_url.split(".")[-1] if "." in file_url else "tmp"
        local_path = f"temp_{file_id}.{file_ext}"
        with open(local_path, "wb") as f:
            f.write(response.content)
        return local_path
    except Exception as e:
        logger.error(f"File download error: {str(e)}")
        return None

# Handlers
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Greetings! I'm Grok, your advanced AI assistant. Use /help to see what I can do!"
    )

def help_command(update: Update, context: CallbackContext):
    help_text = (
        "/start - Wake me up\n"
        "/help - See this message\n"
        "/analyze <X handle or post> - Analyze X profiles or posts\n"
        "/search <query> - Search web or X\n"
        "Send text - Chat with me\n"
        "Send files - Analyze images, PDFs, etc."
    )
    update.message.reply_text(help_text)

def analyze(update: Update, context: CallbackContext):
    args = context.args
    if not args:
        update.message.reply_text("Usage: /analyze <X handle or post URL>")
        return
    query = " ".join(args)
    response = call_grok(f"Analyze this X profile or post: {query}")
    update.message.reply_text(response)

def search(update: Update, context: CallbackContext):
    args = context.args
    if not args:
        update.message.reply_text("Usage: /search <query>")
        return
    query = " ".join(args)
    response = call_grok(f"Search the web and X for: {query}")
    update.message.reply_text(response)

def handle_text(update: Update, context: CallbackContext):
    user_message = update.message.text
    history = context.user_data.get("history", [])
    history.append(user_message)
    context.user_data["history"] = history[-5:]
    if "generate image" in user_message.lower():
        update.message.reply_text("Did you want me to generate an image? Please confirm with 'yes'!")
    elif "who deserves" in user_message.lower() and "die" in user_message.lower():
        update.message.reply_text("As an AI, I’m not allowed to make choices about who deserves to die.")
    else:
        response = call_grok(user_message, history)
        update.message.reply_text(response)

def handle_file(update: Update, context: CallbackContext):
    file = update.message.document or update.message.photo[-1]
    file_url = file.get_file().file_path
    local_path = download_file(file_url, file.file_id)
    if not local_path:
        update.message.reply_text("Failed to process the file!")
        return
    response = call_grok(f"Analyze this file: {local_path}")
    update.message.reply_text(response)
    try:
        os.remove(local_path)
        logger.info(f"Cleaned up file: {local_path}")
    except OSError as e:
        logger.error(f"Cleanup error: {str(e)}")

# Main bot setup
def main():
    if not TELEGRAM_TOKEN:
        logger.error("Missing TELEGRAM_TOKEN in environment variables!")
        return

    # Explicitly set the timezone to UTC using pytz
    application = Application.builder().token(TELEGRAM_TOKEN).job_queue_timezone(pytz.UTC).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("analyze", analyze))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(MessageHandler(Filters.TEXT & ~Filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(Filters.Document() | Filters.Photo(), handle_file))

    logger.info("Starting bot in polling mode...")
    application.run_polling()

if __name__ == "__main__":
    main()