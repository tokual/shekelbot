import sqlite3
import os
import sys

# Ensure we can import from shekkle_bot
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shekkle_bot.config import DB_PATH

def fix_refunded_wagers_based_on_cutoff():
    print(f"Opening database at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    try:
        # Get RESOLVED bets with a cutoff time
        c.execute("SELECT id, description, cutoff_at FROM bets WHERE status = 'RESOLVED' AND cutoff_at IS NOT NULL")
        bets = c.fetchall()
        
        updated_count = 0
        
        for bet in bets:
            bet_id = bet['id']
            cutoff_at = bet['cutoff_at']
            
            # Find wagers placed AFTER the cutoff that are NOT yet marked as refunded
            # Note: placed_at is stored as ISO string, so string comparison works
            query = """
                UPDATE wagers 
                SET refunded = 1 
                WHERE bet_id = ? 
                  AND placed_at > ? 
                  AND (refunded IS NULL OR refunded = 0)
            """
            c.execute(query, (bet_id, cutoff_at))
            
            if c.rowcount > 0:
                print(f"Bet {bet_id} ('{bet['description']}'): Marked {c.rowcount} wagers as refunded (placed after {cutoff_at})")
                updated_count += c.rowcount
        
        conn.commit()
        print(f"\nDone! Total wagers marked as refunded: {updated_count}")
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_refunded_wagers_based_on_cutoff()
