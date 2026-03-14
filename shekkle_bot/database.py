import logging
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager

from shekkle_bot.config import DB_PATH
from shekkle_bot.models import Base, User, Bet, Wager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SQLAlchemy setup
# Use absolute path for sqlite
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
ScopedSession = scoped_session(SessionLocal)

def init_db():
    """Initializes the database tables."""
    Base.metadata.create_all(bind=engine)
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE wagers ADD COLUMN payout INTEGER;"))
    except Exception:
        pass
    logger.info(f"Database initialized at {DB_PATH}")

@contextmanager
def get_db():
    """Context manager for database sessions."""
    db = ScopedSession()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# --- User Functions ---

def add_user(user_id, username):
    with get_db() as db:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            new_user = User(user_id=user_id, username=username)
            db.add(new_user)
            db.commit()
            return True
        return False

def get_user(user_id):
    """Returns User object or None. Note: detached from session."""
    with get_db() as db:
        user = db.query(User).filter(User.user_id == user_id).first()
        if user:
            # We strictly only need the balance/last_daily usually
            # Returning a dict avoids DetachedInstanceError if we access lazy props often
            # But for simple scalars it is usually fine. Let's return a simple object or DTO.
            # To be safe against DetachedInstanceError on relationships:
            db.refresh(user) 
            return user 
        return None

def get_user_by_username(username):
    """Returns User object or None by username. Note: detached from session."""
    with get_db() as db:
        # Strip '@' if provided
        username_clean = username.lstrip('@')
        user = db.query(User).filter(User.username == username_clean).first()
        if user:
            db.refresh(user) 
            return user 
        return None

def get_all_users():
    with get_db() as db:
        users = db.query(User).all()
        return [u.user_id for u in users]

def update_balance(user_id, amount):
    with get_db() as db:
        user = db.query(User).filter(User.user_id == user_id).first()
        if user:
            user.balance += amount
            db.commit()
            return True
        return False

# --- Daily Reward Functions ---

def check_daily_claim(user_id):
    with get_db() as db:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return False
        
        if not user.last_daily:
            return True
            
        last_daily = datetime.fromisoformat(user.last_daily)
        if datetime.now() - last_daily >= timedelta(hours=24):
            return True
        return False

def perform_daily_claim(user_id, amount):
    with get_db() as db:
        user = db.query(User).filter(User.user_id == user_id).first()
        if user:
            user.balance += amount
            user.last_daily = datetime.now().isoformat()
            db.commit()
            db.refresh(user)
            return user.balance
        return 0

def get_daily_time_remaining_str(user_id):
    with get_db() as db:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user or not user.last_daily:
            return "00:00"
        
        last_daily = datetime.fromisoformat(user.last_daily)
        next_claim = last_daily + timedelta(hours=24)
        remaining = next_claim - datetime.now()
        
        if remaining.total_seconds() <= 0:
            return "00:00"
            
        hours, remainder = divmod(remaining.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}"

# --- Betting Functions ---

def create_bet(creator_id, description, deadline, option_a, option_b):
    with get_db() as db:
        new_bet = Bet(
            creator_id=creator_id,
            description=description,
            deadline=deadline,
            option_a=option_a,
            option_b=option_b
        )
        db.add(new_bet)
        db.commit()
        db.refresh(new_bet)
        return new_bet.id

def get_open_bets():
    with get_db() as db:
        bets = db.query(Bet).filter(Bet.status == 'OPEN').all()
        return [{
            'id': b.id, 'creator_id': b.creator_id, 'description': b.description,
            'deadline': b.deadline, 'option_a': b.option_a, 'option_b': b.option_b
        } for b in bets]

def get_bet(bet_id):
    with get_db() as db:
        bet = db.query(Bet).filter(Bet.id == bet_id).first()
        if bet:
            return {
                'id': bet.id, 'description': bet.description, 'status': bet.status,
                'option_a': bet.option_a, 'option_b': bet.option_b, 'deadline': bet.deadline
            }
        return None

def place_wager(user_id, bet_id, choice, amount):
    with get_db() as db:
        bet = db.query(Bet).with_for_update().filter(Bet.id == bet_id).first()
        if not bet:
            return False, "Bet not found."
        
        if bet.status != 'OPEN':
            return False, "Bet is not open."
            
        if datetime.now().isoformat() > bet.deadline:
            return False, "Deadline has passed."

        user = db.query(User).with_for_update().filter(User.user_id == user_id).first()
        if not user or user.balance < amount:
            return False, "Insufficient funds."

        user.balance -= amount
        
        wager = Wager(
            user_id=user_id,
            bet_id=bet_id,
            choice=choice,
            amount=amount,
            placed_at=datetime.now().isoformat()
        )
        db.add(wager)
        db.commit()
        return True, "Wager placed successfully."

def get_bet_wagers(bet_id):
    with get_db() as db:
        wagers = db.query(Wager).filter(Wager.bet_id == bet_id, Wager.refunded == 0).all()
        result = []
        for w in wagers:
            result.append({
                'user_id': w.user_id,
                'choice': w.choice,
                'amount': w.amount,
                'username': w.user.username if w.user else "Unknown"
            })
        return result

