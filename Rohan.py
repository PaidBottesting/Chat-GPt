import telebot
from openai import OpenAI
import random

# 🔹 Bot & OpenAI Setup
TOKEN = "8192955318:AAE8lE3fY4gXibXLqoRFUWLv-QGeChMNxnU"
OPENAI_API_KEY = ""
bot = telebot.TeleBot(TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)

# 🔹 Chat Memory (Optional)
user_chat_history = {}

# 🔹 Fun Random Replies
RANDOM_REPLIES = [
    "That’s interesting! Tell me more. 🤔",
    "Haha, I didn’t see that coming! 😂",
    "I totally agree! What else?",
    "Oh wow, that's cool! 😮",
    "Good point! What do you think about it?",
    "Hmm... I need to think about that. 🧐"
]

def save_chat(user_id, user_msg, bot_response):
    if user_id not in user_chat_history:
        user_chat_history[user_id] = []
    user_chat_history[user_id].append({"user": user_msg, "bot": bot_response})
    if len(user_chat_history[user_id]) > 10:  # Limit memory size
        user_chat_history[user_id].pop(0)

@bot.message_handler(func=lambda message: True)
def chat_with_ai(message):
    user_id = message.from_user.id
    text = message.text.lower()

    # 🔹 Smart Help System
    if "help" in text:
        if "voice" in text:
            response = "🎙 To convert voice messages to text:\n1️⃣ Send a voice message.\n2️⃣ The bot will transcribe it automatically."
        elif "file" in text:
            response = "📂 To extract text from files:\n1️⃣ Upload a PDF, DOCX, or image.\n2️⃣ The bot will extract and send the text."
        elif "image" in text:
            response = "🎨 To generate an AI image:\n1️⃣ Use `/generate <description>`\n2️⃣ Example: `/generate futuristic city`"
        elif "chat" in text:
            response = "🤖 To chat with AI:\n1️⃣ Just type your question.\n2️⃣ I'll reply with the best answer."
        else:
            response = "📌 Need help? Here’s what I can do:\n- 🤖 AI Chat\n- 🎙 Voice to Text\n- 📂 Extract text from files\n- 🎨 Generate AI Images\nType your question, and I’ll help!"
        bot.reply_to(message, response)
        return

    # 🔹 Generate AI Response (With Chat Memory)
    chat_history = [{"role": "system", "content": "You are a helpful AI assistant."}]
    if user_id in user_chat_history:
        for chat in user_chat_history[user_id][-5:]:  # Use last 5 messages for context
            chat_history.append({"role": "user", "content": chat["user"]})
            chat_history.append({"role": "assistant", "content": chat["bot"]})
    
    chat_history.append({"role": "user", "content": message.text})
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=chat_history
    )
    
    ai_response = response.choices[0].message.content  

    # 🔹 Add Random Chat Interaction
    if random.random() < 0.4:  # 40% chance to add a fun response
        ai_response += f"\n\n{random.choice(RANDOM_REPLIES)}"

    save_chat(user_id, message.text, ai_response)
    bot.reply_to(message, ai_response)

# 🔹 Start the bot
print("🤖 Bot is running...")
bot.polling()
