from datetime import datetime
import pandas as pd
from typing import Dict, Any

from ..utils import DatabaseManager, Transaction

class EmaCrossoverStrategy():
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.ema_short = 10
        self.ema_long = 20
        self.entry_price = None
        self.current_position = 0
        
    async def calculate_ema(self, data: pd.DataFrame) -> pd.DataFrame:
        data['ema10'] = data['close'].ewm(span=self.ema_short, adjust=False).mean()
        data['ema20'] = data['close'].ewm(span=self.ema_long, adjust=False).mean()
        return data

    async def execute(self, data: pd.DataFrame, symbol: str) -> None:
        data = await self.calculate_ema(data)
        latest = data.iloc[-1]
        
        # Entry condition: EMA crossover
        if latest['ema10'] > latest['ema20'] and self.current_position <= 0:
            # Calculate position size (example: 95% of available cash)
            price = latest['close']
            quantity = (self.capital * 0.95) // price
            if quantity > 0:
                await self.broker.execute_order(symbol, 'buy', quantity, price)
                self.current_position = quantity
                self.entry_price = price
                await self.log_transaction(symbol, 'buy', price, quantity)
        
        # Exit conditions
        elif self.current_position > 0:
            current_price = latest['close']
            
            # Price drops 2% below crossover point or below EMA20
            exit_condition_1 = current_price < (self.entry_price * 0.98)
            exit_condition_2 = current_price < (latest['ema20'] * 0.98)
            
            if exit_condition_1 or exit_condition_2:
                await self.broker.execute_order(symbol, 'sell', self.current_position, current_price)
                await self.log_transaction(symbol, 'sell', current_price, self.current_position)
                self.current_position = 0
                self.entry_price = None

    async def log_transaction(self, symbol: str, action: str, price: float, quantity: int):
        transaction = {
            'timestamp': datetime.utcnow(),
            'strategy_id': self.strategy_id,
            'symbol': symbol,
            'action': action,
            'price': price,
            'quantity': quantity,
            'status': 'executed'
        }
        db = DatabaseManager()
        session = db.get_transactions_session()
        try:
            session.add(Transaction(**transaction))
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error logging transaction: {str(e)}")
        finally:
            session.close()