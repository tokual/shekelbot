from telegram import Update
from telegram.ext import ContextTypes
import shekkle_bot.database as db
from shekkle_bot.config import DAILY_REWARD

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return

    # Ensure user is in DB
    db.add_user(user.id, user.username)
    
    user_data = db.get_user(user.id)
    balance = user_data['balance'] if user_data else 0
    
    await update.message.reply_text(
        f"Welcome {user.first_name}! You have {balance} Shekkles."
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return
        
    user_data = db.get_user(user.id)
    
    if user_data:
        balance = user_data['balance']
        await update.message.reply_text(f"Your current balance: {balance} Shekkles")
    else:
        # If user not found, add them
        db.add_user(user.id, user.username)
        user_data = db.get_user(user.id)
        balance = user_data['balance']
        await update.message.reply_text(f"Your current balance: {balance} Shekkles")

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return
    
    # Ensure user exists first
    if not db.get_user(user.id):
        db.add_user(user.id, user.username)

    if db.check_daily_claim(user.id):
        new_balance = db.perform_daily_claim(user.id, DAILY_REWARD)
        await update.message.reply_text(
            f"💰 Daily reward claimed! You received {DAILY_REWARD} Shekkles.\n"
            f"New balance: {new_balance} Shekkles"
        )
    else:
        remaining = db.get_daily_time_remaining_str(user.id)
        await update.message.reply_text(
            f"⏳ You have already claimed your daily reward.\n"
            f"Come back in {remaining}."
        )
