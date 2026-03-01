import sqlite3
import logging
from datetime import datetime, timedelta
from .config import DB_PATH, INITIAL_BALANCE

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_connection():
    """Establishes a connection to the SQLite database."""
    return sqlite3.connect(DB_PATH)

def init_db():
    """Initializes the database tables."""
    conn = get_connection()
    c = conn.cursor()

    # Users Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance INTEGER DEFAULT 0,
            last_daily TEXT
        )
    """)

    # Bets Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS bets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            creator_id INTEGER,
            description TEXT,
            deadline TEXT,
            option_a TEXT,
            option_b TEXT,
            outcome TEXT, -- NULL, 'A', or 'B'
            status TEXT DEFAULT 'OPEN' -- 'OPEN', 'LOCKED', 'RESOLVED'
        )
    """)

    # Wagers Table
    c.execute("""
        CREATE TABLE IF NOT EXISTS wagers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            bet_id INTEGER,
            choice TEXT, -- 'A', 'B'
            amount INTEGER,
            placed_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id),
            FOREIGN KEY(bet_id) REFERENCES bets(id)
        )
    """)
    
    # Check if placed_at exists in wagers (migration for existing dbs)
    try:
        c.execute("SELECT placed_at FROM wagers LIMIT 1")
    except sqlite3.OperationalError:
        logger.info("Migrating wagers table: adding placed_at column")
        c.execute("ALTER TABLE wagers ADD COLUMN placed_at TEXT")

    # Check if refunded exists in wagers (migration for existing dbs)
    try:
        c.execute("SELECT refunded FROM wagers LIMIT 1")
    except sqlite3.OperationalError:
        logger.info("Migrating wagers table: adding refunded column")
        c.execute("ALTER TABLE wagers ADD COLUMN refunded INTEGER DEFAULT 0")

    # Commit and close
    conn.commit()
    conn.close()
    logger.info(f"Database initialized at {DB_PATH}")

def add_user(user_id, username):
    """
    Adds a new user to the database if they don't exist.
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        # Check if user exists
        c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if c.fetchone() is None:
            c.execute(
                "INSERT INTO users (user_id, username, balance) VALUES (?, ?, ?)",
                (user_id, username, INITIAL_BALANCE)
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error adding user {user_id}: {e}")
        return False
    finally:
        conn.close()
    return False

def get_user(user_id):
    """
    Retrieves user information as a dictionary.
    Returns None if user does not exist.
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        if row:
            return dict(row)
    except Exception as e:
        logger.error(f"Error retrieving user {user_id}: {e}")
    finally:
        conn.close()
    return None

def update_balance(user_id, amount):
    """
    Atomically updates a user's balance.
    Amount can be positive (credit) or negative (debit).
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (amount, user_id)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error updating balance for {user_id}: {e}")
        return False
    finally:
        conn.close()

def check_daily_claim(user_id):
    """
    Returns True if user can claim daily reward (last claim > 24h ago or never).
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT last_daily FROM users WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        
        if result is None:
            # User might not exist or some error, handled by default 'False' or calling add_user elsewhere
            return False 
            
        last_daily_str = result[0]
        
        if not last_daily_str:
            return True
            
        last_daily = datetime.fromisoformat(last_daily_str)
        if datetime.now() - last_daily >= timedelta(hours=24):
            return True
            
        return False
    except Exception as e:
        logger.error(f"Error checking daily claim for {user_id}: {e}")
        return False
    finally:
        conn.close()

def perform_daily_claim(user_id, amount):
    """
    Updates last_daily timestamp to now and adds amount to balance.
    Returns new balance.
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        now_str = datetime.now().isoformat()
        c.execute("UPDATE users SET balance = balance + ?, last_daily = ? WHERE user_id = ?", (amount, now_str, user_id))
        conn.commit()
        
        c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        res = c.fetchone()
        return res[0] if res else 0
    except Exception as e:
        logger.error(f"Error performing daily claim for {user_id}: {e}")
        return 0
    finally:
        conn.close()

def get_all_users():
    """
    Returns a list of all user_ids.
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT user_id FROM users")
        return [row[0] for row in c.fetchall()]
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        return []
    finally:
        conn.close()