def get_expired_open_bets(current_time_iso):
    with get_db() as db:
        bets = db.query(Bet).filter(Bet.status == 'OPEN', Bet.deadline <= current_time_iso).all()
        return [{'id': b.id, 'description': b.description} for b in bets]

def update_bet_status(bet_id, status):
    with get_db() as db:
        bet = db.query(Bet).filter(Bet.id == bet_id).first()
        if bet:
            bet.status = status
            db.commit()

def resolve_bet(bet_id, outcome, cutoff_dt=None):
    """
    Resolves a bet.
    Returns: (success, message, winners_list)
    winners_list: [{'user_id': int, 'payout': int, 'profit': int}, ...]
    """
    if outcome not in ('A', 'B'):
        return False, "Outcome must be A or B", []

    with get_db() as db:
        bet = db.query(Bet).with_for_update().filter(Bet.id == bet_id).first()
        if not bet:
            return False, "Bet not found", []
        
        if bet.status == 'RESOLVED':
            return False, "Bet already resolved", []

        wagers = db.query(Wager).filter(Wager.bet_id == bet_id).all()
        valid_wagers = []
        refund_count = 0
        refund_gross = 0

        cutoff_val = None
        if cutoff_dt:
            cutoff_val = cutoff_dt.isoformat() if isinstance(cutoff_dt, datetime) else cutoff_dt

        for w in wagers:
            if w.refunded:
                continue
            
            should_keep = True
            if cutoff_val and w.placed_at and w.placed_at > cutoff_val:
                should_keep = False
            
            if should_keep:
                valid_wagers.append(w)
            else:
                w.user.balance += w.amount
                w.refunded = 1
                refund_count += 1
                refund_gross += w.amount

        total_pool = sum(w.amount for w in valid_wagers)
        winning_wagers = [w for w in valid_wagers if w.choice == outcome]
        winning_pool = sum(w.amount for w in winning_wagers)

        bet.status = 'RESOLVED'
        bet.outcome = outcome
        bet.resolved_at = datetime.now().isoformat()
        if cutoff_val:
            bet.cutoff_at = cutoff_val

        msg_prefix = ""
        if refund_count > 0:
            msg_prefix = f"⚠️ Refunded {refund_count} wagers ({refund_gross}) after cutoff.\n"

        winners_list = []

        if winning_pool == 0:
            for w in valid_wagers:
                w.user.balance += w.amount
                w.refunded = 1
            
            db.commit()
            return True, f"{msg_prefix}No winners. All refunded.", []

        ratio = total_pool / winning_pool
        count = 0
        
        for w in winning_wagers:
            payout = int(w.amount * ratio)
            w.user.balance += payout
            w.payout = payout
            
            profit = payout - w.amount
            winners_list.append({
                'user_id': w.user_id,
                'payout': payout,
                'profit': profit
            })
            count += 1

        for w in valid_wagers:
            if w.choice != outcome:
                w.payout = 0

        db.commit()
        return True, f"{msg_prefix}Resolved {outcome}. {count} winners (x{ratio:.2f}).", winners_list

def get_user_history(user_id, limit=10):
    """Returns the most recent resolved wagers for a user."""
    with get_db() as db:
        wagers = (db.query(Wager)
                  .join(Bet)
                  .filter(Wager.user_id == user_id, Bet.status == 'RESOLVED')
                  .order_by(Wager.placed_at.desc())
                  .limit(limit)
                  .all())
        
        history = []
        for w in wagers:
            wager_info = {
                'bet_id': w.bet.id,
                'description': w.bet.description,
                'amount': w.amount,
                'choice': w.choice,
                'outcome': w.bet.outcome,
                'payout': w.payout or 0,
                'refunded': w.refunded
            }
            history.append(wager_info)
        return history

def get_leaderboard_data():
    with get_db() as db:
        users = db.query(User).all()
        stats = {}
        
        for u in users:
            stats[u.user_id] = {
                'username': u.username,
                'net_profit': 0, 'bets_placed': 0, 'bets_won': 0
            }

        bets = db.query(Bet).filter(Bet.status == 'RESOLVED').all()
        
        for bet in bets:
            outcome = bet.outcome
            wagers = [w for w in bet.wagers if not w.refunded]
            if not wagers: continue

            total_pool = sum(w.amount for w in wagers)
            winning_wagers = [w for w in wagers if w.choice == outcome]
            winning_pool = sum(w.amount for w in winning_wagers)
            
            if winning_pool == 0: continue
            
            ratio = total_pool / winning_pool

            for w in wagers:
                if w.user_id not in stats: continue
                
                s = stats[w.user_id]
                s['bets_placed'] += 1
                
                if w.choice == outcome:
                    payout = int(w.amount * ratio)
                    profit = payout - w.amount
                    s['bets_won'] += 1
                    s['net_profit'] += profit
                else:
                    s['net_profit'] -= w.amount

        active_stats = [s for s in stats.values() if s['bets_placed'] > 0]
        winners = sorted(active_stats, key=lambda x: x['net_profit'], reverse=True)
        losers = sorted(active_stats, key=lambda x: x['net_profit'])

        return winners, losers
