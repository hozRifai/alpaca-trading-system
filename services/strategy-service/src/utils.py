from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os

Base = declarative_base()

class DatabaseManager:
    def __init__(self):
        self.market_engine = create_engine(os.getenv('MARKET_DB_CONNECTION'))
        self.transactions_engine = create_engine(os.getenv('TRANSACTIONS_DB_CONNECTION'))
        
        self.market_session = sessionmaker(bind=self.market_engine)
        self.transactions_session = sessionmaker(bind=self.transactions_engine)

    def get_market_session(self):
        return self.market_session()

    def get_transactions_session(self):
        return self.transactions_session()

# Transaction model
class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    strategy_id = Column(String)
    symbol = Column(String)
    action = Column(String)
    price = Column(Float)
    quantity = Column(Integer)
    status = Column(String)