def get_daily_time_remaining_str(user_id):
    """
    Returns a formatted string (HH:MM) of time remaining until next daily claim.
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT last_daily FROM users WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        
        if not result or not result[0]:
            return "00:00"
            
        last_daily = datetime.fromisoformat(result[0])
        next_claim = last_daily + timedelta(hours=24)
        remaining = next_claim - datetime.now()
        
        if remaining.total_seconds() <= 0:
            return "00:00"
            
        hours, remainder = divmod(remaining.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}"
    except Exception as e:
        logger.error(f"Error calculating time remaining for {user_id}: {e}")
        return "Unknown"
    finally:
        conn.close()

def create_bet(creator_id, description, deadline, option_a, option_b):
    """
    Creates a new bet in the database.
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO bets (creator_id, description, deadline, option_a, option_b) VALUES (?, ?, ?, ?, ?)",
            (creator_id, description, deadline, option_a, option_b)
        )
        conn.commit()
        return c.lastrowid
    except Exception as e:
        logger.error(f"Error creating bet: {e}")
        return None
    finally:
        conn.close()

def get_open_bets():
    """
    Returns a list of all OPEN bets.
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM bets WHERE status = 'OPEN'")
        return [dict(row) for row in c.fetchall()]
    except Exception as e:
        logger.error(f"Error getting open bets: {e}")
        return []
    finally:
        conn.close()

def get_bet(bet_id):
    """
    Returns specific bet details.
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM bets WHERE id = ?", (bet_id,))
        row = c.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error getting bet {bet_id}: {e}")
        return None
    finally:
        conn.close()

