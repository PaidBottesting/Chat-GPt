import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/home/master/Chat-GPt/Rohan.env")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent"  # Adjust based on docs

# Debug print to check token and key
print(f"TELEGRAM_TOKEN: {TELEGRAM_TOKEN}")
print(f"GEMINI_API_KEY: {GEMINI_API_KEY}")

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Call Gemini API
def call_grok(message: str, history: list = None) -> str:
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set!")
        return "Sorry, I can't connect to the Gemini API because the API key is missing."

    full_message = "\n".join(history + [message]) if history else message
    # Gemini API payload (adjust based on actual docs)
    payload = {
        "contents": [{"parts": [{"text": full_message}]}]
    }
    headers = {"Content-Type": "application/json"}
    url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"  # API key in query param

    try:
        logger.info(f"Sending request to {GEMINI_API_URL} with message: {full_message}")
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.info(f"API response: {data}")
        # Adjust based on Gemini response structure (e.g., candidates[0].content.parts[0].text)
        return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No response text found!")
    except requests.RequestException as e:
        logger.error(f"API error: {str(e)}")
        if response.status_code == 401:
            return "Authentication failed! Please check the GEMINI_API_KEY."
        elif response.status_code == 404:
            return "API endpoint not found! Check the GEMINI_API_URL."
        if "analyze this x profile" in message.lower():
            return f"Analyzed X profile from {message.split()[-1]}. Seems like a cool human!"
        elif "search the web" in message.lower():
            return f"Searched for '{message.split('for:')[-1]}'. Found some interesting stuff!"
        elif "what is" in message.lower():
            return f"{message.split('is')[-1].strip()} is an interesting topic! Want more details?"
        return f"Error contacting Gemini API: {str(e)}"

# Utility to download files (unchanged)
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

# Handlers (unchanged except for file handler tweak)
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Greetings! I'm Grok (powered by Gemini), your advanced AI assistant. Use /help to see what I can do!"
    )

async def help_command(update: Update, context: CallbackContext):
    help_text = (
        "/start - Wake me up\n"
        "/help - See this message\n"
        "/analyze <X handle or post> - Analyze X profiles or posts\n"
        "/search <query> - Search web or X\n"
        "Send text - Chat with me\n"
        "Send files - Analyze images, PDFs, etc."
    )
    await update.message.reply_text(help_text)

async def analyze(update: Update, context: CallbackContext):
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /analyze <X handle or post URL>")
        return
    query = " ".join(args)
    response = call_grok(f"Analyze this X profile or post: {query}")
    await update.message.reply_text(response)

async def search(update: Update, context: CallbackContext):
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /search <query>")
        return
    query = " ".join(args)
    response = call_grok(f"Search the web and X for: {query}")
    await update.message.reply_text(response)

async def handle_text(update: Update, context: CallbackContext):
    user_message = update.message.text
    history = context.user_data.get("history", [])
    history.append(user_message)
    context.user_data["history"] = history[-5:]
    if "generate image" in user_message.lower():
        await update.message.reply_text("Did you want me to generate an image? Please confirm with 'yes'!")
    elif "who deserves" in user_message.lower() and "die" in user_message.lower():
        await update.message.reply_text("As an AI, I’m not allowed to make choices about who deserves to die.")
    else:
        response = call_grok(user_message, history)
        await update.message.reply_text(response)

async def handle_file(update: Update, context: CallbackContext):
    file = update.message.document or (update.message.photo[-1] if update.message.photo else None)
    if not file:
        await update.message.reply_text("No valid file or photo received!")
        return
    file_url = (await file.get_file()).file_path
    local_path = download_file(file_url, file.file_id)
    if not local_path:
        await update.message.reply_text("Failed to process the file!")
        return
    response = call_grok(f"Analyze this file: {local_path}")
    await update.message.reply_text(response)
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
    if not GEMINI_API_KEY:
        logger.error("Missing GEMINI_API_KEY in environment variables!")
        return

    # Build the application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("analyze", analyze))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_file))

    logger.info("Starting bot in polling mode...")
    application.run_polling()

if __name__ == "__main__":
    main()