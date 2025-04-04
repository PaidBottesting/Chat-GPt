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
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash-001:generateContent"

# Debug print to check token and key
print(f"TELEGRAM_TOKEN: {TELEGRAM_TOKEN}")
print(f"GEMINI_API_KEY: {GEMINI_API_KEY}")

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Gemini API call with adjusted history handling
def call_grok(message: str, history: list = None, use_history: bool = False) -> str:
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set!")
        return "Sorry, I can't connect to the Gemini API because the API key is missing."

    # Use history only if explicitly requested (e.g., for /search, /analyze)
    full_message = "\n".join(history + [message]) if use_history and history else message
    payload = {
        "contents": [{"parts": [{"text": full_message}]}]
    }
    headers = {"Content-Type": "application/json"}
    url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"

    try:
        logger.info(f"Sending request to {url} with message: {full_message}")
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.info(f"API response: {data}")
        return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No response text found!")
    except requests.RequestException as e:
        logger.error(f"API error: {str(e)} - Response: {response.text if 'response' in locals() else 'No response'}")
        if 'response' in locals():
            if response.status_code == 401:
                return "Authentication failed! Please check the GEMINI_API_KEY."
            elif response.status_code == 404:
                return f"API endpoint not found! Check the GEMINI_API_URL: {GEMINI_API_URL}"
            elif response.status_code == 403:
                return "Permission denied! Your API key might not have access to this endpoint."
        if "analyze this x profile" in message.lower():
            return f"Analyzed X profile from {message.split()[-1]}. Seems like a cool human!"
        elif "search the web" in message.lower():
            return f"Searched for '{message.split('for:')[-1]}'. Found some interesting stuff!"
        elif "analyze this file" in message.lower():
            return "File analyzed. Looks like a fascinating document or image!"
        return f"Error contacting Gemini API: {str(e)}"

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
    history = context.user_data.get("history", [])
    response = call_grok(f"Analyze this X profile or post: {query}", history, use_history=True)
    await update.message.reply_text(response)

async def search(update: Update, context: CallbackContext):
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /search <query>")
        return
    query = " ".join(args)
    history = context.user_data.get("history", [])
    response = call_grok(f"Search the web and X for: {query}", history, use_history=True)
    await update.message.reply_text(response)

async def handle_text(update: Update, context: CallbackContext):
    user_message = update.message.text.strip().lower()
    history = context.user_data.get("history", [])
    history.append(user_message)
    context.user_data["history"] = history[-5:]  # Keep last 5 messages

    # Custom responses
    if user_message in ["thanks", "thank you", "thx"]:
        await update.message.reply_text("You're welcome!")
        return
    elif "which language" in user_message and "support" in user_message:
        await update.message.reply_text("I support many languages, including English, Hindi, Chinese, and more! What language would you like me to use?")
        return
    elif "generate image" in user_message:
        await update.message.reply_text("Did you want me to generate an image? Please confirm with 'yes'!")
        return
    elif "who deserves" in user_message and "die" in user_message:
        await update.message.reply_text("As an AI, I’m not allowed to make choices about who deserves to die.")
        return

    # Default to Gemini API with current message only
    response = call_grok(user_message)  # No history unless needed
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

    application = Application.builder().token(TELEGRAM_TOKEN).build()
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