def place_wager(user_id, bet_id, choice, amount):
    """
    Places a wager. Deducts balance from user.
    Returns (Success, Message).
    """
    conn = get_connection()
    c = conn.cursor()
    try:
        # Check bet status first
        c.execute("SELECT status, deadline FROM bets WHERE id = ?", (bet_id,))
        bet_row = c.fetchone()
        if not bet_row:
             return False, "Bet not found."
        
        status, deadline_str = bet_row
        if status != 'OPEN':
            return False, "Bet is no longer open."

        # Check deadline
        deadline = datetime.fromisoformat(deadline_str)
        if datetime.now() > deadline:
            return False, "Betting deadline has passed."

        # Check user balance
        c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        user_row = c.fetchone()
        if not user_row:
            return False, "User not found."
        
        balance = user_row[0]
        if balance < amount:
            return False, f"Insufficient funds. You have {balance}."

        # Deduct balance
        c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
        
        # Add wager
        c.execute("""
            INSERT INTO wagers (user_id, bet_id, choice, amount, placed_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, bet_id, choice, amount, datetime.now().isoformat()))
        
        conn.commit()
        return True, "Wager placed successfully!"
    except Exception as e:
        conn.rollback()
        logger.error(f"Error placing wager: {e}")
        return False, "Database error."
    finally:
        conn.close()

def get_bet_wagers(bet_id):
    """
    Returns all valid (non-refunded) wagers for a specific bet.
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    try:
        # Join with users to get username
        # Filter out refunded wagers
        query = """
            SELECT w.*, u.username 
            FROM wagers w 
            LEFT JOIN users u ON w.user_id = u.user_id 
            WHERE w.bet_id = ? AND (w.refunded IS NULL OR w.refunded = 0)
        """
        try:
            c.execute(query, (bet_id,))
        except sqlite3.OperationalError:
            # Fallback if refunded column doesn't exist
            logger.warning("refunded column missing in wagers table during get_bet_wagers")
            query_fallback = """
                SELECT w.*, u.username 
                FROM wagers w 
                LEFT JOIN users u ON w.user_id = u.user_id 
                WHERE w.bet_id = ?
            """
            c.execute(query_fallback, (bet_id,))
            
        return [dict(row) for row in c.fetchall()]
    except Exception as e:
        logger.error(f"Error getting wagers for bet {bet_id}: {e}")
        return []
    finally:
        conn.close()

def resolve_bet(bet_id, outcome, cutoff_dt=None):
    """
    Resolves a bet, distributes winnings to users.
    Outcome must be 'A' or 'B'.
    cutoff_dt: If provided, refunds all wagers placed after this datetime.
    Returns (Success, Message).
    """
    if outcome not in ('A', 'B'):
        return False, "Invalid outcome. Must be 'A' or 'B'."

    conn = get_connection()
    c = conn.cursor()
    
    try:
        # Check bet exists and is not resolved
        c.execute("SELECT status, option_a, option_b FROM bets WHERE id = ?", (bet_id,))
        bet_row = c.fetchone()
        
        if not bet_row:
            return False, f"Bet {bet_id} not found."
        
        status, option_a, option_b = bet_row
        
        if status == 'RESOLVED':
            return False, f"Bet {bet_id} is already resolved."

        # Get all wagers for this bet
        # Try to select placed_at, fall back to NULL if column somehow missing (should be handled by migration code but safe to be explicit)
        try:
             c.execute("SELECT id, user_id, choice, amount, placed_at FROM wagers WHERE bet_id = ?", (bet_id,))
        except sqlite3.OperationalError:
             # Fallback if migration failed or transient schema issue
             logger.warning("placed_at column missing in wagers table during resolve")
             c.execute("SELECT id, user_id, choice, amount, NULL as placed_at FROM wagers WHERE bet_id = ?", (bet_id,))
             
        all_wagers = c.fetchall()

        valid_wagers = []
        refunded_count = 0
        refunded_gross = 0

        # Parse cutoff once
        cutoff_val = None
        if cutoff_dt:
             if isinstance(cutoff_dt, str):
                 try:
                     cutoff_val = datetime.fromisoformat(cutoff_dt)
                 except ValueError:
                     logger.error(f"Invalid cutoff format: {cutoff_dt}")
             elif isinstance(cutoff_dt, datetime):
                 cutoff_val = cutoff_dt

        for row in all_wagers:
            wager_id, user_id, choice, amount, placed_at_str = row
            
            should_keep = True
            if cutoff_val and placed_at_str:
                try:
                    placed_at = datetime.fromisoformat(placed_at_str)
                    if placed_at > cutoff_val:
                        should_keep = False
                except ValueError:
                    pass # Keep if date is invalid

            if should_keep:
                valid_wagers.append(row)
            else:
                # Refund
                c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
                # Mark as refunded
                c.execute("UPDATE wagers SET refunded = 1 WHERE id = ?", (wager_id,))
                refunded_count += 1
                refunded_gross += amount

        total_pool = sum(w[3] for w in valid_wagers)
        # outcome is 'A' or 'B'
        winning_wagers = [w for w in valid_wagers if w[2] == outcome]
        winning_pool = sum(w[3] for w in winning_wagers)

        # Update status
        c.execute("UPDATE bets SET status = 'RESOLVED', outcome = ? WHERE id = ?", (outcome, bet_id))

        msg_prefix = ""
        if refunded_count > 0:
            msg_prefix = f"⚠️ {refunded_count} wagers placed after cutoff were refunded ({refunded_gross} total).\n"

        # Case 1: No winners (Refund everyone if pool > 0)
        if winning_pool == 0:
            if total_pool > 0:
                # Refund everyone remaining valid
                for wager_id, user_id, choice, amount, _ in valid_wagers:
                    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
                    # Mark as refunded since the bet was cancelled/refunded
                    c.execute("UPDATE wagers SET refunded = 1 WHERE id = ?", (wager_id,))
                
                conn.commit()
                return True, f"{msg_prefix}No one bet on {outcome}. All {total_pool} refunded."
            else:
                conn.commit()
                return True, f"{msg_prefix}Bet resolved to {outcome}. No valid wagers remained."

        # Case 2: Winners exist
        # Calculate ratio: (Total Pool) / (Winning Pool)
        # If Total=100, Winning=50, Ratio=2.0. Bet 10 -> Get 20.
        payout_ratio = total_pool / winning_pool
        
        winners_count = 0
        for _, user_id, choice, amount, _ in winning_wagers:
            payout = int(amount * payout_ratio) # integer math acts as floor
            c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (payout, user_id))
            winners_count += 1
            
        conn.commit()
        return True, f"{msg_prefix}Bet resolved to {outcome}. {winners_count} winners shared pot of {total_pool}. Multiplier: x{payout_ratio:.2f}"

    except Exception as e:
        logger.error(f"Error resolving bet {bet_id}: {e}")
        return False, f"Error resolving bet: {e}"
    finally:
        conn.close()

