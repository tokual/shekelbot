from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship, declarative_base
from shekkle_bot.config import INITIAL_BALANCE

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True)
    username = Column(String)
    balance = Column(Integer, default=INITIAL_BALANCE)
    last_daily = Column(String, nullable=True)

    wagers = relationship("Wager", back_populates="user")

class Bet(Base):
    __tablename__ = 'bets'

    id = Column(Integer, primary_key=True, autoincrement=True)
    creator_id = Column(Integer)
    description = Column(String)
    deadline = Column(String) # Stored as ISO format string
    option_a = Column(String)
    option_b = Column(String)
    outcome = Column(String, nullable=True) # 'A' or 'B'
    status = Column(String, default='OPEN') # 'OPEN', 'LOCKED', 'RESOLVED'
    cutoff_at = Column(String, nullable=True)
    resolved_at = Column(String, nullable=True)

    wagers = relationship("Wager", back_populates="bet")

class Wager(Base):
    __tablename__ = 'wagers'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    bet_id = Column(Integer, ForeignKey('bets.id'))
    choice = Column(String) # 'A' or 'B'
    amount = Column(Integer)
    placed_at = Column(String)
    refunded = Column(Integer, default=0) # 0 = active, 1 = refunded
    payout = Column(Integer, nullable=True) # Amount won (including stake)

    user = relationship("User", back_populates="wagers")
    bet = relationship("Bet", back_populates="wagers")
