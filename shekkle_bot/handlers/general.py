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
    
    user_obj = db.get_user(user.id)
    balance = user_obj.balance if user_obj else 0
    
    await update.message.reply_text(
        f"Welcome {user.first_name}! You have {balance} Shekkles."
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return
        
    user_obj = db.get_user(user.id)
    
    if user_obj:
        await update.message.reply_text(f"Your current balance: {user_obj.balance} Shekkles")
    else:
        # If user not found, add them
        db.add_user(user.id, user.username)
        user_obj = db.get_user(user.id)
        if user_obj:
            await update.message.reply_text(f"Your current balance: {user_obj.balance} Shekkles")
        else:
            await update.message.reply_text("Error retrieving balance.")

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

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return
        
    records = db.get_user_history(user.id, limit=5)
    
    if not records:
        await update.message.reply_text("You have no resolved bets in your history.")
        return
        
    msg = "📜 <b>Your Last 5 Bets</b>\n\n"
    for r in records:
        desc = r['description']
        amount = r['amount']
        choice = r['choice']
        outcome = r['outcome']
        payout = r['payout']
        
        if r['refunded']:
            status = "🔄 Refunded"
            profit_str = ""
        elif choice == outcome:
            status = "✅ Won"
            profit = payout - amount
            profit_str = f"(+{profit})"
        else:
            status = "❌ Lost"
            profit_str = f"(-{amount})"
            
        msg += f"<b>Bet #{r['bet_id']}</b>: {desc}\n"
        msg += f"Wager: {amount} on {choice} | Result: {outcome}\n"
        msg += f"{status} {profit_str}\n\n"
        
    await update.message.reply_text(msg, parse_mode='HTML')