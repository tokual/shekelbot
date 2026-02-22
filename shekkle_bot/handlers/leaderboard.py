from telegram import Update
from telegram.ext import ContextTypes
import shekkle_bot.database as db
from shekkle_bot.config import CURRENCY_NAME
from shekkle_bot.utils.formatters import escape_markdown

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the top winners."""
    winners, _ = db.get_leaderboard_data()
    
    if not winners:
        await update.message.reply_text("No stats available yet.")
        return

    msg = f"🏆 *{CURRENCY_NAME} Leaderboard* 🏆\n\n"
    
    # Show top 10
    for i, user in enumerate(winners[:10], 1):
        username = escape_markdown(user['username'])
        profit = user['net_profit']
        won = user['bets_won']
        total = user['bets_placed']
        win_rate = (won / total * 100) if total > 0 else 0
        
        # E.g. 1. User (Profit: 500, WR: 60%)
        msg += f"{i}. *{username}*: {profit} {CURRENCY_NAME}\n"
        msg += f"   (Won: {won}/{total} | WR: {win_rate:.1f}%)\n"

    await update.message.reply_text(msg, parse_mode='Markdown')

async def show_loserboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the top losers."""
    _, losers = db.get_leaderboard_data()
    
    if not losers:
        await update.message.reply_text("No stats available yet.")
        return

    msg = f"📉 *{CURRENCY_NAME} Loserboard* 📉\n\n"
    
    # Show top 10 (most negative profit first)
    # Filter only those with negative profit to avoid shaming winners on a fresh board
    # Or just show the bottom people even if positive?
    # Usually loserboard is for people who lost money.
    # If everyone is positive, the "loser" is just the one who won the least.
    # But usually "Loserboard" implies negative.
    
    actual_losers = [u for u in losers if u['net_profit'] < 0]
    
    if not actual_losers:
        await update.message.reply_text("No one is in the red yet! 🎉")
        return

    for i, user in enumerate(actual_losers[:10], 1):
        username = escape_markdown(user['username'])
        profit = user['net_profit'] # Negative number
        won = user['bets_won']
        total = user['bets_placed']
        win_rate = (won / total * 100) if total > 0 else 0
        
        msg += f"{i}. *{username}*: {profit} {CURRENCY_NAME}\n"
        msg += f"   (Won: {won}/{total} | WR: {win_rate:.1f}%)\n"

    await update.message.reply_text(msg, parse_mode='Markdown')
