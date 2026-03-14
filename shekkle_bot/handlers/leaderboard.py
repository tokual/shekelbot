from telegram import Update
from telegram.ext import ContextTypes
import shekkle_bot.database as db
from shekkle_bot.config import CURRENCY_NAME
import html

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the top winners."""
    winners, _ = db.get_leaderboard_data()
    
    if not winners:
        await update.message.reply_text("No stats available yet.")
        return

    msg = f"🏆 <b>Top Winners</b> 🏆\n\n"
    
    # Show top 10
    my_rank = None
    user_id = update.effective_user.id
    
    for i, user in enumerate(winners, 1):
        if user['user_id'] == user_id:
            my_rank = (i, user)
            
        if i <= 10:
            username = html.escape(user['username']) if user['username'] else "Unknown"
            profit = user['net_profit']
            won = user['bets_won']
            total = user['bets_placed']
            win_rate = (won / total * 100) if total > 0 else 0
            
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈"
            elif i == 3:
                medal = "🥉"
            else:
                medal = f"{i}."
                
            msg += f"{medal} <b>{username}</b>: {profit}\n"
            msg += f"   (Won: {won}/{total} | WR: {win_rate:.1f}%)\n"

    if my_rank and my_rank[0] > 10:
        msg += f"\n...\n<b>{my_rank[0]}. YOU</b>: {my_rank[1]['net_profit']} (WR: {(my_rank[1]['bets_won']/max(1, my_rank[1]['bets_placed'])*100):.1f}%)\n"

    await update.message.reply_text(msg, parse_mode='HTML')

async def show_loserboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the top losers."""
    _, losers = db.get_leaderboard_data()
    
    if not losers:
        await update.message.reply_text("No stats available yet.")
        return

    msg = f"📉 <b>Top Losers</b> 📉\n\n"
    
    actual_losers = [u for u in losers if u['net_profit'] < 0]
    
    if not actual_losers:
        await update.message.reply_text("No one is in the red yet! 🎉")
        return

    for i, user in enumerate(actual_losers[:10], 1):
        username = html.escape(user['username']) if user['username'] else "Unknown"
        profit = user['net_profit']
        
        msg += f"{i}. <b>{username}</b>: {profit}\n"

    await update.message.reply_text(msg, parse_mode='HTML')