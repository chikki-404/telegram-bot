from telegram.ext import Updater, CommandHandler
import os

TOKEN = os.getenv("8595233518:AAHYLmSC7LJmK3WmX53iORCN4JinOzU1vOs")

def start(update, context):
    update.message.reply_text("Bot is alive 24/7 🚀")

updater = Updater(TOKEN, use_context=True)
dp = updater.dispatcher

dp.add_handler(CommandHandler("start", start))

updater.start_polling()
updater.idle()