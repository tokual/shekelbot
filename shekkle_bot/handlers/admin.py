from telegram import Update
from telegram.ext import ContextTypes
import shekkle_bot.database as db
from shekkle_bot.config import ADMIN_IDS

async def resolve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin command to resolve a bet.
    Usage: /resolve <bet_id> <outcome (A/B)>
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ You are not authorized to use this command.")
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: /resolve <bet_id> <outcome (A/B)>")
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

    success, message = db.resolve_bet(bet_id, outcome)
    await update.message.reply_text(message)

async def add_funds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin command to add funds to a user.
    Usage: /give <user_id> <amount>
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ You are not authorized to use this command.")
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: /give <target_user_id> <amount>")
        return

    target_user_id_str = context.args[0]
    amount_str = context.args[1]

    # Allow negative amounts to remove funds
    if not target_user_id_str.isdigit():
            await update.message.reply_text("Error: User ID must be a number.")
            return

    try:
        target_user_id = int(target_user_id_str)
        amount = int(amount_str)
    except ValueError:
        await update.message.reply_text("Error: Amount must be a valid integer.")
        return

    # Check if user exists before adding funds (optional, but good practice)
    # update_balance returns False if sql fails, but doesn't strictly check existence if we blindly update.
    # But update_balance in db uses a WHERE clause, so it won't update non-existent users.
    # Let's ensure the user exists first.
    if not db.get_user(target_user_id):
        # We can optionally add them or fail. Let's fail for safety.
        await update.message.reply_text(f"❌ User detected as {target_user_id} not found in DB.")
        return

    success = db.update_balance(target_user_id, amount)
    
    if success:
        await update.message.reply_text(f"✅ Successfully added {amount} shekkles to user {target_user_id}.")
    else:
        await update.message.reply_text(f"❌ Failed to update balance.")
