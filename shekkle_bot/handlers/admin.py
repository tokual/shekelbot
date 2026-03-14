from telegram import Update
from telegram.ext import ContextTypes
import shekkle_bot.database as db
from shekkle_bot.config import ADMIN_IDS
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def resolve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin command to resolve a bet.
    Usage: /resolve <bet_id> <outcome (A/B)> [cutoff_time (YYYY-MM-DD HH:MM)]
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ You are not authorized to use this command.")
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: /resolve <bet_id> <outcome (A/B)> [YYYY-MM-DD HH:MM]")
        return

    bet_id_str = context.args[0]
    outcome = context.args[1].upper()

    if not bet_id_str.isdigit():
        await update.message.reply_text("Error: Bet ID must be a number.")
        return
            
    bet_id = int(bet_id_str)

    if outcome not in ('A', 'B'):
        await update.message.reply_text("Error: Outcome must be 'A' or 'B'.")
        return

    cutoff_dt = None
    if len(context.args) > 2:
        cutoff_str = " ".join(context.args[2:])
        try:
            cutoff_dt = datetime.fromisoformat(cutoff_str)
        except ValueError:
            try:
                cutoff_dt = datetime.strptime(cutoff_str, "%Y-%m-%d %H:%M")
            except ValueError:
                await update.message.reply_text("❌ Invalid date format. Use YYYY-MM-DD HH:MM or ISO format.")
                return

    # Call DB resolve
    success, message, winners_list = db.resolve_bet(bet_id, outcome, cutoff_dt)
    await update.message.reply_text(message)

    if success and winners_list:
        # Notify winners
        for winner in winners_list:
            uid = winner['user_id']
            payout = winner['payout']
            profit = winner['profit']
            
            msg = (
                f"🎉 <b>Bet Won!</b> 🎉\n"
                f"You bet on the winning outcome for Bet #{bet_id}.\n"
                f"Payout: {payout} (+{profit} profit)"
            )
            try:
                await context.bot.send_message(chat_id=uid, text=msg, parse_mode='HTML')
            except Exception as e:
                logger.warning(f"Failed to notify user {uid}: {e}")

async def add_funds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin command to add funds to a user.
    Usage: /give <user_id|@username> <amount>
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ You are not authorized to use this command.")
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: /give <user_id|@username> <amount>")
        return

    target_user_str = context.args[0]
    amount_str = context.args[1]

    try:
        amount = int(amount_str)
    except ValueError:
        await update.message.reply_text("Error: Amount must be a valid integer.")
        return

    # Check if target is a username or ID
    target_user_id = None
    if target_user_str.startswith('@') or not target_user_str.isdigit():
        user_obj = db.get_user_by_username(target_user_str)
        if user_obj:
            target_user_id = user_obj.user_id
        else:
            await update.message.reply_text(f"❌ User {target_user_str} not found in DB.")
            return
    else:
        target_user_id = int(target_user_str)
        user_obj = db.get_user(target_user_id)
        if not user_obj:
            await update.message.reply_text(f"❌ User ID {target_user_id} not found in DB.")
            return

    success = db.update_balance(target_user_id, amount)
    
    if success:
        await update.message.reply_text(f"✅ Successfully added {amount} shekkles to {target_user_str}.")
    else:
        await update.message.reply_text(f"❌ Failed to update balance.")