def get_leaderboard_data():
    """
    Calculates betting statistics for all users.
    Returns a tuple of two sorted lists: (winners, losers).
    Each list contains dicts: {'username': str, 'net_profit': int, 'total_won': int, 'total_lost': int, 'bets_placed': int, 'bets_won': int}
    """
    conn = get_connection()
    c = conn.cursor()
    
    stats = {} # user_id -> {stats}

    try:
        # Get all users first to initialize
        c.execute("SELECT user_id, username FROM users")
        for uid, uname in c.fetchall():
            stats[uid] = {
                'username': uname,
                'net_profit': 0,
                'total_won': 0,     # Gross winnings
                'total_lost': 0,    # Gross losses
                'bets_placed': 0,
                'bets_won': 0
            }

        # Get all RESOLVED bets
        c.execute("SELECT id, outcome FROM bets WHERE status = 'RESOLVED'")
        resolved_bets = c.fetchall()

        for bet_id, outcome in resolved_bets:
            if not outcome: 
                continue # Should not happen if resolved

            # Get wagers for this bet
            # Filter out refunded wagers (refunded != 1 or NULL)
            try:
                c.execute("SELECT user_id, choice, amount FROM wagers WHERE bet_id = ? AND (refunded IS NULL OR refunded = 0)", (bet_id,))
            except sqlite3.OperationalError:
                # Column might not exist if migration failed, fallback
                c.execute("SELECT user_id, choice, amount FROM wagers WHERE bet_id = ?", (bet_id,))

            bet_wagers = c.fetchall()

            if not bet_wagers:
                continue

            # Calculate pools
            total_pool = sum(w[2] for w in bet_wagers)
            winning_wagers = [w for w in bet_wagers if w[1] == outcome]
            winning_pool = sum(w[2] for w in winning_wagers)
            
            # If everybody lost or refunded scenario in logic (winning_pool == 0)
            if winning_pool == 0:
                # Everyone effectively "refunded" in the logic if total_pool > 0
                # Or house kept it? logic says "All refunded" if winning_pool==0 and total_pool>0
                # So no winners, no losers (net 0)
                continue

            payout_ratio = total_pool / winning_pool

            for uid, choice, amount in bet_wagers:
                if uid not in stats:
                    # User might be deleted? or just safety
                    stats[uid] = {'username': f"User {uid}", 'net_profit':0, 'total_won':0, 'total_lost':0, 'bets_placed':0, 'bets_won':0}
                
                user_stat = stats[uid]
                user_stat['bets_placed'] += 1

                if choice == outcome:
                    # Winner
                    gross_payout = int(amount * payout_ratio)
                    profit = gross_payout - amount
                    
                    user_stat['bets_won'] += 1
                    user_stat['total_won'] += profit 
                    user_stat['net_profit'] += profit
                else:
                    # Loser
                    user_stat['total_lost'] += amount
                    user_stat['net_profit'] -= amount

        # Convert to lists
        data = list(stats.values())
        
        # Sort by Net Profit (descending) for Winners
        winners = sorted(data, key=lambda x: x['net_profit'], reverse=True)
        
        # Sort by Net Profit (ascending) for Losers (who has the lowest negative profit)
        # Or sort by 'total_lost' descending? 
        # "Loserboard who lost the most" -> usually means biggest negative net profit or biggest total loss.
        # Let's use Net Profit ascending (most negative first).
        losers = sorted(data, key=lambda x: x['net_profit'])

        return winners, losers

    except Exception as e:
        logger.error(f"Error calculating leaderboard: {e}")
        return [], []
    finally:
        conn.close()

def get_expired_open_bets(current_time_iso):
    """
    Returns bets where status='OPEN' and deadline <= current_time_iso.
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    try:
        # Assuming timestamps are stored in ISO 8601, string comparison works
        c.execute("SELECT * FROM bets WHERE status = 'OPEN' AND deadline <= ?", (current_time_iso,))
        return [dict(row) for row in c.fetchall()]
    except Exception as e:
        logger.error(f"Error getting expired open bets: {e}")
        return []
    finally:
        conn.close()

def update_bet_status(bet_id, status):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("UPDATE bets SET status = ? WHERE id = ?", (status, bet_id))
        conn.commit()
    except Exception as e:
        logger.error(f"Error updating bet {bet_id} status: {e}")
    finally:
        conn.close()

